from __future__ import annotations
import inspect
import sys
import threading
import time
import warnings
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple

__version__ = "3.4.1"

__all__ = [
    "PLUS", "MINUS", "MIDDLE", "NEXT", "PREV", "HEADPHONE_BUTTONS",
    "PRESS", "RELEASE", "TAP", "DOUBLE_TAP", "LONG_PRESS", "EVENTS", "ANY",
    "Buttons", "Game", "InputListener", "Screen",
    "run", "normalize_name", "bar", "clamp", "key_tester",
]

PLUS = "plus"      
MINUS = "minus"   
MIDDLE = "middle"  
NEXT = "next"      
PREV = "prev"      
HEADPHONE_BUTTONS = (PLUS, MINUS, MIDDLE, NEXT, PREV)

ANY = "*"  

PRESS = "press"           
RELEASE = "release"        
TAP = "tap"               
DOUBLE_TAP = "double_tap"  
LONG_PRESS = "long_press" 
EVENTS = (PRESS, RELEASE, TAP, DOUBLE_TAP, LONG_PRESS)

_MEDIA_VK = {175: PLUS, 174: MINUS, 179: MIDDLE, 176: NEXT, 177: PREV}
_MEDIA_KEY_NAMES = {
    "media_volume_up": PLUS,
    "media_volume_down": MINUS,
    "media_play_pause": MIDDLE,
    "media_next": NEXT,
    "media_previous": PREV,
}

_ALIASES = {
    "=": PLUS, "+": PLUS, "volume_up": PLUS,
    "-": MINUS, "_": MINUS, "volume_down": MINUS,
    "play_pause": MIDDLE,
    "previous": PREV,
    " ": "space", "spacebar": "space",
    "escape": "esc",
    "return": "enter",
    **_MEDIA_KEY_NAMES,
}


def normalize_name(name: str) -> str:
    """Return the canonical button name: lowercase, with aliases resolved.

    normalize_name("Space") -> "space", normalize_name("=") -> "plus",
    normalize_name("Escape") -> "esc".
    """
    if not isinstance(name, str):
        raise TypeError(f"button names must be strings, got {name!r}")
    if len(name) == 1:  
        return _ALIASES.get(name, name.lower())
    key = name.strip().lower()
    return _ALIASES.get(key, key)


def _wants_arg(fn: Callable) -> bool:
    """True if fn can take one positional argument (used to pass the button name)."""
    try:
        params = inspect.signature(fn).parameters.values()
    except (TypeError, ValueError):
        return False
    for p in params:
        if p.kind == p.VAR_POSITIONAL:
            return True
        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD):
            return True
    return False


def _call(entry: Tuple[Callable, bool], arg: str) -> None:
    fn, wants_arg = entry
    if wants_arg:
        fn(arg)
    else:
        fn()

