# Minecraft Dungeons Tower Guides

A single hyperlinked PDF of weekly [Minecraft Dungeons](https://minecraft.wiki/w/Dungeons:Wiki)
Tower guides (PS4/PS5), sized for the **Remarkable Paper Pro** (color).
Guide data comes from LordForce's community
[tower spreadsheet](https://docs.google.com/spreadsheets/d/1eafYINb3DPrLTDutkAZzCwBUgmLK4EHnm6MxMcHz7PE);
icons and canonical names come from [minecraft.wiki](https://minecraft.wiki/w/Dungeons:Wiki).

**[Download the latest `tower-guides.pdf`](tower-guides.pdf)** and copy it to
your Remarkable.

## What's in the PDF

- **Cover — "Guide of the Week."** The tower that is live *this* week is
  selected automatically at build time, with a button straight to its guide
  and a linked chip for every tower in the cycle.
- **Tower index.** All 29 towers with floor counts, final bosses, the date
  each tower is next live, and links; the current week is highlighted.
- **One guide per tower.** A floor-by-floor table showing:
  - the **item** to take on each floor (with its wiki icon),
  - the **enchantment(s)** to pick (tiers as roman numerals),
  - the **bosses** you'll face on boss floors, or the item to **upgrade**
    on merchant floors (tinted red and blue respectively),
  - a slim **note** column for quick in-game marks.
- **A notes page per tower** — your typed notes followed by ruled lines for
  handwriting.
- **Navigation links** on every page footer (index / previous / next tower)
  plus PDF bookmarks, so the document is easy to hop around on the
  Remarkable.

Item, enchantment, and boss names are corrected and verified against
minecraft.wiki (the source sheet contains typos like "Encahntment point" and
"Mooshroom monstrocity"). Two notations from the sheet are preserved:
"X *replacing/instead of* Y" means the new item X replaces the older item Y
in your loadout (rendered as "X — replaces Y"), and "A + B" / "12x A" mean
multiple simultaneous bosses.

## Which tower is it this week?

The community sheet computes the live tower as
`weeks since Monday 2023-05-29, mod 29` (0 → 29), rolling over Sunday
night into Monday. `scripts/cycle.py` reproduces this locally, so the PDF
needs no network access to know the current week — it just needs to be
rebuilt (the GitHub Action below does this every Monday).

## Keeping notes across the 29-week cycle

Each tower has a markdown file in [`notes/towers/`](notes/towers)
(`tower-01.md` … `tower-29.md`). Anything you write there is rendered onto
that tower's notes page at the next build — so adjustments you make during
one play-through are waiting in the PDF when the tower comes around again
~29 weeks later. Plain lines and `- ` bullets are supported.

Handwritten marks on the Remarkable stay with the *device copy* of the PDF;
to make a recommendation change permanent, transcribe it into the tower's
notes file (or edit it on your computer right after playing).

## Building it yourself

```bash
pip install -r requirements.txt
python scripts/fetch_data.py     # refresh data/towers.json from the sheet
python scripts/fetch_assets.py   # fetch wiki icons + the Monocraft font
python scripts/build_pdf.py      # write tower-guides.pdf (today's week)
python scripts/build_pdf.py --date 2026-09-07   # or any other week
python -m pytest tests/          # real-data tests incl. a full PDF build
```

`data/towers.json` is a committed snapshot, so `build_pdf.py` works offline;
`fetch_data.py` refuses to write data containing names it can't verify, so
new spreadsheet vocabulary has to be mapped consciously in
`scripts/names.py`.

## Automatic weekly updates

[`weekly-build.yml`](.github/workflows/weekly-build.yml) runs every Monday
(just after the tower rollover): it refreshes the spreadsheet data, fetches
any newly needed icons, runs the tests, rebuilds `tower-guides.pdf`, and
commits the result. Re-download the PDF to your Remarkable each week (or
point a sync tool at the raw file URL).

## Repository layout

| Path | Purpose |
|-|-|
| `tower-guides.pdf` | the built guide — copy this to your Remarkable |
| `data/towers.json` | normalized snapshot of the spreadsheet |
| `notes/towers/*.md` | your persistent per-tower notes |
| `scripts/fetch_data.py` | spreadsheet → `data/towers.json` |
| `scripts/names.py` | wiki-verified name corrections / canonicalization |
| `scripts/fetch_assets.py` | wiki icons + Monocraft font |
| `scripts/build_pdf.py` | PDF generator (Remarkable Paper Pro page size) |
| `scripts/cycle.py` | which tower is live in a given week |
| `docs/specs/` | design document |

## Credits & licenses

- Guide data by **LordForce** (community tower spreadsheet).
- Icons and item/boss names from [minecraft.wiki](https://minecraft.wiki),
  [CC BY-NC-SA 3.0](https://creativecommons.org/licenses/by-nc-sa/3.0/);
  Minecraft content © Mojang Studios.
- [Monocraft](https://github.com/IdreesInc/Monocraft) font by Idrees Hassan,
  SIL Open Font License 1.1.
- This is an unofficial fan project, not affiliated with Mojang or Microsoft.
