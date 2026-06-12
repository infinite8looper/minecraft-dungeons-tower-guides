# Minecraft Dungeons Tower Guide PDF — Design

**Date:** 2026-06-11 · **Status:** implemented autonomously; review welcome

## Goal

A single hyperlinked PDF, sized for the Remarkable Paper Pro (color e-ink,
1620×2160 px @ 229 ppi), containing weekly Tower guides for Minecraft Dungeons
(PS4/PS5). Source of truth is LordForce's community spreadsheet
(`1eafYINb3DPrLTDutkAZzCwBUgmLK4EHnm6MxMcHz7PE`).

## Requirements (from user)

1. The current week's tower is shown automatically (like the "Guide of the
   week" sheet); the full set of 29 guides follows the "Guides" sheet.
2. Per floor: item to select, enchantment(s) to select, and either bosses
   faced or the item to upgrade (merchant floors).
3. Single hyperlinked PDF readable on Remarkable Paper Pro (color).
4. Minecraft fonts, nice icons (from https://minecraft.wiki/w/Dungeons:Wiki
   where possible), and space for notes; notes persist across the 29-week
   cycle.
5. Typos/formatting in the spreadsheet are corrected; naming verified against
   the Dungeons wiki.
6. README documentation.

## Architecture

```
scripts/fetch_data.py    Google Sheets xlsx export → data/towers.json
scripts/names.py         canonical-name + typo-correction maps (wiki-verified)
scripts/fetch_assets.py  minecraft.wiki API → assets/icons/*.png; fonts
scripts/build_pdf.py     data + icons + fonts + notes → tower-guides.pdf
notes/towers/tower-NN.md persistent per-tower notes, re-rendered every build
.github/workflows/       weekly (Sunday night) rebuild + commit
```

- **Data flow:** spreadsheet → `towers.json` (committed snapshot, so builds
  are reproducible offline) → PDF. Refreshing data is explicit
  (`fetch_data.py`), building is deterministic (`build_pdf.py`).
- **Current-week logic:** the spreadsheet's own formula, reproduced locally:
  `tower = ((build_date − 2023-05-29) // 7 days) % 29`, where 0 → 29.
  Verified against the live sheet (2026-06-11 → Tower 13 ✓). The guide rolls
  over Sunday→Monday, matching the sheet's "updates every sunday" note.
- **PDF layout (reportlab):**
  - Page size 509×679 pt (1620×2160 px at 229 ppi) so pages fill the
    Remarkable screen exactly.
  - Cover = "Guide of the Week": current tower banner + its full floor table,
    auto-selected at build time, plus links to the index and the tower's
    canonical section.
  - Index page: 29 linked tower entries; the current week highlighted.
  - One section per tower: floor table with columns *Floor · Item ·
    Enchantments · Boss / Upgrade*, icons inline, then a Notes page
    (rendered persistent notes + ruled blank space for handwriting).
  - Every page footer: ⌂ Index / ◀ previous tower / next tower ▶ links.
- **Fonts:** Monocraft (SIL OFL — safe to redistribute) for the Minecraft
  look; system Helvetica fallback for dense body text.
- **Icons:** `fetch_assets.py` resolves each canonical item/boss name to its
  `Dungeons:` page on minecraft.wiki via the MediaWiki API and downloads the
  page image. Missing icons degrade gracefully (text-only cell).
- **Name normalization:** `names.py` maps every raw spreadsheet string
  (typos, casing, shorthand like "Bees"/"Seeds") to wiki-canonical names,
  e.g. "Encahntment point" → "Enchantment Point", "Boneclub" → "Bone Club",
  "Mooshroom monstrocity" → "Mooshroom Monstrosity". "X replacing Y" /
  "X instead of Y" phrasing is parsed into item + replacement note.
- **Notes persistence:** typed notes live in `notes/towers/tower-NN.md` and
  are rendered into that tower's Notes page on every rebuild — so when Tower
  N comes around again in the cycle, the notes are already in the PDF.
  (Handwritten Remarkable annotations live on the device per-document; the
  markdown files are the durable cross-cycle store.)

## Alternatives considered

- **HTML→PDF (WeasyPrint):** nicer CSS layout, but heavier system deps and
  weaker control of internal link targets; reportlab is pure-Python and
  gives exact link/bookmark control. → reportlab.
- **Live Google Sheets API:** needs credentials; the public xlsx export
  endpoint works anonymously and is enough for a weekly refresh. → export.
- **One PDF per tower:** simpler pages but breaks the "single hyperlinked
  PDF" requirement and Remarkable navigation. → single document.

## Error handling

- Network fetches: explicit failures (no silent fallbacks); the build uses
  committed data/assets, so a wiki/Sheets outage never blocks PDF builds.
- Unknown raw names: build fails loudly listing unmapped strings, so new
  spreadsheet entries force a conscious mapping update.

## Testing

Real-data tests (no mocks): parse the committed snapshot and assert tower
count/floor structure; week-formula golden dates checked against the live
sheet; build the real PDF and assert pages, internal links, and embedded
fonts; rasterize sample pages to PNG for visual verification.