class Buttons:
    """Collects raw key events from any thread and turns them into per-frame state.

    The input thread calls feed(). Your game loop calls update() once per frame,
    then reads held()/pressed()/released()/tapped()/double_tapped()/long_pressed().
    All queries return the state of the *current frame*, so every check in one
    frame sees the same answer.
    """

    def __init__(self, double_tap_window: float = 0.30, long_press_time: float = 0.50):
        self.double_tap_window = double_tap_window
        self.long_press_time = long_press_time
        self.frame = 0

        self._lock = threading.Lock()
        self._queue: List[Tuple[str, str, float]] = []
        self._down_raw: Set[str] = set() 
        self._now = time.perf_counter()
        self._held: Dict[str, float] = {}     
        self._pressed: Set[str] = set()
        self._released: Set[str] = set()
        self._tapped: Set[str] = set()
        self._double: Set[str] = set()
        self._long: Set[str] = set()
        self._long_done: Set[str] = set()     
        self._no_tap: Set[str] = set()         
        self._pending_tap: Dict[str, float] = {}  
        self._callbacks: Dict[Tuple[str, str], List[Tuple[Callable, bool]]] = {}

    def feed(self, name: str, is_down: bool, t: Optional[float] = None) -> None:
        """Report that a button went down (is_down=True) or up (False).

        Repeated "down" reports while a key is held (OS auto-repeat) are ignored.
        """
        name = normalize_name(name)
        t = time.perf_counter() if t is None else t
        with self._lock:
            if is_down and name not in self._down_raw:
                self._down_raw.add(name)
                self._queue.append((name, PRESS, t))
            elif not is_down and name in self._down_raw:
                self._down_raw.discard(name)
                self._queue.append((name, RELEASE, t))

    def press(self, name: str) -> None:
        """Simulate pressing a button (e.g. from an on-screen button or a test)."""
        self.feed(name, True)

    def release(self, name: str) -> None:
        """Simulate releasing a button."""
        self.feed(name, False)

    def tap(self, name: str) -> None:
        """Simulate a quick press + release. Both show up on the next update()."""
        self.feed(name, True)
        self.feed(name, False)

    def clear(self) -> None:
        """Forget everything: queued events, held buttons and pending gestures."""
        with self._lock:
            self._queue.clear()
            self._down_raw.clear()
        self._held.clear()
        self._pending_tap.clear()
        self._long_done.clear()
        self._no_tap.clear()
        self._pressed, self._released = set(), set()
        self._tapped, self._double, self._long = set(), set(), set()

    def update(self, now: Optional[float] = None) -> None:
        """Advance one frame: process queued events, detect gestures, run callbacks."""
        self._now = time.perf_counter() if now is None else now
        with self._lock:
            events, self._queue = self._queue, []

        self.frame += 1
        self._pressed, self._released = set(), set()
        self._tapped, self._double, self._long = set(), set(), set()
        fired: List[Tuple[str, str]] = []

        for name, kind, t in events:
            if kind == PRESS:
                self._pressed.add(name)
                self._held[name] = t
                self._long_done.discard(name)
                fired.append((name, PRESS))
                released_at = self._pending_tap.pop(name, None)
                if released_at is not None:
                    if t - released_at <= self.double_tap_window:
                        self._double.add(name)
                        fired.append((name, DOUBLE_TAP))
                        self._no_tap.add(name) 
                    else: 
                        self._tapped.add(name)
                        fired.insert(len(fired) - 1, (name, TAP))
            else:
                down_at = self._held.pop(name, t)
                self._released.add(name)
                fired.append((name, RELEASE))
                short = (t - down_at) < self.long_press_time
                if short and name not in self._no_tap:
                    self._pending_tap[name] = t
                self._no_tap.discard(name)
                self._long_done.discard(name)

        for name, released_at in list(self._pending_tap.items()):
            if self._now - released_at > self.double_tap_window:
                del self._pending_tap[name]
                self._tapped.add(name)
                fired.append((name, TAP))
        for name, down_at in self._held.items():
            if name not in self._long_done and self._now - down_at >= self.long_press_time:
                self._long_done.add(name)
                self._long.add(name)
                fired.append((name, LONG_PRESS))

        for name, kind in fired:
            for entry in list(self._callbacks.get((name, kind), ())):
                _call(entry, name)
            for entry in list(self._callbacks.get((ANY, kind), ())):
                _call(entry, name)

    def held(self, name: str) -> bool:
        """True while the button is down."""
        return normalize_name(name) in self._held

    def pressed(self, name: str) -> bool:
        """True only on the frame the button went down."""
        return normalize_name(name) in self._pressed

    def released(self, name: str) -> bool:
        """True only on the frame the button went up."""
        return normalize_name(name) in self._released

    def tapped(self, name: str) -> bool:
        """True on the frame a short single tap is confirmed (after the double-tap window)."""
        return normalize_name(name) in self._tapped

    def double_tapped(self, name: str) -> bool:
        """True on the frame the second of two quick taps goes down."""
        return normalize_name(name) in self._double

    def long_pressed(self, name: str) -> bool:
        """True on the one frame a hold reaches long_press_time."""
        return normalize_name(name) in self._long

    def held_for(self, name: str) -> float:
        """Seconds the button has been held so far (0.0 if it is up)."""
        down_at = self._held.get(normalize_name(name))
        return 0.0 if down_at is None else max(0.0, self._now - down_at)

    def axis(self, negative: str, positive: str) -> int:
        """-1 if only `negative` is held, +1 if only `positive` is held, else 0."""
        return int(self.held(positive)) - int(self.held(negative))

    def any_pressed(self) -> Optional[str]:
        """Name of a button pressed this frame, or None."""
        return next(iter(sorted(self._pressed)), None)

    def all_held(self) -> Set[str]:
        """Set of every button currently held."""
        return set(self._held)

    def on(self, name: str, event: str = PRESS, fn: Optional[Callable] = None):
        """Run fn when `event` happens to button `name` (use ANY for every button).

        fn may take no arguments or one (the button name). Works as a decorator:

            @buttons.on(PLUS, "double_tap")
            def boost(): ...
        """
        if event not in EVENTS:
            raise ValueError(f"unknown event {event!r}; use one of {EVENTS}")
        key = (name if name == ANY else normalize_name(name), event)

        def register(f: Callable) -> Callable:
            self._callbacks.setdefault(key, []).append((f, _wants_arg(f)))
            return f

        return register if fn is None else register(fn)

    def off(self, name: str, event: str = PRESS, fn: Optional[Callable] = None) -> None:
        """Remove a callback (or all callbacks for that name/event if fn is None)."""
        key = (name if name == ANY else normalize_name(name), event)
        if fn is None:
            self._callbacks.pop(key, None)
        else:
            self._callbacks[key] = [e for e in self._callbacks.get(key, []) if e[0] != fn]

