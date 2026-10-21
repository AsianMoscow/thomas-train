#!/usr/bin/env python3
"""Состояние поезда: где мы, следующая станция, стоянка, отправление.

Расписание — в schedule.json рядом со скриптом:
{
  "train": "Москва — Анапа",
  "stops": [
    {"name": "Москва Казанская", "dep": "10:50", "km": 0},
    {"name": "Рязань-2", "arr": "13:10", "dep": "13:15", "km": 198},
    {"name": "Анапа", "arr": "09:40", "km": 1634}
  ]
}
Дата и время отправления — константа DEPARTURE ниже, даты станций
вычисляются сами (переход через полночь = +1 сутки). Время местное (МСК).
Запуск: python3 train.py   |  следить каждую минуту: python3 train.py -w
"""
import json, sys, time
from datetime import datetime, timedelta
from pathlib import Path

# Отправление зашито жёстко: дата + время первой станции.
DEPARTURE = datetime(2026, 10, 21, 10, 50)

def load(path):
    """Читает станции и раскладывает время по датам.
    Даты считаются сами: каждое следующее время не может быть раньше
    предыдущего, поэтому при переходе через полночь добавляются сутки.
    Поля start_date/day в schedule.json больше не нужны и игнорируются."""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    cur = DEPARTURE
    def nxt(s):
        nonlocal cur
        h, m = map(int, s.split(":"))
        t = cur.replace(hour=h, minute=m, second=0, microsecond=0)
        while t < cur:                         # через полночь → следующие сутки
            t += timedelta(days=1)
        cur = t
        return t
    stops = []
    for i, s in enumerate(d["stops"]):
        if i == 0:
            arr, dep = None, DEPARTURE         # первая станция = зашитое отправление
        else:
            arr = nxt(s["arr"]) if "arr" in s else None
            dep = nxt(s["dep"]) if "dep" in s else None
        stops.append({"name": s["name"], "arr": arr, "dep": dep, "km": s.get("km")})
    return d.get("train", "Поезд"), stops

def fmt_delta(td):
    m = int(td.total_seconds() // 60)
    d, m = divmod(max(m, 0), 1440)
    h, m = divmod(m, 60)
    if d:
        return f"{d} д {h} ч {m} мин"
    return f"{h} ч {m} мин" if h else f"{m} мин"

def hm(dt):
    return dt.strftime("%H:%M")

def dhm(dt):
    return dt.strftime("%d.%m %H:%M")

def status(stops, now):
    first, last = stops[0], stops[-1]
    if now < first["dep"]:
        return (f"До отправления {fmt_delta(first['dep'] - now)}\n"
                f"Отправление с «{first['name']}» {dhm(first['dep'])}, "
                f"прибытие в «{last['name']}» {dhm(last['arr'])}")
    if last["arr"] and now >= last["arr"]:
        return f"Приехали: «{last['name']}» в {hm(last['arr'])}"
    for i, s in enumerate(stops):
        # стоим на станции
        if s["arr"] and s["dep"] and s["arr"] <= now < s["dep"]:
            stay = fmt_delta(s["dep"] - s["arr"])
            return (f"Стоим: «{s['name']}», стоянка {stay}, "
                    f"отправление в {hm(s['dep'])} (через {fmt_delta(s['dep'] - now)})")
        # едем к этой станции
        if s["arr"] and now < s["arr"]:
            msg = f"Следующая: «{s['name']}» через {fmt_delta(s['arr'] - now)} (в {hm(s['arr'])})"
            if s["dep"]:
                msg += f", стоим {fmt_delta(s['dep'] - s['arr'])}, отправка в {hm(s['dep'])}"
            else:
                msg += " — конечная"
            prev = stops[i - 1]["name"] if i else ""
            return f"Едем: {prev} → {s['name']}\n{msg}"
    return "Не понимаю, где мы — проверь расписание"

def distance(stops, now):
    """Пройденный км по расписанию: на стоянке — км станции, в пути — линейно по времени."""
    if any(s["km"] is None for s in stops):
        return None
    if now <= stops[0]["dep"]:
        return 0.0
    for prev, nxt in zip(stops, stops[1:]):
        if now < prev["dep"]:                  # стоим на prev
            return float(prev["km"])
        if now < nxt["arr"]:                   # едем prev → nxt
            frac = (now - prev["dep"]) / (nxt["arr"] - prev["dep"])
            return prev["km"] + frac * (nxt["km"] - prev["km"])
    return float(stops[-1]["km"])

def distance_line(stops, now):
    done = distance(stops, now)
    if done is None:
        return ""
    total = stops[-1]["km"]
    line = f"\nПройдено {done:.0f} км, осталось {total - done:.0f} км из {total}"
    start = stops[0]["dep"]
    if start < now:
        end = min(now, stops[-1]["arr"])
        hours = (end - start).total_seconds() / 3600
        line += f"\nСредняя скорость {done / hours:.0f} км/ч (со стоянками)"
    return line

def main():
    path = Path(__file__).with_name("schedule.json")
    train, stops = load(path)
    watch = "-w" in sys.argv
    while True:
        now = datetime.now()
        if watch:
            print("\033[2J\033[H", end="")
        print(f"🚆 {train}   сейчас {hm(now)}\n{status(stops, now)}{distance_line(stops, now)}")
        if not watch:
            break
        time.sleep(60)

if __name__ == "__main__":
    main()
