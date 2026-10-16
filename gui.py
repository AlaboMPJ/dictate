"""The window for dictate. Runs under WINDOWS Python (tkinter + Pillow), driven over stdin by
the recorder in WSL, so it sits on the real desktop rather than in WSLg.

stdin lines:   state <name> <text...>     starting | listening | hearing | converting | done | error
               wave <v> <v> ...           envelope values 0..1, newest last
stdout lines:  stop                       click or Enter: finish the take now
               cancel                     Esc: throw it away

WHY IT IS DRAWN AS AN IMAGE (2026-10-13, "still jagged"). Tk draws polygons with no anti-aliasing,
and an unaware process on a high-DPI screen is bitmap-scaled by Windows, so every edge stair-stepped
whatever the curve. The process declares itself DPI aware and the ribbon is rendered by Pillow at
three times its size and reduced with Lanczos, which is real anti-aliasing, with a soft glow under it.
"""
import ctypes
import math
import sys
import threading
import time
import tkinter as tk

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

from PIL import Image, ImageDraw, ImageFilter, ImageTk  # noqa: E402

BG, FG, DIM, LINE = "#000000", "#e8e8e8", "#7a7a7a", "#262626"
ACCENT = (176, 48, 106)       # Tyrian lifted so it reads on black
CORE = (236, 236, 236)
COLS = 160                    # 40 per second, ~4 s of history
SS = 3                        # supersampling factor for the ribbon

root = tk.Tk()
S = max(1.0, root.winfo_fpixels("1i") / 96.0)
px = lambda v: int(round(v * S))  # noqa: E731
W, H, WAVE_H, PAD = px(560), px(150), px(76), px(18)
WAVE_W = W - 2 * PAD