_WM_KEYDOWN, _WM_SYSKEYDOWN = 0x100, 0x104

def _import_keyboard():
    try:
        from pynput import keyboard
    except (ImportError, OSError) as exc:
        raise ImportError(
            f"pypods needs the 'pynput' package ({exc}). Install it with:  pip install pynput"
        ) from exc
    return keyboard

class InputListener:
    """Listens to the keyboard (and headphone media keys) in a background thread
    and feeds every key into a Buttons object.

        buttons = Buttons()
        with InputListener(buttons, block_media_keys=True):
            while True:
                buttons.update()
                ...

    block_media_keys=True stops volume/play-pause from also changing your system
    volume or music while the game runs. Windows only; ignored elsewhere.
    """

    def __init__(self, buttons: Buttons, block_media_keys: bool = False):
        self.buttons = buttons
        self.block_media_keys = block_media_keys
        self._listener = None
        self._kb = None

    @property
    def running(self) -> bool:
        return self._listener is not None and self._listener.running

    def start(self) -> "InputListener":
        if self._listener is not None:
            return self
        kb = self._kb = _import_keyboard()
        extra = {}

        if self.block_media_keys:
            if sys.platform == "win32":
                extra["win32_event_filter"] = self._win32_filter
            else:
                warnings.warn(
                    "block_media_keys only works on Windows; media keys will still "
                    "change volume/music on this system.",
                    RuntimeWarning, stacklevel=2,
                )

        self._listener = kb.Listener(
            on_press=self._handler(True), on_release=self._handler(False), **extra
        )
        self._listener.start()
        return self
    
    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def __enter__(self) -> "InputListener":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()

    def _win32_filter(self, msg, data):
        name = _MEDIA_VK.get(getattr(data, "vkCode", None))
        if name is None:
            return True  # not a media key: let it through normally
        self.buttons.feed(name, msg in (_WM_KEYDOWN, _WM_SYSKEYDOWN))
        self._listener.suppress_event()  
        return False

    def _handler(self, is_down: bool):
        def callback(key, *_):
            try:
                name = self.key_name(key)
                if name:
                    self.buttons.feed(name, is_down)
            except Exception:
                pass
        return callback

    def key_name(self, key) -> Optional[str]:
        """Convert a pynput key object into a pypods button name."""
        kb = self._kb
        if kb is not None and isinstance(key, kb.Key):
            return normalize_name(_MEDIA_KEY_NAMES.get(key.name, key.name))
        vk = getattr(key, "vk", None)
        if vk in _MEDIA_VK:
            return _MEDIA_VK[vk]
        char = getattr(key, "char", None)
        if char:
            if len(char) == 1 and 1 <= ord(char) <= 26:  
                char = chr(ord(char) + 96)
            return normalize_name(char)
        if vk is not None:
            return f"vk{vk}"
        return None

def _enable_windows_ansi() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)  
    except Exception:
        pass

