"""Real-data tests: committed snapshot, real PDF builds, real file IO."""

import datetime
import json
import subprocess
import sys
from pathlib import Path

import pypdf
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_pdf
import names
from cycle import CYCLE_WEEKS, current_tower, week_range


@pytest.fixture(scope="session")
def data():
    return json.loads((ROOT / "data" / "towers.json").read_text())


# -- cycle math (golden values cross-checked against the live sheet) ---------

def test_current_tower_matches_live_sheet():
    # the live "Guide of the week" tab showed Tower 13 on 2026-06-11/12
    assert current_tower(datetime.date(2026, 6, 11)) == 13
    assert current_tower(datetime.date(2026, 6, 12)) == 13


def test_cycle_rolls_over_monday():
    assert current_tower(datetime.date(2026, 6, 14)) == 13  # sunday
    assert current_tower(datetime.date(2026, 6, 15)) == 14  # monday


def test_cycle_wraps_after_29():
    d = datetime.date(2026, 6, 15)
    seen = {current_tower(d + datetime.timedelta(weeks=w))
            for w in range(CYCLE_WEEKS)}
    assert seen == set(range(1, CYCLE_WEEKS + 1))


def test_week_range_covers_seven_days():
    start, end = week_range(datetime.date(2026, 6, 11))
    assert start == datetime.date(2026, 6, 8)
    assert end == datetime.date(2026, 6, 14)


# -- name normalization -------------------------------------------------------

def test_typos_are_corrected():
    assert names.canonical_item("Encahntment point") == "Enchantment Point"
    assert names.canonical_item("Corrupted becon") == "Corrupted Beacon"
    assert names.canonical_item("Bussy nest") == "Buzzy Nest"
    assert names.canonical_boss("Mooshroom monstrocity") == \
        "Mooshroom Monstrosity"
    assert names.canonical_enchant("coolsown 3") == ("Cool Down", 3)


def test_replacing_means_new_item_replaces_old():
    item, replaces, better = names.parse_item_cell(
        "Blast fungus replacing satchel")
    assert item == "Blast Fungus"
    assert replaces == "Satchel of Elements"
    item, replaces, _ = names.parse_item_cell(
        "Harpoon Quiver instead of mushroom")
    assert (item, replaces) == ("Harpoon Quiver", "Death Cap Mushroom")


def test_better_prefix():
    item, replaces, better = names.parse_item_cell("Better blast fungus")
    assert (item, replaces, better) == ("Blast Fungus", None, True)


def test_boss_counts_and_pairs():
    assert names.parse_boss_cell("12x Skeleton horsemen") == \
        [("Skeleton Horseman", 12)]
    assert names.parse_boss_cell("Ghast +evoker") == \
        [("Ghast", 1), ("Evoker", 1)]
    assert names.parse_boss_cell("2x drowned necromancer") == \
        [("Drowned Necromancer", 2)]


def test_unknown_names_raise():
    with pytest.raises(names.UnknownName):
        names.canonical_item("Diamond Sword of Wishful Thinking")


# -- data snapshot -------------------------------------------------------------

def test_snapshot_has_full_cycle(data):
    numbers = [t["number"] for t in data["towers"]]
    assert numbers == list(range(1, CYCLE_WEEKS + 1))


def test_every_tower_has_floors_and_final_boss(data):
    for t in data["towers"]:
        assert 18 <= len(t["floors"]) <= 30
        assert any(f.get("bosses") for f in t["floors"]), t["number"]
        for f in t["floors"]:
            if f["kind"] == "merchant":
                assert f["upgrade"]
            assert f["floor"] >= 1


def test_tower_13_matches_live_guide_of_the_week(data):
    """Spot-check against the live sheet's 'Guide of the week' tab."""
    t13 = data["towers"][12]
    f = t13["floors"]
    assert f[0]["item"] == "Corrupted Seeds"
    assert f[0]["enchants"] == [{"name": "Radiance", "tier": 1}]
    assert [x["floor"] for x in f if x["kind"] == "merchant"] == [8, 18, 28]
    assert f[9]["bosses"] == [{"name": "Enderman", "count": 1},
                              {"name": "Wildfire", "count": 1}]


# -- assets ---------------------------------------------------------------------

def test_font_and_icons_present(data):
    assert (ROOT / "assets" / "fonts" / "Monocraft.ttf").exists()
    missing = []
    for t in data["towers"]:
        for f in t["floors"]:
            for key in ({f.get("item")} | {b["name"]
                        for b in f.get("bosses", [])}):
                if key and key != "Enchantment Point" \
                        and not build_pdf.icon_path(key):
                    missing.append(key)
    assert not missing, sorted(set(missing))


# -- notes persistence -----------------------------------------------------------

def test_notes_roundtrip(tmp_path, monkeypatch):
    # real file IO against the real loader, isolated in tmp_path
    monkeypatch.setattr(build_pdf, "NOTES", tmp_path)
    assert build_pdf.load_notes(7) == []          # template auto-created
    path = tmp_path / "tower-07.md"
    assert path.exists() and "rendered on" in path.read_text()
    path.write_text(path.read_text() + "skip floor 3 pick\n- watch ghast\n")
    assert build_pdf.load_notes(7) == ["skip floor 3 pick", "- watch ghast"]


# -- the PDF itself ---------------------------------------------------------------

@pytest.fixture(scope="session")
def built_pdf(tmp_path_factory, data):
    out = tmp_path_factory.mktemp("pdf") / "guides.pdf"
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_pdf.py"),
         "--date", "2026-06-11", "--out", str(out)],
        check=True, capture_output=True)
    return out


def test_pdf_page_count(built_pdf, data):
    reader = pypdf.PdfReader(str(built_pdf))
    expected = 2 + sum(  # cover + index
        -(-len(t["floors"]) // build_pdf.ROWS_PER_PAGE) + 1  # tables + notes
        for t in data["towers"])
    assert len(reader.pages) == expected


def test_pdf_has_outline_and_links(built_pdf):
    reader = pypdf.PdfReader(str(built_pdf))
    titles = [o.title for o in reader.outline]
    assert "Guide of the Week" in titles
    assert "Tower Index" in titles
    assert "Tower 13 (this week)" in titles
    assert sum(1 for t in titles if t.startswith("Tower ")) == CYCLE_WEEKS + 1
    n_links = sum(len(p.get("/Annots") or []) for p in reader.pages)
    assert n_links > 300


def test_pdf_page_size_matches_remarkable(built_pdf):
    reader = pypdf.PdfReader(str(built_pdf))
    box = reader.pages[0].mediabox
    assert abs(float(box.width) / float(box.height) - 1620 / 2160) < 0.001


def test_pdf_embeds_monocraft(built_pdf):
    raw = built_pdf.read_bytes()
    assert b"Monocraft" in raw
