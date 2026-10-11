#!/usr/bin/env python3
"""Генерирует схемы подключения docs/wiring/*.svg.

Пины плат и модулей заданы здесь в физическом порядке (вид сверху, антенна вверху,
USB внизу) и должны совпадать с firmware/empolimer/board.h. После правки:

    python3 docs/wiring/generate.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parent

# Цвета проводов — как советуем брать провода при сборке.
C5V, C3V3, CGND = "#e65100", "#d32f2f", "#212121"
CDHT, CLED, CSCK, CMOSI, CMISO, CCS, CBAT, CUSB = (
    "#f9a825", "#2e7d32", "#1565c0", "#6a1b9a", "#00838f", "#ad1457", "#795548", "#757575")

LEGEND = [
    (C5V, "+5 В"), (C3V3, "+3,3 В"), (CGND, "GND (минус)"), (CDHT, "данные датчика"),
    (CLED, "данные ленты"), (CSCK, "SD SCK"), (CMOSI, "SD MOSI"), (CMISO, "SD MISO"),
    (CCS, "SD CS"), (CBAT, "батарея"),
]

PIN_STEP = 28


class Svg:
    def __init__(self, width: int, height: int):
        self.width, self.height = width, height
        self.back: list[str] = []   # провода — под модулями
        self.front: list[str] = []

    def text(self, x, y, s, size=13, anchor="start", weight="normal", color="#24292f", layer=None):
        (layer if layer is not None else self.front).append(
            f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" '
            f'fill="{color}">{escape(s)}</text>')

    def rect(self, x, y, w, h, fill="#fff", stroke="#57606a", rx=6, width=1.5, dash=None, layer=None):
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        (layer if layer is not None else self.front).append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
                          f'stroke="{stroke}" stroke-width="{width}"{extra}/>')

    def wire(self, points, color, width=3.2):
        path = " ".join(f"{x},{y}" for x, y in points)
        self.back.append(f'<polyline points="{path}" fill="none" stroke="#fff" stroke-width="{width + 3}" '
                         'stroke-linejoin="round" stroke-linecap="round"/>')
        self.back.append(f'<polyline points="{path}" fill="none" stroke="{color}" stroke-width="{width}" '
                         'stroke-linejoin="round" stroke-linecap="round"/>')
        for x, y in (points[0], points[-1]):
            self.back.append(f'<circle cx="{x}" cy="{y}" r="4.5" fill="{color}" stroke="#fff" stroke-width="1.5"/>')

    def resistor(self, x, y, label, vertical=False, label_left=False):
        """Резистор поверх провода с центром в (x, y)."""
        w, h = (14, 34) if vertical else (34, 14)
        self.rect(x - w / 2, y - h / 2, w, h, fill="#fff3e0", stroke="#8d6e63", rx=3)
        if vertical:
            self.text(x - 12 if label_left else x + 12, y + 4, label, size=12, color="#5d4037",
                      anchor="end" if label_left else "start")
        else:
            self.text(x, y - 12, label, size=12, anchor="middle", color="#5d4037")

    def save(self, name: str, title: str):
        body = "\n".join(self.back + self.front)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} {self.height}" '
               f'width="{self.width}" height="{self.height}" font-family="Arial, Helvetica, sans-serif">\n'
               f'<title>{escape(title)}</title>\n'
               f'<rect width="100%" height="100%" fill="#ffffff"/>\n{body}\n</svg>\n')
        (OUT / name).write_text(svg, encoding="utf-8")
        print("Сохранено:", OUT / name)


@dataclass
class Board:
    """Плата с двумя рядами пинов. left/right — подписи сверху вниз."""

    name: str
    left: list[str]
    right: list[str]
    x: int
    y: int
    width: int = 190
    used: set = field(default_factory=set)

    @property
    def top(self):
        return self.y + 60

    def pin(self, label: str, side: str = "") -> tuple[int, int]:
        """Координаты пина; side — 'L' или 'R', если подпись встречается на обеих сторонах;
        для повторяющихся подписей можно указать 'GND#2' — второй сверху."""
        base, _, nth = label.partition("#")
        nth = int(nth or 1)
        for column, names, x in (("L", self.left, self.x + 16), ("R", self.right, self.x + self.width - 16)):
            if side and side != column:
                continue
            hits = [i for i, n in enumerate(names) if n.split(" ")[0] == base]
            if len(hits) >= nth:
                self.used.add((column, hits[nth - 1]))
                return x, self.top + hits[nth - 1] * PIN_STEP
        raise KeyError(label)

    def draw(self, svg: Svg, subtitle: str):
        rows = max(len(self.left), len(self.right))
        height = 60 + rows * PIN_STEP + 50
        svg.rect(self.x, self.y, self.width, height, fill="#263238", stroke="#11171a", rx=8, width=2)
        # антенна и USB — для ориентации платы
        svg.rect(self.x + 30, self.y + 8, self.width - 60, 30, fill="#cfd8dc", stroke="#90a4ae", rx=3)
        svg.text(self.x + self.width / 2, self.y + 28, "антенна", size=11, anchor="middle", color="#455a64")
        usb_y = self.y + height - 26
        svg.rect(self.x + self.width / 2 - 26, usb_y, 52, 34, fill="#b0bec5", stroke="#78909c", rx=3)
        svg.text(self.x + self.width / 2, usb_y + 22, "USB", size=12, anchor="middle", weight="bold", color="#37474f")
        svg.text(self.x + self.width / 2, self.y + height / 2 - 8, self.name, size=15, anchor="middle",
                 weight="bold", color="#eceff1")
        svg.text(self.x + self.width / 2, self.y + height / 2 + 12, subtitle, size=11, anchor="middle",
                 color="#b0bec5")
        for column, names in (("L", self.left), ("R", self.right)):
            for i, label in enumerate(names):
                px = self.x + 16 if column == "L" else self.x + self.width - 16
                py = self.top + i * PIN_STEP
                used = (column, i) in self.used
                svg.front.append(f'<circle cx="{px}" cy="{py}" r="6" fill="{"#ffd54f" if used else "#90a4ae"}" '
                                 'stroke="#11171a" stroke-width="1.5"/>')
                tx = px + 12 if column == "L" else px - 12
                svg.text(tx, py + 4, label, size=12, anchor="start" if column == "L" else "end",
                         weight="bold" if used else "normal", color="#ffffff" if used else "#90a4ae")
        return height


class Module:
    """Модуль с рядом выводов на одной стороне (left/right/top/bottom) в физическом порядке."""

    def __init__(self, svg: Svg, x, y, w, h, title, subtitle, pins, side="left", fill="#f6f8fa"):
        self.pins = {}
        svg.rect(x, y, w, h, fill=fill, stroke="#57606a", rx=8, width=1.8)
        shift = 22 if side == "top" else 0  # подписи выводов сверху — название ниже них
        svg.text(x + w / 2, y + 22 + shift, title, size=14, anchor="middle", weight="bold")
        for i, line in enumerate(subtitle.split("\n") if subtitle else []):
            svg.text(x + w / 2, y + 40 + shift + i * 15, line, size=11, anchor="middle", color="#57606a")
        n = len(pins)
        lines = len(subtitle.split("\n")) if subtitle else 0
        start = 34 + 15 * lines
        for i, name in enumerate(pins):
            if side in ("left", "right"):
                step = (h - start) / max(n, 1)
                py = y + start + step * (i + 0.5)
                px = x if side == "left" else x + w
                tx, anchor = (px + 10, "start") if side == "left" else (px - 10, "end")
                svg.text(tx, py + 4, name, size=12, anchor=anchor, weight="bold")
            else:
                step = w / n
                px = x + step * (i + 0.5)
                py = y if side == "top" else y + h
                svg.text(px, py + (16 if side == "top" else -8), name, size=12, anchor="middle", weight="bold")
            svg.front.append(f'<rect x="{px - 5}" y="{py - 5}" width="10" height="10" fill="#ffd54f" '
                             'stroke="#57606a"/>')
            self.pins[name] = (round(px), round(py))

    def __getitem__(self, name):
        return self.pins[name]


def header(svg: Svg, title: str, subtitle: str):
    svg.text(30, 40, title, size=22, weight="bold")
    svg.text(30, 62, subtitle, size=13, color="#57606a")


def legend(svg: Svg, x, y, items=LEGEND):
    svg.text(x, y, "Цвета проводов", size=13, weight="bold")
    for i, (color, label) in enumerate(items):
        cy = y + 20 + i * 20
        svg.back.append(f'<line x1="{x}" y1="{cy}" x2="{x + 30}" y2="{cy}" stroke="{color}" stroke-width="4"/>')
        svg.text(x + 38, cy + 4, label, size=12)


def notes(svg: Svg, x, y, lines, width=520, title="Проверьте перед включением"):
    height = 34 + len(lines) * 18
    svg.rect(x, y, width, height, fill="#fff8e1", stroke="#f9a825", rx=8)
    svg.text(x + 14, y + 22, title, size=13, weight="bold", color="#7a5300")
    for i, line in enumerate(lines):
        svg.text(x + 14, y + 44 + i * 18, line, size=12, color="#3d2c00")


# --- общие элементы ---

def flag(svg: Svg, x, y, text, color, side="right"):
    """Метка цепи питания на выводе: «→ VIN (5 В)». Провод по метке — к выводу с той же подписью."""
    length = 26
    w = 8 + 6.6 * len(text)
    if side == "right":
        sx, tx = x + length, x + length
        box_x = tx
    else:
        sx, tx = x - length, x - length - w
        box_x = tx
    svg.wire([(x, y), (sx, y)], color, width=3)
    svg.rect(box_x, y - 11, w, 22, fill="#ffffff", stroke=color, rx=11, width=2)
    svg.text(box_x + w / 2, y + 4, text, size=11.5, anchor="middle", weight="bold", color=color)


def crossings(wires, lanes, x_from, x_to):
    """Сколько пересечений дадут провода «горизонталь → дорожка → горизонталь»."""
    segs_v, segs_h = [], []
    for (sy, ey), lane in zip(wires, lanes):
        segs_v.append((lane, min(sy, ey), max(sy, ey)))
        segs_h.append((sy, min(x_from, lane), max(x_from, lane)))
        segs_h.append((ey, min(lane, x_to), max(lane, x_to)))
    count = 0
    for i, (vx, y1, y2) in enumerate(segs_v):
        for j, (hy, x1, x2) in enumerate(segs_h):
            if j // 2 != i and x1 < vx < x2 and y1 < hy < y2:
                count += 1
    return count


def route(svg: Svg, items, lanes, x_to):
    """items: (точка на плате, точка на модуле, цвет). Дорожки распределяются с минимумом пересечений."""
    from itertools import permutations
    x_from = items[0][0][0]
    wires = [(a[1], b[1]) for a, b, _ in items]
    best = min(permutations(lanes[:len(items)]), key=lambda order: crossings(wires, order, x_from, x_to))
    for (a, b, color), lane in zip(items, best):
        svg.wire([a, (lane, a[1]), (lane, b[1]), b], color)


def dht_module(svg, x, y):
    return Module(svg, x, y, 190, 140, "Датчик DHT11 / DHT22", "модуль на плате, 3 вывода;\nподписи: S/DATA, +/VCC, −/GND",
                  ["S (DATA)", "+ (VCC)", "− (GND)"], side="left", fill="#e3f2fd")


def sd_module(svg, x, y):
    # Порядок выводов распространённого модуля microSD (Catalex): GND VCC MISO MOSI SCK CS
    return Module(svg, x, y, 210, 250, "Модуль microSD", "со стабилизатором 3,3 В на плате\n→ питание 5 В",
                  ["GND", "VCC", "MISO", "MOSI", "SCK", "CS"], side="left", fill="#ede7f6")


def power_section(svg, x, y, strip_note):
    """Блок питания и лента: отдельная цепь 5 В, общий GND с платой.
    Выводы ленты сверху: DIN подходит сверху, +5V — слева, GND — в обход справа, без пересечений."""
    psu = Module(svg, x, y, 200, 110, "Блок питания 5 В", "≥ 2 А на 30 светодиодов",
                 ["+5V", "GND"], side="right", fill="#fff3e0")
    strip = Module(svg, x + 400, y + 20, 330, 90, "Лента WS2812B", strip_note,
                   ["+5V", "DIN", "GND"], side="top", fill="#e8f5e9")
    (px5, py5), (pxg, pyg) = psu["+5V"], psu["GND"]
    (sx5, sy5), (sxg, syg) = strip["+5V"], strip["GND"]
    svg.wire([(px5, py5), (px5 + 40, py5), (px5 + 40, sy5 - 22), (sx5, sy5 - 22), (sx5, sy5)], C5V)
    right = x + 400 + 330 + 25
    bottom = y + 135
    svg.wire([(pxg, pyg), (pxg + 20, pyg), (pxg + 20, bottom), (right, bottom), (right, syg - 30), (sxg, syg - 30),
              (sxg, syg)], CGND)
    flag(svg, pxg + 20, bottom, "к GND платы", CGND, side="left")
    return psu, strip
def rpi_box(svg, x, y):
    svg.rect(x, y, 240, 54, fill="#fce4ec", stroke="#ad1457", rx=8)
    svg.text(x + 120, y + 24, "Raspberry Pi — порт USB", size=13, anchor="middle", weight="bold")
    svg.text(x + 120, y + 42, "кабель USB с передачей данных", size=11, anchor="middle", color="#57606a")
    return x + 120, y


def battery_box(svg, x, y, adc_pin, gnd_pin, divider_text, r1="15 кОм"):
    """Делитель напряжения батареи: Бат+ → R1 → узел → R2 → GND; узел → вход АЦП."""
    svg.rect(x, y, 300, 170, fill="#efebe9", stroke="#795548", rx=8, dash="6 4", layer=svg.back)
    svg.back.insert(0, svg.back.pop())  # рамка под проводами
    svg.text(x + 14, y + 22, "Батарея — необязательно", size=13, weight="bold")
    svg.text(x + 14, y + 40, "battery.enabled = true", size=11, color="#57606a")
    node_x = x + 230
    plus_y, minus_y = y + 75, y + 140
    svg.text(x + 14, plus_y + 4, "Батарея +", size=12, weight="bold")
    svg.text(x + 14, minus_y + 4, "Батарея −", size=12, weight="bold")
    ax, ay = adc_pin
    svg.wire([(x + 90, plus_y), (node_x, plus_y), (node_x, ay), (ax, ay)], CBAT)
    svg.resistor(x + 160, plus_y, f"R1 {r1}")
    svg.wire([(node_x, plus_y), (node_x, minus_y)], CBAT)
    svg.resistor(node_x, (plus_y + minus_y) / 2, "R2 10 кОм", vertical=True)
    if gnd_pin:
        gx, gy = gnd_pin
        svg.wire([(x + 90, minus_y), (node_x + 40, minus_y), (node_x + 40, gy), (gx, gy)], CGND)
    else:
        svg.wire([(x + 90, minus_y), (node_x, minus_y)], CGND)
        flag(svg, node_x, minus_y, "→ GND", CGND)
    svg.back.append(f'<circle cx="{node_x}" cy="{plus_y}" r="5" fill="{CBAT}"/>')
    svg.back.append(f'<circle cx="{node_x}" cy="{minus_y}" r="5" fill="{CGND}"/>')
    svg.text(x, y + 190, divider_text, size=12, color="#5d4037")


def devkit(name, title, subtitle, board, pins, file_name, notes_lines, sd_y=470, dht_y=230):
    """Общая раскладка для NodeMCU и ESP32 DevKit. pins — пины платы для каждой роли."""
    svg = Svg(1240, 1010)
    header(svg, title, subtitle)
    for role, (label, side) in pins.items():
        if label:
            board.pin(label, side)
    height = board.draw(svg, name)
    p = {role: board.pin(label, side) for role, (label, side) in pins.items() if label}
    right = board.x + board.width

    notes(svg, 720, 84, notes_lines, width=500, title="Перед включением")

    # Датчик: данные — проводом, питание 3,3 В и GND — проводами к соседним пинам
    dht = dht_module(svg, 960, dht_y)
    route(svg, [(p["dht"], dht["S (DATA)"], CDHT), (p["dht_vcc"], dht["+ (VCC)"], C3V3),
                (p["dht_gnd"], dht["− (GND)"], CGND)], [880, 900, 920], dht["S (DATA)"][0])

    # SD: сигналы проводами, питание метками
    sd = sd_module(svg, 990, sd_y)
    route(svg, [(p["sck"], sd["SCK"], CSCK), (p["miso"], sd["MISO"], CMISO), (p["mosi"], sd["MOSI"], CMOSI),
                (p["cs"], sd["CS"], CCS)], [800, 820, 840, 860], sd["GND"][0])
    flag(svg, sd["GND"][0], sd["GND"][1], "→ GND платы", CGND, side="left")
    flag(svg, sd["VCC"][0], sd["VCC"][1], f"→ {pins['vin'][0]} (5 В)", C5V, side="left")
    flag(svg, *p["vin"], "→ VCC модуля SD", C5V, side="left")
    side_of = lambda role: "left" if pins[role][1] == "L" else "right"
    if pins["psu_gnd"] == pins["sd_gnd"]:
        flag(svg, *p["sd_gnd"], "→ GND модуля SD и блока питания", CGND, side=side_of("sd_gnd"))
    else:
        flag(svg, *p["sd_gnd"], "→ GND модуля SD", CGND, side=side_of("sd_gnd"))
        flag(svg, *p["psu_gnd"], "→ GND блока питания", CGND, side=side_of("psu_gnd"))

    # Лента: данные через 330 Ом
    psu, strip = power_section(svg, 40, 850, "к началу ленты: вход DIN, стрелки — от вас")
    lx, ly = p["led"]
    lane = right + 70 if pins["led"][1] == "R" else 245
    out_x = 1215 if pins["led"][1] == "R" else 420
    din_x, din_y = strip["DIN"]
    if pins["led"][1] == "R":
        path = [(lx, ly), (lane, ly), (lane, 210), (out_x, 210), (out_x, 830), (din_x, 830), (din_x, din_y)]
        svg.wire(path, CLED)
        svg.resistor(out_x, 760, "330 Ом", vertical=True, label_left=True)
    else:
        path = [(lx, ly), (lane, ly), (lane, 830), (din_x, 830), (din_x, din_y)]
        svg.wire(path, CLED)
        svg.resistor(lane, 780, "330 Ом", vertical=True)

    battery_box(svg, 40, 235, p["bat"], p.get("bat_gnd"), "в config.json: divider = (R1 + R2) / R2 = 2,5")

    rx, ry = rpi_box(svg, board.x + board.width / 2 - 120, board.y + height + 30)
    ux, uy = board.x + board.width / 2, board.y + height + 8
    svg.wire([(ux, uy), (ux, ry)], CUSB, width=6)

    legend(svg, 40, 470)
    for i, line in enumerate(["Метка «→ VIN (5 В)»: провод", "к выводу с той же подписью.",
                              "Все GND платы соединены —", "подходит любой."]):
        svg.text(40, 700 + i * 16, line, size=12, color="#57606a")
    svg.save(file_name, title)


def nodemcu():
    board = Board("NodeMCU", x=480, y=150,
                  left=["A0", "RSV (G)", "RSV (VU)", "SD3", "SD2", "SD1", "CMD", "SD0", "CLK", "GND", "3V3", "EN",
                        "RST", "GND", "VIN"],
                  right=["D0", "D1", "D2", "D3", "D4", "3V3", "GND", "D5", "D6", "D7", "D8", "RX", "TX", "GND", "3V3"])
    devkit("v2 / v3", "Подключение: NodeMCU ESP8266 (ESP-12E)",
           "Вид сверху: антенна вверху, USB внизу. Подписи пинов совпадают у NodeMCU v2 (Amica) и v3 (LoLin): "
           "у v3 второй и третий слева — G и VU.",
           board,
           {"dht": ("D4", "R"), "dht_vcc": ("3V3#1", "R"), "dht_gnd": ("GND#1", "R"),
            "sck": ("D5", "R"), "miso": ("D6", "R"), "mosi": ("D7", "R"), "cs": ("D8", "R"),
            "sd_gnd": ("GND#2", "R"), "vin": ("VIN", "L"), "led": ("D2", "R"),
            "psu_gnd": ("GND#2", "L"), "bat": ("A0", "L"), "bat_gnd": ("GND#1", "L")},
           "nodemcu.svg",
           ["1. Лента — от отдельного блока 5 В; GND блока соединён с GND платы.",
            "2. Резистор 330 Ом — в разрыв провода D2 → DIN ленты.",
            "3. Модуль SD со стабилизатором — VCC к VIN (5 В), не к 3V3.",
            "4. Батарея: на A0 не больше 3,3 В — только через делитель."])


def esp32():
    board = Board("ESP32", x=480, y=150, width=200,
                  left=["EN", "VP", "VN", "D34", "D35", "D32", "D33", "D25", "D26", "D27", "D14", "D12", "D13",
                        "GND", "VIN"],
                  right=["D23", "D22", "TX0", "RX0", "D21", "D19", "D18", "D5", "TX2", "RX2", "D4", "D2", "D15",
                         "GND", "3V3"])
    devkit("DevKit V1 · 30 pin", "Подключение: ESP32 DevKit V1 (30 пинов)",
           "Вид сверху: антенна вверху, USB внизу. У плат на 38 пинов порядок другой — подключайте по подписям "
           "(D4 = GPIO4), а не по месту на плате.",
           board,
           {"dht": ("D4", "R"), "dht_vcc": ("3V3", "R"), "dht_gnd": ("GND", "R"),
            "sck": ("D18", "R"), "miso": ("D19", "R"), "mosi": ("D23", "R"), "cs": ("D5", "R"),
            "sd_gnd": ("GND", "L"), "vin": ("VIN", "L"), "led": ("D13", "L"),
            "psu_gnd": ("GND", "L"), "bat": ("D34", "L"), "bat_gnd": ("", "")},
           "esp32.svg",
           ["1. Лента — от отдельного блока 5 В; GND блока соединён с GND платы.",
            "2. Резистор 330 Ом — в разрыв провода D13 → DIN ленты.",
            "3. Модуль SD со стабилизатором — VCC к VIN (5 В), не к 3V3.",
            "4. Батарея: на D34 не больше 3,3 В — только через делитель."],
           sd_y=195, dht_y=462)


if __name__ == "__main__":
    nodemcu()
    esp32()
