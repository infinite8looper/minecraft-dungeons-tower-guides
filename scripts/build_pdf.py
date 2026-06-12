"""Build the hyperlinked tower-guide PDF for the Remarkable Paper Pro.

Usage:
    python scripts/build_pdf.py [--date YYYY-MM-DD] [--out PATH]

Reads data/towers.json, assets/, and notes/towers/*.md. The cover shows the
guide that is live for --date (default: today), reproducing the
spreadsheet's "Guide of the week" behavior. Per-tower notes files are
rendered into each tower's notes page, so they persist across the 29-week
cycle; missing notes files are created from a template.
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
FAINT = HexColor("#8a8578")
PARCHMENT = HexColor("#f1ede2")
GRASS = HexColor("#3e8948")
GRASS_DARK = HexColor("#2c5e33")
GRASS_PALE = HexColor("#dcead8")
GOLD = HexColor("#b8860b")
BOSS_RED = HexColor("#a63a26")
BOSS_PALE = HexColor("#f5ded6")
MERCH_BLUE = HexColor("#2f6584")
MERCH_PALE = HexColor("#dbe8f0")
RULE = HexColor("#c9c2b2")

MC = "Monocraft"
BODY = "Helvetica"
BODY_B = "Helvetica-Bold"
BODY_I = "Helvetica-Oblique"

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


def next_live(n, today):
    """Monday of the next week tower n is (or was last) live."""
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


def boss_text(bosses):
    parts = []
    for b in bosses:
        prefix = f"{b['count']}x " if b["count"] > 1 else ""
        parts.append(prefix + b["name"])
    return " + ".join(parts)


class Builder:
    def __init__(self, data, today, out):
        self.data = data
        self.today = today
        self.current = ((today - ANCHOR).days // 7) % CYCLE_WEEKS or CYCLE_WEEKS
        self.c = Canvas(str(out), pagesize=(PAGE_W, PAGE_H))
        self.c.setTitle("Minecraft Dungeons Tower Guides")
        self.c.setAuthor("Guide data by LordForce; PDF by tower-guide-builder")
        self.page_num = 0

    # -- low-level helpers ---------------------------------------------------

    def fit(self, text, font, size, max_w, min_size=5.5):
        while size > min_size and self.c.stringWidth(text, font, size) > max_w:
            size -= 0.5
        return size

    def text(self, x, y, s, font=BODY, size=9, color=INK, max_w=None,
             align="left"):
        if max_w:
            size = self.fit(s, font, size, max_w)
        self.c.setFont(font, size)
        self.c.setFillColor(color)
        if align == "left":
            self.c.drawString(x, y, s)
        elif align == "right":
            self.c.drawRightString(x, y, s)
        else:
            self.c.drawCentredString(x, y, s)

    def icon(self, name, x, y, size):
        path = icon_path(name)
        if not path:
            return False
        try:
            self.c.drawImage(str(path), x, y, size, size, mask="auto",
                             preserveAspectRatio=True, anchor="c")
            return True
        except Exception:
            return False

    def link_box(self, rect, dest, fill, label, font=MC, size=11,
                 text_color=None):
        x, y, w, h = rect
        self.c.setFillColor(fill)
        self.c.roundRect(x, y, w, h, 3, stroke=0, fill=1)
        self.text(x + w / 2, y + h / 2 - size * 0.35, label, font, size,
                  text_color or HexColor("#ffffff"), max_w=w - 10,
                  align="center")
        self.c.linkAbsolute("", dest, (x, y, x + w, y + h))

    def footer(self, tower=None):
        y = 12
        c = self.c
        c.setStrokeColor(RULE)
        c.setLineWidth(0.6)
        c.line(MARGIN, y + 12, PAGE_W - MARGIN, y + 12)
        self.text(PAGE_W - MARGIN, y, str(self.page_num), MC, 7, FAINT,
                  align="right")
        # nav links: prev tower / index / next tower
        labels = [("INDEX", "index")]
        if tower:
            prev_t = tower - 1 if tower > 1 else CYCLE_WEEKS
            next_t = tower + 1 if tower < CYCLE_WEEKS else 1
            labels = [(f"<< TOWER {prev_t}", f"tower-{prev_t}"),
                      ("INDEX", "index"),
                      (f"TOWER {next_t} >>", f"tower-{next_t}")]
        positions = {1: [0.5], 3: [0.22, 0.5, 0.78]}[len(labels)]
        for (label, dest), frac in zip(labels, positions):
            w = c.stringWidth(label, MC, 8) + 8
            x = PAGE_W * frac - w / 2
            self.text(PAGE_W * frac, y, label, MC, 8, GRASS_DARK,
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
        self.text(PAGE_W / 2, PAGE_H - 78, "MINECRAFT DUNGEONS", MC, 30,
                  HexColor("#ffffff"), align="center")
        self.text(PAGE_W / 2, PAGE_H - 112, "TOWER GUIDES", MC, 20,
                  HexColor("#c8e6b8"), align="center")

        start, end = (None, None)
        monday, _ = next_live(self.current, self.today)
        sunday = monday + datetime.timedelta(days=6)
        y = PAGE_H - 215
        self.text(PAGE_W / 2, y, "GUIDE OF THE WEEK", MC, 13, GOLD,
                  align="center")
        self.text(PAGE_W / 2, y - 56, f"TOWER {self.current}", MC, 44,
                  INK, align="center")
        self.text(PAGE_W / 2, y - 80,
                  f"{fmt_date(monday)} - {fmt_date(sunday)}",
                  MC, 10, FAINT, align="center")
        self.link_box((PAGE_W / 2 - 110, y - 130, 220, 34),
                      f"tower-{self.current}", GRASS,
                      f"OPEN TOWER {self.current} >>", size=13)

        # mini index: chips for all towers
        y0 = y - 195
        self.text(PAGE_W / 2, y0 + 18, "ALL TOWERS", MC, 10, FAINT,
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
                          GOLD if cur else PARCHMENT, f"T{n}", size=10,
                          text_color=HexColor("#ffffff") if cur else INK)

        self.text(PAGE_W / 2, 78,
                  "Cover updates automatically each week (rebuild the PDF).",
                  BODY_I, 8.5, FAINT, align="center")
        self.text(PAGE_W / 2, 64,
                  f"Built {fmt_date(self.today)}  -  guide data by LordForce",
                  BODY, 8.5, FAINT, align="center")
        self.text(PAGE_W / 2, 50,
                  "Icons & names: minecraft.wiki (CC BY-NC-SA 3.0)",
                  BODY, 8.5, FAINT, align="center")
        self.footer()

    def index(self):
        self.new_page()
        c = self.c
        c.bookmarkPage("index")
        c.addOutlineEntry("Tower Index", "index", 0)
        self.text(MARGIN, PAGE_H - 58, "TOWER INDEX", MC, 22, GRASS_DARK)
        self.text(PAGE_W - MARGIN, PAGE_H - 58,
                  f"THIS WEEK: TOWER {self.current}", MC, 10, GOLD,
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
            self.text(x + 8, y - 14, f"TOWER {n}", MC, 11,
                      GRASS_DARK if cur else INK)
            if cur:
                self.text(x + col_w - 8, y - 14, "THIS WEEK", MC, 7, GOLD,
                          align="right")
            final = next((f for f in reversed(t["floors"])
                          if f.get("bosses")), None)
            info = f"{len(t['floors'])} floors"
            if final:
                info += "  -  final: " + boss_text(final["bosses"])
            mon, live_now = next_live(n, self.today)
            if not live_now:
                info += f"  -  live {mon.strftime('%b %-d')}"
            self.text(x + 8, y - 26, info, BODY, 8, FAINT,
                      max_w=col_w - 16)
            c.linkAbsolute("", f"tower-{n}",
                           (x, y - row_h + 6, x + col_w, y + 1))
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
        c.setFillColor(GRASS_DARK if live_now else HexColor("#4a4438"))
        c.rect(0, PAGE_H - 64, PAGE_W, 64, stroke=0, fill=1)
        self.text(MARGIN, PAGE_H - 44, f"TOWER {n}", MC, 24,
                  HexColor("#ffffff"))
        sub = (f"THIS WEEK  ({fmt_date(monday)} - "
               f"{fmt_date(monday + datetime.timedelta(days=6))})"
               if live_now else
               f"NEXT LIVE: WEEK OF {fmt_date(monday)}")
        self.text(MARGIN, PAGE_H - 58, sub, MC, 8,
                  HexColor("#c8e6b8") if live_now else HexColor("#cfc8b8"))
        self.text(PAGE_W - MARGIN, PAGE_H - 44, f"{ci + 1}/{total}", MC, 10,
                  HexColor("#cfc8b8"), align="right")

    def floor_table(self, chunk):
        c = self.c
        x0 = MARGIN
        widths = [26, 158, 122, 112, 33]  # floor, item, enchants, boss, notes
        headers = ["FL", "ITEM TO TAKE", "ENCHANTMENTS", "BOSS / MERCHANT",
                   "NOTE"]
        table_w = sum(widths)
        top = PAGE_H - 80
        row_h = (top - 40) / ROWS_PER_PAGE
        # header row
        c.setFillColor(INK)
        c.rect(x0, top - 16, table_w, 16, stroke=0, fill=1)
        x = x0
        for w, h in zip(widths, headers):
            self.text(x + 4, top - 12, h, MC, 7.5, HexColor("#ffffff"))
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
            cy = y + row_h / 2
            # floor number
            self.text(x0 + widths[0] / 2, cy - 4, str(f["floor"]), MC, 11,
                      INK, align="center")
            # item
            ix = x0 + widths[0]
            if f["kind"] == "merchant":
                self.text(ix + 24, cy - 4, "MERCHANT", MC, 10, MERCH_BLUE)
                self.text(ix + 4, cy - 4, "$", MC, 12, MERCH_BLUE)
            elif f.get("item"):
                has_icon = self.icon(f["item"], ix + 3, cy - 10, 20)
                tx = ix + (27 if has_icon else 4)
                name = f["item"] + (" (improved)" if f.get("better") else "")
                if f.get("replaces"):
                    self.text(tx, cy + 1, name, BODY_B, 9, INK,
                              max_w=widths[1] - 30)
                    self.text(tx, cy - 9, "replaces " + f["replaces"],
                              BODY_I, 7.5, FAINT, max_w=widths[1] - 30)
                else:
                    self.text(tx, cy - 3, name, BODY_B, 9, INK,
                              max_w=widths[1] - 30)
            # enchantments
            ex = ix + widths[1]
            if f.get("enchants"):
                txt = enchant_text(f["enchants"])
                size = self.fit(txt, BODY, 8.5, widths[2] - 8, min_size=7)
                if self.c.stringWidth(txt, BODY, size) > widths[2] - 8:
                    # wrap to two lines on the comma nearest the middle
                    parts = txt.split(", ")
                    best, l1 = None, ""
                    for k in range(1, len(parts)):
                        a = ", ".join(parts[:k]) + ","
                        b = ", ".join(parts[k:])
                        if (self.c.stringWidth(a, BODY, 8) < widths[2] - 8
                                and self.c.stringWidth(b, BODY, 8)
                                < widths[2] - 8):
                            best = (a, b)
                    if best:
                        self.text(ex + 4, cy + 1, best[0], BODY, 8, INK)
                        self.text(ex + 4, cy - 9, best[1], BODY, 8, INK)
                    else:
                        self.text(ex + 4, cy - 3, txt, BODY, 8.5, INK,
                                  max_w=widths[2] - 8)
                else:
                    self.text(ex + 4, cy - 3, txt, BODY, size, INK)
            # boss / merchant upgrade
            bx = ex + widths[2]
            if f["kind"] == "merchant":
                self.text(bx + 4, cy + 1, "UPGRADE:", MC, 7, MERCH_BLUE)
                self.text(bx + 4, cy - 9, f["upgrade"], BODY_B, 8.5,
                          MERCH_BLUE, max_w=widths[3] - 8)
            elif f.get("bosses"):
                bosses = f["bosses"]
                bicon = self.icon(bosses[0]["name"], bx + 2, cy - 9, 18)
                tx = bx + (23 if bicon else 4)
                max_w = widths[3] - (27 if bicon else 8)
                one_line = boss_text(bosses)
                if (len(bosses) > 1
                        and self.c.stringWidth(one_line, BODY_B, 8) > max_w):
                    self.text(tx, cy + 1, boss_text(bosses[:1]) + " +",
                              BODY_B, 8, BOSS_RED, max_w=max_w)
                    self.text(tx, cy - 9, boss_text(bosses[1:]),
                              BODY_B, 8, BOSS_RED, max_w=max_w)
                else:
                    self.text(tx, cy - 3, one_line, BODY_B, 8, BOSS_RED,
                              max_w=max_w)
        c.setStrokeColor(RULE)
        c.rect(x0, y, table_w, top - y, stroke=1, fill=0)
        # column separators
        x = x0
        for w in widths[:-1]:
            x += w
            c.line(x, y, x, top)

    def notes_page(self, n, monday, live_now, chunks):
        self.new_page()
        self.tower_header(n, monday, live_now, chunks, chunks + 1)
        self.text(MARGIN, PAGE_H - 96, "NOTES", MC, 16, GRASS_DARK)
        self.text(PAGE_W - MARGIN, PAGE_H - 96,
                  f"edit notes/towers/tower-{n:02d}.md to keep notes "
                  "across cycles", BODY_I, 7.5, FAINT, align="right")
        y = PAGE_H - 120
        for line in load_notes(n):
            if not line.strip():
                y -= 8
                continue
            text = line.strip()
            if text.startswith("- "):
                self.text(MARGIN + 10, y, "*", MC, 9, GRASS)
                self.text(MARGIN + 22, y, text[2:], BODY, 10, INK,
                          max_w=PAGE_W - 2 * MARGIN - 22)
            else:
                self.text(MARGIN, y, text, BODY, 10, INK,
                          max_w=PAGE_W - 2 * MARGIN)
            y -= 16
            if y < 60:
                break
        # ruled lines for handwritten notes
        self.c.setStrokeColor(RULE)
        self.c.setLineWidth(0.5)
        y -= 14
        while y > 40:
            self.c.line(MARGIN, y, PAGE_W - MARGIN, y)
            y -= 26
        self.footer(tower=n)

    def build(self):
        self.cover()
        self.index()
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
