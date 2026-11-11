<div align="center">
<h1>Pypods</h1>
  <picture >
    
  <source media="(prefers-color-scheme: dark)" width="1081" height="530"srcset="https://i.postimg.cc/vBZ0tL6m/glyph-mosaic-photo.png">
  <img width="1081" height="530" src="https://i.postimg.cc/QdcY8M3G/glyph-mosaic-photo-(1).png" alt="bg-earbuds" width="500">
</picture>
</div>
<hr>


<ul>
  <h2>✨ Features</h2>
  <li>🎮 Turns headphone media keys (and any keyboard key) into game input</li>
  <li>🕵️ Detects <b>press</b>, <b>release</b>, <b>tap</b>, <b>double tap</b> and <b>long press</b></li>
  <li>👾 Simple game loop with <code>setup</code> / <code>update</code> / <code>draw</code></li>
  <li>🖥️ Flicker-free terminal drawing</li>
  <li>🔇 Optional blocking of media keys so they don't change your volume while playing ( <img alt = "win" width="15px" styles = "padding-right-10px;" src="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/windows11/windows11-original.svg" /> only )</li>
</ul>

<h2>📦 Installation</h2>

<pre lang="bash">
git clone https://github.com/kernighantech/pypods.git
cd pypods
pip install .
</pre>

<p>Requires <img alt = "win" width="15px" src="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/python/python-original.svg" /> Python 3.8+ and <a href="https://pypi.org/project/pynput/">pynput</a>.</p>

<h2>🚀 Quick start</h2>

<pre lang="python">
from pypods import Game, PLUS, MINUS, MIDDLE, run, bar, clamp

class Volume(Game):
    controls = {
        "up":   [PLUS, "up"],
        "down": [MINUS, "down"],
        "quit": [MIDDLE, "q"],
    }

    def setup(self):
        self.level = 50

    def update(self, dt):
        self.level = clamp(self.level + self.action_axis("down", "up") * 40 * dt, 0, 100)
        if self.action_pressed("quit"):
            self.quit()

    def draw(self):
        self.show(f"🔊 {bar(self.level, 100)} {self.level:3.0f}%")

run(Volume, block_media_keys=True)
</pre>

<h2>▶️Buttons</h2>

<table>
  <tr><th>Constant</th><th>Button</th></tr>
  <tr><td><code>PLUS</code></td><td>Volume +</td></tr>
  <tr><td><code>MINUS</code></td><td>Volume −</td></tr>
  <tr><td><code>MIDDLE</code></td><td>Play / Pause</td></tr>
  <tr><td><code>NEXT</code></td><td>Next track</td></tr>
  <tr><td><code>PREV</code></td><td>Previous track</td></tr>
</table>

<h2>🎬 Events</h2>

<table>
  <tr><th>Event</th><th>Check</th><th>When</th></tr>
  <tr><td><code>PRESS</code></td><td><code>pressed()</code></td><td>Button goes down</td></tr>
  <tr><td><code>RELEASE</code></td><td><code>released()</code></td><td>Button goes up</td></tr>
  <tr><td><code>TAP</code></td><td><code>tapped()</code></td><td>Short single press</td></tr>
  <tr><td><code>DOUBLE_TAP</code></td><td><code>double_tapped()</code></td><td>Two quick presses</td></tr>
  <tr><td><code>LONG_PRESS</code></td><td><code>long_pressed()</code></td><td>Held for a while</td></tr>
</table>

<p>You can use callbacks if you want :</p>

<pre lang="python">
@game.on(PLUS, "double_tap")
def boost():
    ...
</pre>
<h2>🔍 Key tester</h2>
<p>See what pypods receives from your headphones:</p>

<pre lang="bash">
python pypods.py       
</pre>

<h2>📡 Example : Morse code trainer</h2>

<p><code>morzyanka_testgame.py</code></p>

<pre lang="bash">
python morzyanka_testgame.py
</pre>

<hr>

<p align="center">Works on <img alt = "win" width="15px" styles = "padding-right-10px;" src="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/windows11/windows11-original.svg" /> Windows · <img alt = "applelogo" width="15px" styles = "padding-right-10px;" src="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/apple/apple-original.svg" /> macOS ·  <img alt = "linux" width="15px" styles = "padding-right-10px;" src="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/linux/linux-original.svg" />Linux</p>
