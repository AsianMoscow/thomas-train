#!/usr/bin/env python3
"""Окно «Где поезд» в стиле билетных сайтов. Нужны train.py и schedule.json рядом.
Запуск: python3 train_app.py
"""
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from train import load, distance, fmt_delta, hm, dhm

# Палитра в духе tutu.ru (поменяй здесь, если захочешь точнее)
GREEN = "#1DB45A"
GREEN_DARK = "#14894A"
GREEN_LIGHT = "#E8F7EE"
YELLOW = "#FFD84D"
BG = "#F2F4F5"
CARD = "#FFFFFF"
TEXT = "#1F2328"
MUTED = "#8A9199"
LINE = "#E1E4E8"
FONT = "Segoe UI" if sys.platform == "win32" else "Helvetica"


def find_state(stops, now):
    """(режим, индекс): before / moving к i / standing на i / arrived."""
    if now < stops[0]["dep"]:
        return "before", 0
    if now >= stops[-1]["arr"]:
        return "arrived", len(stops) - 1
    for i, s in enumerate(stops):
        if s["arr"] and s["dep"] and s["arr"] <= now < s["dep"]:
            return "standing", i
        if s["arr"] and now < s["arr"]:
            return "moving", i
    return "arrived", len(stops) - 1


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        base = (Path(sys.executable).parent if getattr(sys, "frozen", False)
                else Path(__file__).parent)          # в exe — папка рядом с exe
        self.train, self.stops = load(base / "schedule.json")
        self.title("Где поезд")
        self.configure(bg=BG)
        self.geometry("460x760")
        self.minsize(420, 600)
        self._build()
        self.tick()

    def lbl(self, parent, text="", size=11, bold=False, fg=TEXT, bg=CARD, **kw):
        return tk.Label(parent, text=text, fg=fg, bg=bg,
                        font=(FONT, size, "bold" if bold else "normal"), **kw)

    def _build(self):
        # шапка
        head = tk.Frame(self, bg=GREEN, padx=20, pady=14)
        head.pack(fill="x")
        self.lbl(head, "🚆 " + self.train, 15, True, "white", GREEN).pack(anchor="w")
        self.clock = self.lbl(head, "", 10, fg="#D6F5E2", bg=GREEN)
        self.clock.pack(anchor="w")

        # карточка-билет
        wrap = tk.Frame(self, bg=BG, padx=16, pady=14)
        wrap.pack(fill="x")
        card = tk.Frame(wrap, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        card.pack(fill="x")
        top = tk.Frame(card, bg=CARD, padx=18, pady=14)
        top.pack(fill="x")
        self.mode = self.lbl(top, "", 9, True, GREEN_DARK, GREEN_LIGHT, padx=8, pady=2)
        self.mode.pack(anchor="w")
        self.station = self.lbl(top, "", 20, True, wraplength=380, justify="left")
        self.station.pack(anchor="w", pady=(8, 0))
        self.eta = self.lbl(top, "", 30, True, GREEN)
        self.eta.pack(anchor="w")

        # перфорация билета
        perf = tk.Canvas(card, height=14, bg=CARD, highlightthickness=0)
        perf.pack(fill="x")
        perf.bind("<Configure>", lambda e: self._perf(perf, e.width))

        info = tk.Frame(card, bg=CARD, padx=18, pady=12)
        info.pack(fill="x")
        self.cells, self.cell_titles = {}, {}
        for col, key in enumerate(("Прибытие", "Стоянка", "Отправление")):
            f = tk.Frame(info, bg=CARD)
            f.grid(row=0, column=col, sticky="w", padx=(0, 16))
            t = self.lbl(f, key.upper(), 8, True, MUTED)
            t.pack(anchor="w")
            self.cell_titles[key] = t
            v = self.lbl(f, "—", 14, True)
            v.pack(anchor="w")
            self.cells[key] = v

        # прогресс
        prog = tk.Frame(wrap, bg=CARD, highlightbackground=LINE, highlightthickness=1,
                        padx=18, pady=12)
        prog.pack(fill="x", pady=(12, 0))
        row = tk.Frame(prog, bg=CARD)
        row.pack(fill="x")
        self.done_lbl = self.lbl(row, "", 11, True)
        self.done_lbl.pack(side="left")
        self.left_lbl = self.lbl(row, "", 11, fg=MUTED)
        self.left_lbl.pack(side="right")
        self.bar = tk.Canvas(prog, height=12, bg=CARD, highlightthickness=0)
        self.bar.pack(fill="x", pady=8)
        self.speed = self.lbl(prog, "", 10, fg=MUTED)
        self.speed.pack(anchor="w")

        # маршрут
        self.lbl(self, "МАРШРУТ", 9, True, MUTED, BG, padx=18).pack(anchor="w", pady=(4, 2))
        outer = tk.Frame(self, bg=BG, padx=16)
        outer.pack(fill="both", expand=True, pady=(0, 14))
        self.route = tk.Canvas(outer, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        sb = tk.Scrollbar(outer, command=self.route.yview)
        self.route.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.route.pack(side="left", fill="both", expand=True)
        self.route.bind("<MouseWheel>", lambda e: self.route.yview_scroll(-e.delta // 120, "units"))
        self.route.bind("<Button-4>", lambda e: self.route.yview_scroll(-1, "units"))
        self.route.bind("<Button-5>", lambda e: self.route.yview_scroll(1, "units"))
        self._scrolled = False

    def _perf(self, c, w):
        c.delete("all")
        c.create_oval(-8, -1, 8, 15, fill=BG, outline=LINE)
        c.create_oval(w - 8, -1, w + 8, 15, fill=BG, outline=LINE)
        for x in range(18, w - 14, 12):
            c.create_line(x, 7, x + 6, 7, fill=LINE, width=2)

    def tick(self):
        now = datetime.now()
        st = self.stops
        mode, i = find_state(st, now)
        s = st[i]
        self.clock.config(text=now.strftime("Сейчас %H:%M:%S · %d.%m.%Y"))

        if mode == "before":
            self.mode.config(text="ДО ОТПРАВЛЕНИЯ", fg=TEXT, bg=YELLOW)
            self.station.config(text=f"{s['name']} → {st[-1]['name']}")
            sec = int((s["dep"] - now).total_seconds())
            h, rem = divmod(sec, 3600)
            self.eta.config(text=f"{h:02d}:{rem // 60:02d}:{rem % 60:02d}", fg=GREEN)
        elif mode == "moving":
            self.mode.config(text=f"В ПУТИ  ·  {st[i-1]['name']} →", fg=GREEN_DARK, bg=GREEN_LIGHT)
            self.station.config(text=s["name"])
            self.eta.config(text="через " + fmt_delta(s["arr"] - now), fg=GREEN)
        elif mode == "standing":
            self.mode.config(text="СТОЯНКА", fg=TEXT, bg=YELLOW)
            self.station.config(text=s["name"])
            self.eta.config(text="отправка через " + fmt_delta(s["dep"] - now), fg="#E08A00")
        else:
            self.mode.config(text="ПРИБЫЛИ", fg=GREEN_DARK, bg=GREEN_LIGHT)
            self.station.config(text=s["name"])
            self.eta.config(text="Конечная 🎉", fg=GREEN)

        if mode == "before":       # до отправления — даты всей поездки
            self.cell_titles["Прибытие"].config(text="ОТПРАВЛЕНИЕ")
            self.cells["Прибытие"].config(text=dhm(st[0]["dep"]))
            self.cell_titles["Стоянка"].config(text="В ПУТИ")
            self.cells["Стоянка"].config(text=fmt_delta(st[-1]["arr"] - st[0]["dep"]))
            self.cell_titles["Отправление"].config(text="ПРИБЫТИЕ")
            self.cells["Отправление"].config(text=dhm(st[-1]["arr"]))
        else:
            self.cells["Прибытие"].config(text=hm(s["arr"]) if s["arr"] else "—")
            self.cells["Отправление"].config(text=hm(s["dep"]) if s["dep"] else "—")
            self.cells["Стоянка"].config(
                text=fmt_delta(s["dep"] - s["arr"]) if s["arr"] and s["dep"] else "—")
            for k in self.cells:
                self.cell_titles[k].config(text=k.upper())

        # прогресс
        done = distance(st, now) or 0
        total = st[-1]["km"] or 1
        self.done_lbl.config(text=f"Пройдено {done:.0f} км")
        self.left_lbl.config(text=f"осталось {total - done:.0f} км")
        self._bar(done / total)
        if now > st[0]["dep"]:
            hrs = (min(now, st[-1]["arr"]) - st[0]["dep"]).total_seconds() / 3600
            left = fmt_delta(st[-1]["arr"] - now) if now < st[-1]["arr"] else "0 мин"
            self.speed.config(text=f"Средняя скорость {done / hrs:.0f} км/ч  ·  до конечной {left}")
        else:
            self.speed.config(text="")

        self._draw_route(mode, i)
        self.after(1000, self.tick)

    def _bar(self, frac):
        c = self.bar
        c.update_idletasks()
        w = max(c.winfo_width(), 10)
        c.delete("all")
        c.create_rectangle(0, 3, w, 9, fill=LINE, outline="")
        x = int(w * max(0, min(frac, 1)))
        c.create_rectangle(0, 3, x, 9, fill=GREEN, outline="")
        c.create_oval(x - 6, 0, x + 6, 12, fill="white", outline=GREEN, width=3)

    def _draw_route(self, mode, cur):
        c = self.route
        c.delete("all")
        w = max(c.winfo_width(), 300)
        rowh, x0, y = 54, 30, 24
        for j, s in enumerate(self.stops):
            passed = j < cur or (j == cur and mode == "arrived")
            here = j == cur and mode in ("standing", "moving", "before")
            color = MUTED if passed else TEXT
            if j < len(self.stops) - 1:
                seg_done = j < cur or (j == cur and mode == "standing")
                c.create_line(x0, y, x0, y + rowh, width=4,
                              fill=GREEN if seg_done or passed else LINE)
            if here:
                c.create_oval(x0 - 10, y - 10, x0 + 10, y + 10, fill=GREEN_LIGHT, outline="")
                c.create_oval(x0 - 6, y - 6, x0 + 6, y + 6, fill=GREEN, outline="white", width=2)
            else:
                c.create_oval(x0 - 5, y - 5, x0 + 5, y + 5,
                              fill=GREEN if passed else CARD, outline=GREEN if passed else MUTED, width=2)
            c.create_text(x0 + 22, y - 8, text=s["name"], anchor="w", fill=color,
                          font=(FONT, 11, "bold" if here else "normal"))
            day0 = self.stops[0]["dep"].date()
            times = " – ".join(hm(t) + (f" ({t:%d.%m})" if t.date() != day0 else "")
                               for t in (s["arr"], s["dep"]) if t)
            stay = f"  ·  стоянка {fmt_delta(s['dep'] - s['arr'])}" if s["arr"] and s["dep"] else ""
            c.create_text(x0 + 22, y + 10, text=times + stay, anchor="w", fill=MUTED, font=(FONT, 9))
            if s["km"] is not None:
                c.create_text(w - 16, y, text=f"{s['km']} км", anchor="e", fill=MUTED, font=(FONT, 9))
            y += rowh
        c.configure(scrollregion=(0, 0, w, y))
        if not self._scrolled:          # один раз прокрутить к текущей станции
            self._scrolled = True
            self.after(50, lambda: c.yview_moveto(max(cur - 2, 0) / len(self.stops)))


if __name__ == "__main__":
    App().mainloop()
