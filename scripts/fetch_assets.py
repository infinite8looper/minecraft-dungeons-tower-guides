"""Download item/boss icons from minecraft.wiki and the Monocraft font.

Usage:
    python scripts/fetch_assets.py

Icons land in assets/icons/<slug>.png, the font in assets/fonts/. Existing
files are kept (delete to re-fetch). Failures are reported loudly at the end;
the PDF builder degrades to text for any missing icon.
"""

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import names

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "assets" / "icons"
FONTS = ROOT / "assets" / "fonts"
API = "https://minecraft.wiki/api.php"
UA = {"User-Agent": "tower-guide-builder/1.0 (github.com/infinite8looper)"}

MONOCRAFT_URL = ("https://github.com/IdreesInc/Monocraft/releases/download/"
                 "v4.2.1/Monocraft-ttf.zip")


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def api_get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def page_image_url(title, size=160):
    data = api_get({
        "action": "query", "format": "json", "redirects": 1,
        "prop": "pageimages", "piprop": "thumbnail", "pithumbsize": size,
        "titles": title})
    for page in data["query"]["pages"].values():
        thumb = page.get("thumbnail")
        if thumb:
            return thumb["source"]
    return None


def download(url, dest):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req) as resp:
        dest.write_bytes(resp.read())


def fetch_icons():
    ICONS.mkdir(parents=True, exist_ok=True)
    wanted = sorted(
        (set(names.ITEMS.values()) | set(names.BOSSES.values()))
        - {"Enchantment Point"})
    failures = []
    for name in wanted:
        dest = ICONS / f"{slug(name)}.png"
        if dest.exists():
            continue
        url = page_image_url("Dungeons:" + name)
        if not url:
            failures.append(name)
            print(f"  MISSING image for {name}")
            continue
        download(url, dest)
        print(f"  {name} -> {dest.name}")
        time.sleep(0.3)  # be polite to the wiki
    return failures


def fetch_font():
    import io
    import zipfile
    FONTS.mkdir(parents=True, exist_ok=True)
    dest = FONTS / "Monocraft.ttf"
    if dest.exists():
        return
    print(f"downloading Monocraft -> {dest}")
    req = urllib.request.Request(MONOCRAFT_URL, headers=UA)
    with urllib.request.urlopen(req) as resp:
        zf = zipfile.ZipFile(io.BytesIO(resp.read()))
    ttf = [n for n in zf.namelist()
           if n.endswith(".ttf") and "no-ligatures" not in n]
    dest.write_bytes(zf.read(ttf[0]))


def main():
    fetch_font()
    failures = fetch_icons()
    if failures:
        print(f"\n{len(failures)} icons missing: {failures}")
    else:
        print("\nall icons fetched")


if __name__ == "__main__":
    main()
