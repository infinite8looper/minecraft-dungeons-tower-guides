"""Build the hyperlinked tower-guide PDF for the Remarkable Paper Pro.

Usage:
    python scripts/build_pdf.py [--date YYYY-MM-DD] [--out PATH]

Reads data/towers.json, assets/, and notes/towers/*.md. The cover shows the
guide that is live for --date (default: today), reproducing the
spreadsheet's "Guide of the week" behavior; a schedule page maps the next
29 weeks to their towers so the document stays usable between rebuilds.
Per-tower notes files are rendered into each tower's notes page, so they
persist across the 29-week cycle; missing notes files are created from a
template.
"""

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

sys.path.insert(0, str(Path(__file__).parent))
from cycle import ANCHOR, CYCLE_WEEKS

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "towers.json"
ICONS = ROOT / "assets" / "icons"
FONTS = ROOT / "assets" / "fonts"
NOTES = ROOT / "notes" / "towers"

# Remarkable Paper Pro: 1620 x 2160 px at 229 ppi
PAGE_W, PAGE_H = 1620 / 229 * 72, 2160 / 229 * 72
MARGIN = 30

INK = HexColor("#1d1b16")
WHITE = HexColor("#ffffff")
FAINT = HexColor("#8a8578")
PARCHMENT = HexColor("#f1ede2")
GRASS = HexColor("#3e8948")
GRASS_DARK = HexColor("#2c5e33")
GRASS_PALE = HexColor("#dcead8")
GRASS_LIGHT = HexColor("#c8e6b8")
STONE = HexColor("#4a4438")
STONE_LIGHT = HexColor("#cfc8b8")
GOLD = HexColor("#b8860b")
BOSS_RED = HexColor("#a63a26")
BOSS_PALE = HexColor("#f5ded6")
MERCH_BLUE = HexColor("#2f6584")
MERCH_PALE = HexColor("#dbe8f0")
RULE = HexColor("#c9c2b2")
WRITE_RULE = HexColor("#ddd7c7")

MC = "Monocraft"  # the one font, used everywhere

# consistent type scale
S_TITLE = 30
S_H1 = 24
S_H2 = 13
S_H3 = 10
S_BODY = 8
S_SMALL = 6.5

ROWS_PER_PAGE = 15
ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V"}

NOTES_TEMPLATE = """\
<!-- Notes for Tower {n}. Anything you write below this line is rendered on
Tower {n}'s notes page the next time the PDF is built, so adjustments you
make during one cycle are waiting for you the next time this tower is up.
Plain lines and "- " bullets are supported. -->
"""


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def icon_path(name):
    p = ICONS / f"{slug(name)}.png"
    return p if p.exists() else None


def load_notes(n):
    NOTES.mkdir(parents=True, exist_ok=True)
    path = NOTES / f"tower-{n:02d}.md"
    if not path.exists():
        path.write_text(NOTES_TEMPLATE.format(n=n))
    text = re.sub(r"<!--.*?-->", "", path.read_text(), flags=re.DOTALL)
    return [ln.rstrip() for ln in text.strip().splitlines()]


def fmt_date(d):
    return d.strftime("%b %-d, %Y").upper()


def fmt_short(d):
    return d.strftime("%b %-d").upper()


def next_live(n, today):
    """Monday of the next week tower n is (or currently is) live."""
    weeks = (today - ANCHOR).days // 7
    monday = ANCHOR + datetime.timedelta(weeks=weeks)
    cur = weeks % CYCLE_WEEKS or CYCLE_WEEKS
    delta = (n - cur) % CYCLE_WEEKS
    return monday + datetime.timedelta(weeks=delta), delta == 0


def enchant_text(enchants):
    parts = []
    for e in enchants:
        t = f" {ROMAN.get(e['tier'], e['tier'])}" if e.get("tier") else ""
        parts.append(e["name"] + t)
    return ", ".join(parts)


def boss_label(b):
    return (f"{b['count']}x " if b["count"] > 1 else "") + b["name"]


