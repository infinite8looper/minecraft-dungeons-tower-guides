"""Fetch the community tower spreadsheet and normalize it to data/towers.json.

Usage:
    python scripts/fetch_data.py [--xlsx PATH]

Without --xlsx, downloads the public spreadsheet export. All names are
corrected/canonicalized against minecraft.wiki via names.py; an unknown name
aborts the run so new vocabulary gets mapped deliberately.
"""

import argparse
import datetime
import json
import sys
import tempfile
import urllib.request
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).parent))
import names
from cycle import ANCHOR, CYCLE_WEEKS

SHEET_ID = "1eafYINb3DPrLTDutkAZzCwBUgmLK4EHnm6MxMcHz7PE"
EXPORT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "towers.json"


def download_xlsx(dest):
    req = urllib.request.Request(
        EXPORT_URL, headers={"User-Agent": "tower-guide-builder/1.0"})
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
        f.write(resp.read())


def parse_guides(xlsx_path):
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    towers = {}
    for row in wb["Guides"].iter_rows(values_only=True):
        number, item, ench, upgrade, boss = row[:5]
        if number is None:
            continue
        number = int(number)
        if not (item or ench or upgrade or boss):
            continue  # padding rows after a tower's last floor
        floors = towers.setdefault(number, [])
        floor = {"floor": len(floors) + 1}
        if upgrade is not None:
            floor["kind"] = "merchant"
            floor["upgrade"] = names.canonical_upgrade(str(upgrade))
        else:
            floor["kind"] = "floor"
            if item:
                got, replaces, better = names.parse_item_cell(item)
                floor["item"] = got
                if replaces:
                    floor["replaces"] = replaces
                if better:
                    floor["better"] = True
            if ench:
                floor["enchants"] = [
                    {"name": n, "tier": t}
                    for n, t in names.parse_enchant_cell(ench)]
        if boss:
            floor["bosses"] = [
                {"name": n, "count": c} for n, c in names.parse_boss_cell(boss)]
        floors.append(floor)
    if sorted(towers) != list(range(1, CYCLE_WEEKS + 1)):
        raise SystemExit(f"expected towers 1..{CYCLE_WEEKS}, got {sorted(towers)}")
    return towers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", help="parse a local xlsx instead of downloading")
    args = ap.parse_args()

    if args.xlsx:
        xlsx = args.xlsx
    else:
        xlsx = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False).name
        print(f"downloading {EXPORT_URL}")
        download_xlsx(xlsx)

    towers = parse_guides(xlsx)
    data = {
        "source": f"https://docs.google.com/spreadsheets/d/{SHEET_ID}",
        "credit": "Guide data by LordForce (community tower spreadsheet)",
        "fetched": datetime.date.today().isoformat(),
        "anchor_monday": ANCHOR.isoformat(),
        "cycle_weeks": CYCLE_WEEKS,
        "towers": [
            {"number": n, "floors": towers[n]} for n in sorted(towers)],
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1))
    total = sum(len(t["floors"]) for t in data["towers"])
    print(f"wrote {OUT} ({len(data['towers'])} towers, {total} floors)")


if __name__ == "__main__":
    main()
