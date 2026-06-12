"""Canonical Minecraft Dungeons names, verified against minecraft.wiki.

The community spreadsheet contains typos, inconsistent casing, and shorthand
("Bees" for Buzzy Nest, "Seeds" for Corrupted Seeds). Everything rendered in
the PDF goes through these maps; unmapped strings raise so new spreadsheet
vocabulary forces a conscious decision here.
"""

import re

# ---------------------------------------------------------------------------
# Items (weapons, armor, artifacts) — keys are lowercased raw strings.
# Values are wiki-canonical page names (page "Dungeons:<value>").
# ---------------------------------------------------------------------------

ITEMS = {
    # weapons
    "backstabber": "Backstabber",
    "battlestaff": "Battlestaff",
    "boneclub": "Boneclub",
    "broken sawblade": "Broken Sawblade",
    "sawblade": "Broken Sawblade",
    "burst crossbow": "Burst Crossbow",
    "cog crossbow": "Cog Crossbow",
    "double axe": "Double Axe",
    "eternal knife": "Eternal Knife",
    "flail": "Flail",
    "glaive": "Glaive",
    "great hammer": "Great Hammer",
    "harpoon crossbow": "Harpoon Crossbow",
    "katana": "Katana",
    "mace": "Mace",
    "mechanized sawblade": "Mechanized Sawblade",
    "obsidian claymore": "Obsidian Claymore",
    "pickaxe": "Pickaxe",
    "power bow": "Power Bow",
    "powerbow": "Power Bow",
    "pride of the piglins": "Pride of the Piglins",
    "scatter crossbow": "Scatter Crossbow",
    "soul bow": "Soul Bow",
    "soul crossbow": "Soul Crossbow",
    "soul knife": "Soul Knife",
    "soul scythe": "Soul Scythe",
    "spear": "Spear",
    "starless night": "The Starless Night",
    "sword": "Sword",
    "tempest knife": "Tempest Knife",
    "the beginning and the end": "The Beginning and The End",
    "void bow": "Void Bow",
    "void touched blades": "Void Touched Blades",
    "whispering spear": "Whispering Spear",
    # armor
    "beehive armor": "Beehive Armor",
    "beenest armor": "Beenest Armor",
    "champions armor": "Champion's Armor",
    "dark armor": "Dark Armor",
    "frost armor": "Frost Armor",
    "grim armor": "Grim Armor",
    "heroes armor": "Hero's Armor",
    "hunters armor": "Hunter's Armor",
    "mercenary armor": "Mercenary Armor",
    "mercanary armor": "Mercenary Armor",
    "plate armor": "Plate Armor",
    "reinforced mail": "Reinforced Mail",
    "reinforce mail": "Reinforced Mail",
    "scale mail": "Scale Mail",
    "shulker armor": "Shulker Armor",
    "snow armor": "Snow Armor",
    "soul robe": "Soul Robe",
    "spider armor": "Spider Armor",
    "titans shroud": "Titan's Shroud",
    "turtle armor": "Turtle Armor",
    "wither armor": "Wither Armor",
    # artifacts
    "beacon": "Corrupted Beacon",
    "bees": "Buzzy Nest",
    "blast fungus": "Blast Fungus",
    "bussy nest": "Buzzy Nest",
    "buzzy nest": "Buzzy Nest",
    "corrupted beacon": "Corrupted Beacon",
    "corrupted becon": "Corrupted Beacon",
    "corrupted seeds": "Corrupted Seeds",
    "golem": "Golem Kit",
    "gong": "Gong of Weakening",
    "harpoon quiver": "Harpoon Quiver",
    "harvester": "Harvester",
    "lightning rod": "Lightning Rod",
    "lighting rod": "Lightning Rod",
    "love medallion": "Love Medallion",
    "mines": "Scatter Mines",
    "scatter mines": "Scatter Mines",
    "mushroom": "Death Cap Mushroom",
    "powershaker": "Powershaker",
    "satchel": "Satchel of Elements",
    "satchle": "Satchel of Elements",
    "satchel of elements": "Satchel of Elements",
    "satchel of elixirs": "Satchel of Elixirs",
    "seeds": "Corrupted Seeds",
    "soul lantern": "Soul Lantern",
    "tasty bone": "Tasty Bone",
    "thundering quiver": "Thundering Quiver",
    "updraft tome": "Updraft Tome",
    "vexes": "Vexing Chant",
    "vexing chant": "Vexing Chant",
    # tower reward, not a wiki item
    "enchantment point": "Enchantment Point",
    "encahntment point": "Enchantment Point",
}

# ---------------------------------------------------------------------------
# Merchant-floor upgrade targets ("upgrade your <X>"). Gear-slot words stay
# as slots; concrete items resolve through ITEMS.
# ---------------------------------------------------------------------------

UPGRADE_SLOTS = {
    "armor": "Armor",
    "melee": "Melee Weapon",
    "ranged": "Ranged Weapon",
    "bow": "Ranged Weapon",
}

# ---------------------------------------------------------------------------
# Bosses — lowercased raw name → wiki-canonical name.
# ---------------------------------------------------------------------------

BOSSES = {
    "ancient guardian": "Ancient Guardian",
    "cauldron": "Corrupted Cauldron",
    "corrupted cauldron": "Corrupted Cauldron",
    "drowned necromancer": "Drowned Necromancer",
    "elder guardian": "Elder Guardian",
    "enderman": "Enderman",
    "endersent": "Endersent",
    "evoker": "Evoker",
    "ghast": "Ghast",
    "illusioner": "Illusioner",
    "jungle abomination": "Jungle Abomination",
    "jungle abomiation": "Jungle Abomination",
    "mooshroom monstrosity": "Mooshroom Monstrosity",
    "mooshroom monstrocity": "Mooshroom Monstrosity",
    "nameless one": "Nameless One",
    "redstone golem": "Redstone Golem",
    "redstone monstrosity": "Redstone Monstrosity",
    "redstone monstrocity": "Redstone Monstrosity",
    "skeleton horseman": "Skeleton Horseman",
    "skeleton horsemen": "Skeleton Horseman",
    "tempest golem": "Tempest Golem",
    "wildfire": "Wildfire",
    "wretched wraith": "Wretched Wraith",
}