root.overrideredirect(True)
root.attributes("-topmost", True)
root.configure(bg=BG, highlightthickness=1, highlightbackground=LINE)
sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
root.geometry("%dx%d+%d+%d" % (W, H, (sw - W) // 2, sh - H - px(90)))

top = tk.Frame(root, bg=BG)
top.pack(fill="x", padx=PAD, pady=(px(14), 0))
dot = tk.Label(top, text="●", bg=BG, fg=DIM, font=("Segoe UI", 8))
dot.pack(side="left")
status = tk.Label(top, text="Starting the microphone", bg=BG, fg=FG, font=("Segoe UI", 11))
status.pack(side="left", padx=(px(6), 0))
clock = tk.Label(top, text="0.0 s", bg=BG, fg=DIM, font=("Segoe UI", 10))
clock.pack(side="right")

wave = tk.Label(root, bg=BG, bd=0, highlightthickness=0)
wave.pack(padx=PAD, pady=(px(10), 0))
hint = tk.Label(root, text="Click or Enter to finish. Esc to cancel.", bg=BG, fg=DIM,
                font=("Segoe UI", 9), anchor="w", justify="left", wraplength=WAVE_W)
hint.pack(fill="x", padx=PAD, pady=(px(8), px(14)))

vals = [0.0] * COLS
pending = []
acc_cols = [0.0]
state = {"name": "starting", "t0": None, "pulse": 0.0}
text_full = {}

# Fixed parts of the render, built once.
SIG = 5.0
KR = int(SIG * 3)
KERNEL = [math.exp(-(d / SIG) ** 2 / 2) for d in range(-KR, KR + 1)]
# Newest sound on the right at full strength, the oldest on the left at 28 per cent.
_row = Image.new("L", (WAVE_W, 1))
_row.putdata([int(255 * (0.28 + 0.72 * (x / max(1, WAVE_W - 1)) ** 1.4)) for x in range(WAVE_W)])
FADE = _row.resize((WAVE_W, WAVE_H))


def out(msg):
    try:
        sys.stdout.write(msg + "\n")
        sys.stdout.flush()
    except Exception:
        pass


def finish(_e=None):
    if state["name"] in ("listening", "hearing", "starting"):
        out("stop")


def cancel(_e=None):
    out("cancel")
    root.after(50, root.destroy)


for wdg in (root, top, status, clock, wave, hint, dot):
    wdg.bind("<Button-1>", finish)
root.bind("<Return>", finish)
root.bind("<Escape>", cancel)


def smooth():
    n = len(vals)
    out_ = []
    for i in range(n):
        acc = wt = 0.0
        for d in range(-KR, KR + 1):
            t = i + d
            if 0 <= t < n:
                kw = KERNEL[d + KR]
                acc += vals[t] * kw
                wt += kw
        out_.append(acc / wt)
    return out_


def draw():
    live = state["name"] in ("listening", "hearing")
    sm = smooth()
    n = len(sm)
    bw, bh = WAVE_W * SS, WAVE_H * SS
    mid = bh / 2.0
    mask = Image.new("L", (bw, bh), 0)
    d = ImageDraw.Draw(mask)
    steps = 220
    upper, lower = [], []
    for k in range(steps + 1):
        f = k / steps
        x = f * (n - 1)
        i = int(x)
        t = x - i
        a = sm[i]
        b = sm[min(n - 1, i + 1)]
        v = a + (b - a) * (3 * t * t - 2 * t * t * t)          # smoothstep between columns
        taper = min(1.0, f * 8, (1 - f) * 14)
        h = max(SS * 0.9, v * taper * (mid - SS * 4))
        upper.append((f * bw, mid - h))
        lower.append((f * bw, mid + h))
    d.polygon(upper + lower[::-1], fill=255)
    mask = mask.resize((WAVE_W, WAVE_H), Image.LANCZOS)
    from PIL import ImageChops
    core = ImageChops.multiply(mask, FADE)
    glow = core.filter(ImageFilter.GaussianBlur(px(7)))
    img = Image.new("RGB", (WAVE_W, WAVE_H), (0, 0, 0))
    line_y = WAVE_H // 2
    ImageDraw.Draw(img).line([(0, line_y), (WAVE_W, line_y)], fill=(30, 30, 30), width=1)
    gcol = ACCENT if live else (90, 90, 90)
    img.paste(Image.new("RGB", img.size, gcol), (0, 0), glow.point(lambda v: int(v * 0.85)))
    ccol = CORE if live else (130, 130, 130)
    img.paste(Image.new("RGB", img.size, ccol), (0, 0), core)
    photo = ImageTk.PhotoImage(img)
    wave.configure(image=photo)
    wave.image = photo


def set_state(name, text):
    state["name"] = name
    status.config(text=text)
    if name in ("listening", "hearing") and state["t0"] is None:
        state["t0"] = time.time()
    dot.config(fg={"converting": FG, "done": FG, "error": "#d06060"}.get(name, DIM))
    if name == "converting":
        hint.config(text="Converting with local whisper. Nothing leaves this machine.")
    elif name == "done":
        words = text_full.get("t", "")
        hint.config(text=words, fg=FG, font=("Segoe UI", 10), justify="left")
        status.config(text="Sent to Claude")
        fit()
        root.after(1500 + 45 * len(words.split()), root.destroy)
    elif name == "error":
        hint.config(text=text, fg=FG)
        status.config(text="Did not record")
        fit()
        root.after(3500, root.destroy)
    draw()


def fit():
    """Grow the window to the text so a long transcript is never cut, bottom edge held."""
    root.update_idletasks()
    need = min(max(H, root.winfo_reqheight() + px(14)), int(sh * 0.6))
    root.geometry("%dx%d+%d+%d" % (W, need, (sw - W) // 2, sh - need - px(90)))


def tick():
    if state["t0"] and state["name"] in ("listening", "hearing"):
        clock.config(text="%.1f s" % (time.time() - state["t0"]))
    if state["name"] in ("listening", "hearing"):
        # A slow breathing pulse on the dot, between the accent and a dim Tyrian.
        state["pulse"] += 0.12
        k = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(state["pulse"]))
        dot.config(fg="#%02x%02x%02x" % tuple(int(c * k) for c in ACCENT))
    root.after(50, tick)


def scroll():
    """Thirty frames a second, about 1.3 new columns a frame, so the ribbon glides."""
    if pending:
        acc_cols[0] += max(1.33, len(pending) / 8.0)
        k = int(acc_cols[0])
        acc_cols[0] -= k
        if k:
            vals.extend(pending[:k])
            del pending[:k]
            del vals[:len(vals) - COLS]
            draw()
    root.after(33, scroll)


def reader():
    for line in sys.stdin:
        parts = line.rstrip("\n").split(" ", 2)
        if not parts or not parts[0]:
            continue
        if parts[0] == "wave":
            try:
                new = [float(x) for x in line.split()[1:]]
            except ValueError:
                continue

            def push(new=new):
                last = pending[-1] if pending else vals[-1]
                for v in new:
                    last = last * 0.6 + v * 0.4 if v > last else last * 0.88 + v * 0.12
                    pending.append(last)
            root.after(0, push)
        elif parts[0] == "state":
            name = parts[1] if len(parts) > 1 else ""
            text = parts[2] if len(parts) > 2 else ""
            if name == "done":
                text_full["t"] = text
            root.after(0, lambda n=name, t=text: set_state(n, t))
    root.after(0, lambda: root.after(2000, root.destroy))


threading.Thread(target=reader, daemon=True).start()
draw()
tick()
scroll()
root.focus_force()
root.mainloop()