class Builder:
    def __init__(self, data, today, out):
        self.data = data
        self.today = today
        self.current = ((today - ANCHOR).days // 7) % CYCLE_WEEKS or CYCLE_WEEKS
        self.c = Canvas(str(out), pagesize=(PAGE_W, PAGE_H),
                        initialFontName=MC, initialFontSize=S_BODY)
        self.c.setTitle("Minecraft Dungeons Tower Guides")
        self.c.setAuthor("Guide data by LordForce; PDF by tower-guide-builder")
        self.page_num = 0

    # -- low-level helpers ---------------------------------------------------

    def fit(self, text, size, max_w, min_size=5.5):
        while size > min_size and self.c.stringWidth(text, MC, size) > max_w:
            size -= 0.5
        return size

    def wrap(self, text, size, max_w, max_lines=2):
        """Greedy word-wrap into at most max_lines, ellipsizing overflow."""
        lines, cur = [], ""
        for word in text.split():
            cand = f"{cur} {word}".strip()
            if not cur or self.c.stringWidth(cand, MC, size) <= max_w:
                cur = cand
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            last = lines[-1]
            while (" " in last and self.c.stringWidth(
                    last + "...", MC, size) > max_w):
                last = last.rsplit(" ", 1)[0]
            lines[-1] = last + "..."
        return lines

    def text(self, x, y, s, size=S_BODY, color=INK, max_w=None, align="left"):
        if max_w:
            size = self.fit(s, size, max_w)
        self.c.setFont(MC, size)
        self.c.setFillColor(color)
        if align == "left":
            self.c.drawString(x, y, s)
        elif align == "right":
            self.c.drawRightString(x, y, s)
        else:
            self.c.drawCentredString(x, y, s)

    def lines_block(self, x, y_center, lines, line_h=None):
        """Draw [(text, size, color, dx)] stacked, vertically centered."""
        if not lines:
            return
        lh = line_h or max(sz for _, sz, _, _ in lines) + 3
        top = y_center + (len(lines) * lh) / 2 - lh * 0.75
        for i, (s, sz, col, dx) in enumerate(lines):
            self.text(x + dx, top - i * lh, s, sz, col)

    def icon(self, name, x, y, size):
        path = icon_path(name) if not str(name).endswith(".png") else \
            ICONS / name
        if not path or not Path(path).exists():
            return False
        try:
            self.c.drawImage(str(path), x, y, size, size, mask="auto",
                             preserveAspectRatio=True, anchor="c")
            return True
        except Exception:
            return False

    def link_box(self, rect, dest, fill, label, size=S_H2, text_color=None):
        x, y, w, h = rect
        self.c.setFillColor(fill)
        self.c.roundRect(x, y, w, h, 3, stroke=0, fill=1)
        self.text(x + w / 2, y + h / 2 - size * 0.35, label, size,
                  text_color or WHITE, max_w=w - 10, align="center")
        self.c.linkAbsolute("", dest, (x, y, x + w, y + h))

    def footer(self, tower=None):
        y = 12
        c = self.c
        c.setStrokeColor(RULE)
        c.setLineWidth(0.6)
        c.line(MARGIN, y + 12, PAGE_W - MARGIN, y + 12)
        self.text(PAGE_W - MARGIN, y, str(self.page_num), S_SMALL, FAINT,
                  align="right")
        if tower:
            prev_t = tower - 1 if tower > 1 else CYCLE_WEEKS
            next_t = tower + 1 if tower < CYCLE_WEEKS else 1
            labels = [(f"<< TOWER {prev_t}", f"tower-{prev_t}"),
                      ("INDEX", "index"),
                      (f"TOWER {next_t} >>", f"tower-{next_t}")]
            positions = [0.22, 0.5, 0.78]
        else:
            labels = [("INDEX", "index"), ("SCHEDULE", "schedule")]
            positions = [0.38, 0.62]
        for (label, dest), frac in zip(labels, positions):
            w = c.stringWidth(label, MC, S_BODY) + 8
            x = PAGE_W * frac - w / 2
            self.text(PAGE_W * frac, y, label, S_BODY, GRASS_DARK,
                      align="center")
            c.linkAbsolute("", dest, (x, y - 3, x + w, y + 10))

    def new_page(self):
        if self.page_num:
            self.c.showPage()
        self.page_num += 1

    # -- pages ---------------------------------------------------------------

    def cover(self):
        self.new_page()
        c = self.c
        c.bookmarkPage("cover")
        c.addOutlineEntry("Guide of the Week", "cover", 0)
        c.setFillColor(GRASS_DARK)
        c.rect(0, PAGE_H - 150, PAGE_W, 150, stroke=0, fill=1)
        self.text(PAGE_W / 2, PAGE_H - 78, "MINECRAFT DUNGEONS", S_TITLE,
                  WHITE, align="center")
        self.text(PAGE_W / 2, PAGE_H - 112, "TOWER GUIDES", 20, GRASS_LIGHT,
                  align="center")

        monday, _ = next_live(self.current, self.today)
        sunday = monday + datetime.timedelta(days=6)
        y = PAGE_H - 210
        self.text(PAGE_W / 2, y, "GUIDE OF THE WEEK", S_H2, GOLD,
                  align="center")
        self.text(PAGE_W / 2, y - 54, f"TOWER {self.current}", 44, INK,
                  align="center")
        self.text(PAGE_W / 2, y - 76,
                  f"{fmt_date(monday)} - {fmt_date(sunday)}", S_H3, FAINT,
                  align="center")
        self.link_box((PAGE_W / 2 - 110, y - 126, 220, 34),
                      f"tower-{self.current}", GRASS,
                      f"OPEN TOWER {self.current} >>", size=S_H2)
        self.link_box((PAGE_W / 2 - 110, y - 162, 106, 36 - 8),
                      "index", STONE, "INDEX", size=S_H3)
        self.link_box((PAGE_W / 2 + 4, y - 162, 106, 36 - 8),
                      "schedule", STONE, "SCHEDULE", size=S_H3)

        # mini index: chips for all towers
        y0 = y - 218
        self.text(PAGE_W / 2, y0 + 18, "ALL TOWERS", S_H3, FAINT,
                  align="center")
        cols, cw, ch, gap = 6, 64, 26, 9
        grid_w = cols * cw + (cols - 1) * gap
        x0 = (PAGE_W - grid_w) / 2
        for i, t in enumerate(self.data["towers"]):
            n = t["number"]
            gx = x0 + (i % cols) * (cw + gap)
            gy = y0 - 24 - (i // cols) * (ch + gap)
            cur = n == self.current
            self.link_box((gx, gy, cw, ch), f"tower-{n}",
                          GOLD if cur else PARCHMENT, f"T{n}", size=S_H3,
                          text_color=WHITE if cur else INK)

        self.text(PAGE_W / 2, 78,
                  "The cover updates when the PDF is rebuilt (weekly); the",
                  S_SMALL, FAINT, align="center")
        self.text(PAGE_W / 2, 67,
                  "SCHEDULE page maps dates to towers if this copy is old.",
                  S_SMALL, FAINT, align="center")
        self.text(PAGE_W / 2, 52,
                  f"Built {fmt_date(self.today)} - guide data by LordForce - "
                  "icons: minecraft.wiki (CC BY-NC-SA 3.0)",
                  S_SMALL, FAINT, align="center", max_w=PAGE_W - 2 * MARGIN)
        self.footer()

    def index(self):
        self.new_page()
        c = self.c
        c.bookmarkPage("index")
        c.addOutlineEntry("Tower Index", "index", 0)
        self.text(MARGIN, PAGE_H - 58, "TOWER INDEX", 22, GRASS_DARK)
        self.text(PAGE_W - MARGIN, PAGE_H - 58,
                  f"THIS WEEK: TOWER {self.current}", S_H3, GOLD,
                  align="right")
        col_w = (PAGE_W - 2 * MARGIN - 16) / 2
        row_h = 38
        top = PAGE_H - 92
        for i, t in enumerate(self.data["towers"]):
            n = t["number"]
            col, row = divmod(i, 15)
            x = MARGIN + col * (col_w + 16)
            y = top - row * row_h
            cur = n == self.current
            c.setFillColor(GRASS_PALE if cur else PARCHMENT)
            c.roundRect(x, y - row_h + 6, col_w, row_h - 5, 3, stroke=0,
                        fill=1)
            self.text(x + 8, y - 14, f"TOWER {n}", 11,
                      GRASS_DARK if cur else INK)
            if cur:
                self.text(x + col_w - 8, y - 14, "THIS WEEK", S_SMALL, GOLD,
                          align="right")
            final = next((f for f in reversed(t["floors"])
                          if f.get("bosses")), None)
            info = f"{len(t['floors'])} floors"
            if final:
                info += " - " + " + ".join(
                    boss_label(b) for b in final["bosses"])
            mon, live_now = next_live(n, self.today)
            if not live_now:
                info += f" - live {fmt_short(mon)}"
            self.text(x + 8, y - 26, info, S_SMALL, FAINT, max_w=col_w - 16)
            c.linkAbsolute("", f"tower-{n}",
                           (x, y - row_h + 6, x + col_w, y + 1))
        self.footer()

    def schedule(self):
        """Date -> tower for the next full cycle, so a stale build still
        gets you to the right guide (a PDF cannot recompute itself when
        opened)."""
        self.new_page()
        c = self.c
        c.bookmarkPage("schedule")
        c.addOutlineEntry("Schedule", "schedule", 0)
        self.text(MARGIN, PAGE_H - 58, "SCHEDULE", 22, GRASS_DARK)
        self.text(PAGE_W - MARGIN, PAGE_H - 58,
                  "WEEKS ROLL OVER SUNDAY NIGHT", S_SMALL, FAINT,
                  align="right")
        top = PAGE_H - 90
        row_h = (top - 40) / CYCLE_WEEKS
        weeks_now = (self.today - ANCHOR).days // 7
        for w in range(CYCLE_WEEKS):
            monday = ANCHOR + datetime.timedelta(weeks=weeks_now + w)
            sunday = monday + datetime.timedelta(days=6)
            n = (weeks_now + w) % CYCLE_WEEKS or CYCLE_WEEKS
            y = top - (w + 1) * row_h
            if w == 0:
                c.setFillColor(GRASS_PALE)
                c.rect(MARGIN, y, PAGE_W - 2 * MARGIN, row_h, stroke=0,
                       fill=1)
            elif w % 2:
                c.setFillColor(PARCHMENT)
                c.rect(MARGIN, y, PAGE_W - 2 * MARGIN, row_h, stroke=0,
                       fill=1)
            cy = y + row_h / 2 - 3
            self.text(MARGIN + 10, cy,
                      f"{fmt_short(monday)} - {fmt_short(sunday)}, "
                      f"{sunday.year}", S_BODY,
                      GRASS_DARK if w == 0 else INK)
            self.text(PAGE_W / 2 + 30, cy, f"TOWER {n}", S_BODY,
                      GRASS_DARK if w == 0 else INK)
            if w == 0:
                self.text(PAGE_W - MARGIN - 10, cy, "THIS WEEK", S_SMALL,
                          GOLD, align="right")
            c.linkAbsolute("", f"tower-{n}",
                           (MARGIN, y, PAGE_W - MARGIN, y + row_h))
        self.footer()

    def tower_pages(self, tower):
        n = tower["number"]
        floors = tower["floors"]
        monday, live_now = next_live(n, self.today)
        chunks = [floors[i:i + ROWS_PER_PAGE]
                  for i in range(0, len(floors), ROWS_PER_PAGE)]
        for ci, chunk in enumerate(chunks):
            self.new_page()
            if ci == 0:
                self.c.bookmarkPage(f"tower-{n}")
                label = f"Tower {n}" + (" (this week)" if live_now else "")
                self.c.addOutlineEntry(label, f"tower-{n}", 0)
            self.tower_header(n, monday, live_now, ci, len(chunks) + 1)
            self.floor_table(chunk)
            self.footer(tower=n)
        self.notes_page(n, monday, live_now, len(chunks))

    def tower_header(self, n, monday, live_now, ci, total):
        c = self.c
        c.setFillColor(GRASS_DARK if live_now else STONE)
        c.rect(0, PAGE_H - 64, PAGE_W, 64, stroke=0, fill=1)
        self.text(MARGIN, PAGE_H - 44, f"TOWER {n}", S_H1, WHITE)
        sub = (f"THIS WEEK  ({fmt_date(monday)} - "
               f"{fmt_date(monday + datetime.timedelta(days=6))})"
               if live_now else
               f"NEXT LIVE: WEEK OF {fmt_date(monday)}")
        self.text(MARGIN, PAGE_H - 58, sub, S_BODY,
                  GRASS_LIGHT if live_now else STONE_LIGHT)
        self.text(PAGE_W - MARGIN, PAGE_H - 44, f"{ci + 1}/{total}", S_H3,
                  STONE_LIGHT, align="right")

    def floor_table(self, chunk):
        c = self.c
        x0 = MARGIN
        widths = [26, 175, 130, 120]  # floor, item, enchants, boss/merchant
        headers = ["FL", "ITEM TO TAKE", "ENCHANTMENTS", "BOSS / MERCHANT"]
        table_w = sum(widths)
        top = PAGE_H - 80
        row_h = (top - 40) / ROWS_PER_PAGE  # ~37pt: content + writing space
        # header row
        c.setFillColor(INK)
        c.rect(x0, top - 16, table_w, 16, stroke=0, fill=1)
        x = x0
        for w, h in zip(widths, headers):
            self.text(x + 4, top - 12, h, 7.5, WHITE)
            x += w
        y = top - 16
        for f in chunk:
            y -= row_h
            kind = ("merchant" if f["kind"] == "merchant"
                    else "boss" if f.get("bosses") else "plain")
            bg = {"merchant": MERCH_PALE, "boss": BOSS_PALE,
                  "plain": PARCHMENT if f["floor"] % 2 else None}[kind]
            if bg:
                c.setFillColor(bg)
                c.rect(x0, y, table_w, row_h, stroke=0, fill=1)
            c.setStrokeColor(RULE)
            c.setLineWidth(0.5)
            c.line(x0, y, x0 + table_w, y)
            # writing line for in-game pencil notes
            c.setStrokeColor(WRITE_RULE)
            c.line(x0 + widths[0] + 4, y + 7, x0 + table_w - 4, y + 7)
            ccy = y + row_h / 2 + 4  # center of the content zone
            # floor number
            self.text(x0 + widths[0] / 2, ccy - 4, str(f["floor"]), 11, INK,
                      align="center")
            # item
            ix = x0 + widths[0]
            iw = widths[1]
            if f["kind"] == "merchant":
                self.icon("merchant.png", ix + 4, ccy - 9, 18)
                self.text(ix + 27, ccy - 4, "MERCHANT", S_H3, MERCH_BLUE)
            elif f.get("item"):
                has_icon = (self.icon("enchantment-point.png", ix + 5,
                                      ccy - 8, 16)
                            if f["item"] == "Enchantment Point"
                            else self.icon(f["item"], ix + 4, ccy - 9, 18))
                tx = ix + (27 if has_icon else 4)
                tw = iw - (31 if has_icon else 8)
                name = f["item"] + (" (improved)" if f.get("better") else "")
                lines = [(s, S_BODY, INK, 0)
                         for s in self.wrap(name, S_BODY, tw)]
                if f.get("replaces"):
                    lines += [(s, S_SMALL, FAINT, 0) for s in self.wrap(
                        "replaces " + f["replaces"], S_SMALL, tw, 1)]
                self.lines_block(tx, ccy, lines, line_h=10)
            # enchantments (wrap between enchantments, not mid-name)
            ex = ix + widths[1]
            if f.get("enchants"):
                tokens = enchant_text(f["enchants"]).split(", ")
                rows, cur = [], ""
                for tok in tokens:
                    cand = f"{cur}, {tok}" if cur else tok
                    if not cur or self.c.stringWidth(
                            cand + ",", MC, S_BODY) <= widths[2] - 8:
                        cur = cand
                    else:
                        rows.append(cur + ",")
                        cur = tok
                rows.append(cur)
                lines = [(s, S_BODY, INK, 0) for s in rows]
                self.lines_block(ex + 4, ccy, lines, line_h=10)
            # boss / merchant upgrade
            bx = ex + widths[2]
            if f["kind"] == "merchant":
                lines = ([("UPGRADE:", S_SMALL, MERCH_BLUE, 0)]
                         + [(s, S_BODY, MERCH_BLUE, 0) for s in self.wrap(
                             f["upgrade"], S_BODY, widths[3] - 8)])
                self.lines_block(bx + 4, ccy, lines, line_h=9)
            elif f.get("bosses"):
                bosses = f["bosses"]
                lh = 14
                top_y = ccy + (len(bosses) * lh) / 2 - lh / 2
                for i, b in enumerate(bosses):
                    ly = top_y - i * lh
                    has_icon = self.icon(b["name"], bx + 3, ly - 6, 13)
                    self.text(bx + (20 if has_icon else 4), ly - 3,
                              boss_label(b), S_BODY, BOSS_RED,
                              max_w=widths[3] - (24 if has_icon else 8))
        c.setStrokeColor(RULE)
        c.rect(x0, y, table_w, top - y, stroke=1, fill=0)
        x = x0
        for w in widths[:-1]:
            x += w
            c.line(x, y, x, top)

    def notes_page(self, n, monday, live_now, chunks):
        self.new_page()
        self.tower_header(n, monday, live_now, chunks, chunks + 1)
        self.text(MARGIN, PAGE_H - 96, "NOTES", 16, GRASS_DARK)
        self.text(PAGE_W - MARGIN, PAGE_H - 96,
                  f"edit notes/towers/tower-{n:02d}.md to keep notes "
                  "across cycles", S_SMALL, FAINT, align="right")
        y = PAGE_H - 120
        max_w = PAGE_W - 2 * MARGIN
        for line in load_notes(n):
            if not line.strip():
                y -= 8
                continue
            stripped = line.strip()
            bullet = stripped.startswith("- ")
            body = stripped[2:] if bullet else stripped
            for i, s in enumerate(self.wrap(body, S_BODY, max_w - 22,
                                            max_lines=4)):
                if bullet and i == 0:
                    self.text(MARGIN + 10, y, "*", S_BODY, GRASS)
                self.text(MARGIN + (22 if bullet else 0), y, s, S_BODY, INK)
                y -= 13
                if y < 60:
                    break
            if y < 60:
                break
        # ruled lines for handwritten notes
        self.c.setStrokeColor(RULE)
        self.c.setLineWidth(0.5)
        y -= 18
        while y > 40:
            self.c.line(MARGIN, y, PAGE_W - MARGIN, y)
            y -= 36  # ~1/2 inch between rules: comfortable handwriting size
        self.footer(tower=n)

    def build(self):
        self.cover()
        self.index()
        self.schedule()
        for tower in self.data["towers"]:
            self.tower_pages(tower)
        self.c.save()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="build as of this date (YYYY-MM-DD)")
    ap.add_argument("--out", default=str(ROOT / "tower-guides.pdf"))
    args = ap.parse_args()
    today = (datetime.date.fromisoformat(args.date) if args.date
             else datetime.date.today())

    pdfmetrics.registerFont(TTFont(MC, str(FONTS / "Monocraft.ttf")))
    data = json.loads(DATA.read_text())
    Builder(data, today, args.out).build()
    cur = ((today - ANCHOR).days // 7) % CYCLE_WEEKS or CYCLE_WEEKS
    print(f"wrote {args.out} (guide of the week: Tower {cur})")


if __name__ == "__main__":
    main()
