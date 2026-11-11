import random
import tkinter as tk
from pypods import MIDDLE, Buttons, InputListener

MORSE = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", (
    ".- -... -.-. -.. . ..-. --. .... .. .--- -.- .-.. -- -. --- .--. --.- .-. ... - ..- ...- .-- -..- -.-- --.. "
    "----- .---- ..--- ...-- ....- ..... -.... --... ---.. ----.").split()))
WHO = "THE CAT|MY DOG|A ROBOT|THE PILOT|OUR TEACHER|A TINY BIRD|THE OLD SAILOR|MY FRIEND".split("|")
DOES = "FOUND|PAINTED|CHASED|BUILT|SOLD|LOST|FIXED|WATCHED".split("|")
WHAT = "A RED BALL|THE MOON|TWO BOXES|A SECRET MAP|THE BLUE CAR|SEVEN APPLES|A FAST BOAT|THE RADIO".split("|")
WHEN = ["TODAY", "AT NIGHT", "IN 1999", "ON MONDAY", "AGAIN", ""]
CELL, GAP, ROW, PAD = 64, 36, 150, 40

def sentence():
    return " ".join(filter(None, map(random.choice, (WHO, DOES, WHAT, WHEN))))

class MorseCode:
    def __init__(self, root):
        self.root, self.buttons = root, Buttons(long_press_time=0.3)
        self.errors, self.dashed = 0, False
        self.canvas = tk.Canvas(root, width=1000, height=560, bg="#111", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _: self.draw())
        self.new_sentence()
        self.poll()

    def new_sentence(self):
        self.text, self.i, self.typed, self.wrong = sentence(), 0, "", False
        self.letters = self.text.replace(" ", "")

    def enter(self, symbol):
        self.typed += symbol
        code = MORSE[self.letters[self.i]]
        self.wrong = not code.startswith(self.typed)
        if self.wrong: 
            self.errors, self.typed = self.errors + 1, ""
        elif self.typed == code: 
            self.i, self.typed = self.i + 1, ""
            if self.i == len(self.letters):
                self.new_sentence()
        self.draw()

    def draw(self):
        c, x, y, k = self.canvas, PAD, PAD, 0
        c.delete("all")
        for word in self.text.split():
            if x > PAD and x + len(word) * CELL > c.winfo_width() - PAD:  
                x, y = PAD, y + ROW
            for ch in word:
                color = "#66bb6a" if k < self.i else "white" if k > self.i else "#ef5350" if self.wrong else "#ffd54f"
                c.create_text(x + CELL / 2, y, text=ch, fill=color, font=("Courier", 34, "bold"), anchor="n")
                c.create_text(x + CELL / 2, y + 55, text=MORSE[ch], fill="#4fc3f7", font=("Courier", 16, "bold"), anchor="n")
                if k == self.i:
                    c.create_text(x + CELL / 2, y + 85, text=self.typed, fill=color, font=("Courier", 16, "bold"), anchor="n")
                x, k = x + CELL, k + 1
            x += GAP
        c.create_text(PAD, c.winfo_height() - PAD / 2, fill="#888", font=("Courier", 12), anchor="sw",
                      text=f"tap middle = dot   hold middle = dash      mistakes: {self.errors}")

    def poll(self):
        self.buttons.update()
        if self.buttons.long_pressed(MIDDLE):  
            self.dashed = True
            self.enter("-")
        if self.buttons.released(MIDDLE):
            if not self.dashed:
                self.enter(".")
            self.dashed = False
        self.root.after(16, self.poll)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Morse Code")
    game = MorseCode(root)
    with InputListener(game.buttons, block_media_keys=True):
        root.mainloop()