class Screen:
    """Redraws a block of text in place in the terminal (no scrolling, no flicker)."""

    def __init__(self, stream=None):
        self.stream = stream if stream is not None else sys.stdout
        self._lines = 0
        self._last: Optional[str] = None
        self._ready = False

    def show(self, text) -> None:
        text = str(text)
        if text == self._last:
            return
        if not self._ready:
            _enable_windows_ansi()
            self.stream.write("\x1b[?25l")  
            self._ready = True
        out = []
        if self._lines > 1:
            out.append(f"\x1b[{self._lines - 1}F")  
        else:
            out.append("\r")
        out.append("\x1b[J")  
        out.append(text)
        self.stream.write("".join(out))
        self.stream.flush()
        self._lines = text.count("\n") + 1
        self._last = text

    def finish(self) -> None:
        """Move below the drawn block and restore the cursor."""
        if self._ready:
            self.stream.write("\n\x1b[?25h")
            self.stream.flush()
        self._lines, self._last, self._ready = 0, None, False

def bar(value: float, maximum: float, width: int = 20, fill: str = "█", empty: str = "░") -> str:
    """Text progress bar: bar(30, 100, 10) -> '███░░░░░░░'."""
    frac = 0.0 if maximum <= 0 else clamp(value / maximum, 0.0, 1.0)
    n = int(round(frac * width))
    return fill * n + empty * (width - n)

def clamp(value: float, low: float, high: float) -> float:
    """Keep value between low and high."""
    return max(low, min(high, value))

class Game:
    """Subclass this, override setup/update/draw, then call run(MyGame).

    Class settings (override in your subclass or pass to run()):
        title, fps, controls, block_media_keys, double_tap_window,
        long_press_time, max_dt, listen
    """

    title = "Game"
    fps: Optional[float] = 60
    controls: Dict[str, Iterable[str]] = {}
    block_media_keys = False
    block_volume_keys = False  
    double_tap_window = 0.30
    long_press_time = 0.50
    max_dt = 0.25               
    listen = True               

    def __init__(self, **settings):
        for key, value in settings.items():
            if not hasattr(type(self), key):
                raise TypeError(f"unknown game setting {key!r}")
            setattr(self, key, value)

        self.buttons = Buttons(self.double_tap_window, self.long_press_time)
        self.screen = Screen()
        self.running = False
        self.time = 0.0   
        self.frame = 0    
        self.dt = 0.0     

        self._binds: Dict[str, List[str]] = {}
        self._action_cbs: Dict[Tuple[str, str], List[Tuple[Callable, bool]]] = {}
        self._action_fired: Dict[Tuple[str, str], int] = {}
        for action, names in dict(self.controls).items():
            self.bind(action, *([names] if isinstance(names, str) else names))
        for event in EVENTS:
            self.buttons.on(ANY, event, self._make_action_dispatch(event))

    def setup(self) -> None:
        """Called once before the first frame. Create your game state here."""

    def update(self, dt: float) -> None:
        """Called every frame. dt = seconds since last frame. Move things here."""

    def draw(self) -> None:
        """Called every frame after update(). Show things here (e.g. self.show(...))."""

    def teardown(self) -> None:
        """Called once when the game stops, even after an error or Ctrl+C."""

    def bind(self, action: str, *names: str) -> None:
        """Attach buttons to an action: bind("jump", PLUS, "space")."""
        lst = self._binds.setdefault(action, [])
        for n in names:
            n = normalize_name(n)
            if n not in lst:
                lst.append(n)

    def unbind(self, action: str, *names: str) -> None:
        """Remove some buttons from an action, or the whole action if no names given."""
        if not names:
            self._binds.pop(action, None)
            return
        drop = {normalize_name(n) for n in names}
        self._binds[action] = [n for n in self._binds.get(action, []) if n not in drop]
    def bindings(self, action: Optional[str] = None):
        """Buttons bound to one action (tuple), or a copy of all bindings (dict)."""
        if action is None:
            return {a: tuple(n) for a, n in self._binds.items()}
        return tuple(self._binds.get(action, ()))
    
    def _any(self, action: str, test: Callable[[str], bool]) -> bool:
        return any(test(n) for n in self._binds.get(action, ()))
    
    def action_held(self, action: str) -> bool:
        return self._any(action, self.buttons.held)
    
    def action_pressed(self, action: str) -> bool:
        return self._any(action, self.buttons.pressed)
    
    def action_released(self, action: str) -> bool:
        return self._any(action, self.buttons.released)
    
    def action_tapped(self, action: str) -> bool:
        return self._any(action, self.buttons.tapped)
    
    def action_double_tapped(self, action: str) -> bool:
        return self._any(action, self.buttons.double_tapped)

    def action_long_pressed(self, action: str) -> bool:
        return self._any(action, self.buttons.long_pressed)

    def action_held_for(self, action: str) -> float:
        return max((self.buttons.held_for(n) for n in self._binds.get(action, ())), default=0.0)

    def action_axis(self, negative: str, positive: str) -> int:
        """-1, 0 or +1 from two actions, e.g. action_axis("left", "right")."""
        return int(self.action_held(positive)) - int(self.action_held(negative))

    def on(self, name: str, event: str = PRESS, fn: Optional[Callable] = None):
        """Callback for a raw button. Same as self.buttons.on(...). Decorator-friendly."""
        return self.buttons.on(name, event, fn)

    def on_action(self, action: str, event: str = PRESS, fn: Optional[Callable] = None):
        """Callback for an action (fires at most once per frame per event)."""
        if event not in EVENTS:
            raise ValueError(f"unknown event {event!r}; use one of {EVENTS}")

        def register(f: Callable) -> Callable:
            self._action_cbs.setdefault((action, event), []).append((f, _wants_arg(f)))
            return f

        return register if fn is None else register(fn)

    def _make_action_dispatch(self, event: str) -> Callable[[str], None]:
        def dispatch(name: str) -> None:
            for action, names in self._binds.items():
                key = (action, event)
                if name in names and key in self._action_cbs:
                    if self._action_fired.get(key) == self.buttons.frame:
                        continue
                    self._action_fired[key] = self.buttons.frame
                    for entry in list(self._action_cbs[key]):
                        _call(entry, action)
        return dispatch

    def show(self, text) -> None:
        """Draw text in the terminal, replacing what show() drew last frame."""
        self.screen.show(text)

    def quit(self) -> None:
        """Stop the game after the current frame."""
        self.running = False

    def run(self) -> "Game":
        """Start input, call setup(), loop update()/draw() at self.fps, clean up."""
        listener = None
        if self.listen:
            block = self.block_media_keys or self.block_volume_keys
            listener = InputListener(self.buttons, block_media_keys=block).start()
        self.running = True
        try:
            self.setup()
            period = 1.0 / self.fps if self.fps else 0.0
            last = time.perf_counter()  
            next_frame = last
            while self.running:
                now = time.perf_counter()
                self.dt = min(now - last, self.max_dt) if self.max_dt else now - last
                last = now
                self.time += self.dt
                self.buttons.update(now)
                self.update(self.dt)
                self.draw()
                self.frame += 1
                if period:
                    next_frame += period
                    delay = next_frame - time.perf_counter()
                    if delay > 0:
                        time.sleep(delay)
                    else:
                        next_frame = time.perf_counter()  
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            try:
                self.teardown()
            finally:
                if listener is not None:
                    listener.stop()
                self.screen.finish()
        return self