# ---------------------------------------------------------------------------
# Enchantments — lowercased raw token (tier digits stripped) → canonical.
# ---------------------------------------------------------------------------

ENCHANTS = {
    "accelerate": "Accelerate",
    "ambush": "Ambush",
    "anima": "Anima Conduit",
    "anima conduit": "Anima Conduit",
    "artifact synergy": "Artifact Synergy",
    "bag of souls": "Bag of Souls",
    "beast burst": "Beast Burst",
    "bonus shot": "Bonus Shot",
    "busy bee": "Busy Bee",
    "chilling": "Chilling",
    "chilling tier": "Chilling",
    "committed": "Committed",
    "cooldown": "Cool Down",
    "cool down": "Cool Down",
    "coolsown": "Cool Down",
    "cowardice": "Cowardice",
    "crit": "Critical Hit",
    "critical hit": "Critical Hit",
    "crittical hit": "Critical Hit",
    "deflect": "Deflect",
    "echo": "Echo",
    "enigma": "Enigma Resonator",
    "enigma resonator": "Enigma Resonator",
    "exploding": "Exploding",
    "final shout": "Final Shout",
    "fire aspect": "Fire Aspect",
    "fire aspekt": "Fire Aspect",
    "fuse shot": "Fuse Shot",
    "grav": "Gravity",
    "gravity": "Gravity",
    "guarding strike": "Guarding Strike",
    "guerding strike": "Guarding Strike",
    "infinity": "Infinity",
    "leeching": "Leeching",
    "lightning focus": "Lightning Focus",
    "multishot": "Multishot",
    "overcharge": "Overcharge",
    "piercing": "Piercing",
    "poison cloud": "Poison Cloud",
    "pot barreir": "Potion Barrier",
    "pot barrier": "Potion Barrier",
    "potion barrier": "Potion Barrier",
    "radiance": "Radiance",
    "rampaging": "Rampaging",
    "refreshment": "Refreshment",
    "ricochet": "Ricochet",
    "sharp": "Sharpness",
    "sharpness": "Sharpness",
    "shockwave": "Shockwave",
    "smiting": "Smiting",
    "snowball": "Snowball",
    "soul siphon": "Soul Siphon",
    "supercharge": "Supercharge",
    "surprise gift": "Surprise Gift",
    "swirling": "Swirling",
    "thorns": "Thorns",
    "thundering": "Thundering",
    "tumble bee": "Tumblebee",
    "tumblebee": "Tumblebee",
    "void": "Void Strike",
    "void strike": "Void Strike",
    "weakening": "Weakening",
    "weakeing": "Weakening",
}


class UnknownName(ValueError):
    pass


def canonical_item(raw):
    key = " ".join(raw.lower().split())
    if key not in ITEMS:
        raise UnknownName(f"unknown item: {raw!r}")
    return ITEMS[key]


def canonical_boss(raw):
    key = " ".join(raw.lower().split())
    if key not in BOSSES:
        raise UnknownName(f"unknown boss: {raw!r}")
    return BOSSES[key]


def canonical_upgrade(raw):
    key = " ".join(raw.lower().split())
    if key in UPGRADE_SLOTS:
        return UPGRADE_SLOTS[key]
    return canonical_item(raw)


def canonical_enchant(raw):
    """'Snowball 3' -> ('Snowball', 3); 'Deflect' -> ('Deflect', None)."""
    text = " ".join(raw.lower().split())
    m = re.match(r"^(.*?)\s*(\d+)?$", text)
    base, tier = m.group(1).strip(), m.group(2)
    if base not in ENCHANTS:
        raise UnknownName(f"unknown enchantment: {raw!r}")
    return ENCHANTS[base], int(tier) if tier else None


def parse_item_cell(raw):
    """Parse an item cell into (item, replaces, better).

    'X replacing Y' / 'X instead of Y' means the new item X replaces the
    older item Y in your loadout. 'Better X' means take the higher-power X.
    """
    text = " ".join(raw.split())
    better = False
    m = re.match(r"^better\s+(.*)$", text, re.IGNORECASE)
    if m:
        better, text = True, m.group(1)
    m = re.match(r"^(.*?)\s+(?:replacing|instead of|replaces)\s+(.*)$", text,
                 re.IGNORECASE)
    if m:
        return canonical_item(m.group(1)), canonical_item(m.group(2)), better
    return canonical_item(text), None, better


def parse_boss_cell(raw):
    """Parse a boss cell into a list of (boss, count).

    '+' separates simultaneous bosses; a '12x'/'2x' prefix is a count.
    """
    out = []
    for part in re.split(r"\s*\+\s*", " ".join(raw.split())):
        m = re.match(r"^(\d+)\s*x\s*(.*)$", part, re.IGNORECASE)
        count, name = (int(m.group(1)), m.group(2)) if m else (1, part)
        out.append((canonical_boss(name), count))
    return out


def parse_enchant_cell(raw):
    """'Snowball 3, Deflect 1' -> [('Snowball', 3), ('Deflect', 1)]."""
    return [canonical_enchant(p) for p in re.split(r"[,;]", raw) if p.strip()]