def run(game, **settings) -> Game:
    """Run a game class (or an already-created game). Returns the game object.

        run(MyGame)
        run(MyGame, fps=30, block_media_keys=True)
    """
    if isinstance(game, Game):
        for key, value in settings.items():
            setattr(game, key, value)
        return game.run()
    return game(**settings).run()

def key_tester(block_media_keys: bool = False) -> None:
    """Print the name of every key/button you press. Ctrl+C to quit."""

    class KeyTester(Game):
        def setup(self):
            self.log: List[str] = []
            self.on(ANY, PRESS, lambda n: self.log.append(f"{n:<12} press"))
            self.on(ANY, RELEASE, lambda n: self.log.append(f"{n:<12} release"))
            self.on(ANY, TAP, lambda n: self.log.append(f"{n:<12} tap"))
            self.on(ANY, DOUBLE_TAP, lambda n: self.log.append(f"{n:<12} DOUBLE TAP"))
            self.on(ANY, LONG_PRESS, lambda n: self.log.append(f"{n:<12} LONG PRESS"))

        def draw(self):
            held = ", ".join(sorted(self.buttons.all_held())) or "-"
            lines = [f"pypods {__version__} key tester  |  Ctrl+C to quit",
                     f"held now: {held}", ""]
            lines += self.log[-12:] or ["press any key or headphone button..."]
            self.show("\n".join(lines))

    run(KeyTester, block_media_keys=block_media_keys)

if __name__ == "__main__":
    key_tester(block_media_keys="--block" in sys.argv[1:])
