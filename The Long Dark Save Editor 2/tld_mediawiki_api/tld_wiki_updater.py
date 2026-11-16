#!/usr/bin/env python3
"""
tld_wiki_updater.py — Fetch current item lists from the TLD Fandom wiki
and report any GEAR_ prefab names in your save that aren't in the taxonomy.

Run this from your local machine (requires internet access to fandom.com).
It will NOT modify tld_reader.py — it outputs a report of missing items
so you can decide how to classify them.

Usage:
    python tld_wiki_updater.py                      # report only
    python tld_wiki_updater.py --save sandbox1      # cross-ref against a save
    python tld_wiki_updater.py --patch              # write missing.json patch
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests")

WIKI_API = "https://thelongdark.fandom.com/api.php"
HEADERS  = {"User-Agent": "TLD-taxonomy-updater/1.0 (local tool)"}

# Wiki categories to enumerate
WIKI_CATEGORIES = [
    "Clothing", "Tools", "Materials", "Food_And_Drink",
    "First_Aid", "Other", "Research_Books", "Collectibles",
]

# Known mapping from wiki display name → GEAR_ prefab name
# Extend this as new items are discovered
WIKI_NAME_TO_PREFAB: dict[str, str] = {
    # Food - Meat
    "Bear Meat (Cooked)":          "GEAR_CookedMeatBear",
    "Bear Meat (Raw)":             "GEAR_RawMeatBear",
    "Cougar Meat (Cooked)":        "GEAR_CookedMeatCougar",
    "Cougar Meat (Raw)":           "GEAR_RawMeatCougar",
    "Moose Meat (Cooked)":         "GEAR_CookedMeatMoose",
    "Moose Meat (Raw)":            "GEAR_RawMeatMoose",
    "Rabbit Meat (Cooked)":        "GEAR_CookedMeatRabbit",
    "Rabbit Meat (Raw)":           "GEAR_RawMeatRabbit",
    "Venison (Cooked)":            "GEAR_CookedMeatDeer",
    "Venison (Raw)":               "GEAR_RawMeatDeer",
    "Wolf Meat (Cooked)":          "GEAR_CookedMeatWolf",
    "Wolf Meat (Raw)":             "GEAR_RawMeatWolf",
    # Food - Fish
    "Coho Salmon (Cooked)":        "GEAR_CookedCohoSalmon",
    "Coho Salmon (Raw)":           "GEAR_RawCohoSalmon",
    "Lake Whitefish (Cooked)":     "GEAR_CookedLakeWhiteFish",
    "Lake Whitefish (Raw)":        "GEAR_RawLakeWhiteFish",
    "Rainbow Trout (Cooked)":      "GEAR_CookedRainbowTrout",
    "Rainbow Trout (Raw)":         "GEAR_RawRainbowTrout",
    "Smallmouth Bass (Cooked)":    "GEAR_CookedSmallmouthBass",
    "Smallmouth Bass (Raw)":       "GEAR_RawSmallmouthBass",
    "Burbot (Cooked)":             "GEAR_CookedBurbot",
    "Burbot (Raw)":                "GEAR_RawBurbot",
    "Goldeye (Cooked)":            "GEAR_CookedGoldeye",
    "Goldeye (Raw)":               "GEAR_RawGoldeye",
    "Red Irish Lord (Cooked)":     "GEAR_CookedRedIrishLord",
    "Red Irish Lord (Raw)":        "GEAR_RawRedIrishLord",
    "Rockfish (Cooked)":           "GEAR_CookedRockfish",
    "Rockfish (Raw)":              "GEAR_RawRockfish",
    # Food - Packaged
    "Beef Jerky":                  "GEAR_BeefJerky",
    "Candy Bar":                   "GEAR_CandyBar",
    "Condensed Milk":              "GEAR_CondensedMilk",
    "Dog Food":                    "GEAR_DogFood",
    "Energy Bar":                  "GEAR_EnergyBar",
    "Granola Bar":                 "GEAR_GranolaBar",
    "Maple Syrup":                 "GEAR_MapleSyrup",
    "Military-Grade MRE":          "GEAR_MRE",
    "Peanut Butter":               "GEAR_PeanutButter",
    "Pinnacle Peaches":            "GEAR_PinnacleCanPeaches",
    "Pork and Beans":              "GEAR_CannedBeans",
    "Salty Crackers":              "GEAR_Crackers",
    "Tin of Sardines":             "GEAR_CannedSardines",
    "Tomato Soup":                 "GEAR_TomatoSoupCan",
    # Drinks
    "Coffee":                      "GEAR_CoffeeTin",
    "Herbal Tea":                  "GEAR_GreenTeaPackage",
    "Orange Soda":                 "GEAR_SodaOrange",
    "Potable Water":               "GEAR_WaterSupplyPotable",
    "Stacy's Grape Soda":          "GEAR_SodaGrape",
    "Summit Soda":                 "GEAR_Soda",
    # First Aid
    "Antibiotics":                 "GEAR_BottleAntibiotics",
    "Antiseptic":                  "GEAR_Antiseptic",
    "Bandage":                     "GEAR_HeavyBandage",
    "Emergency stim":              "GEAR_EmergencyStim",
    "Painkillers":                 "GEAR_BottlePainKillers",
    "Vitamins":                    "GEAR_Vitamins",
    # Materials
    "Birch bark":                  "GEAR_BarkTinder",
    "Birch sapling":               "GEAR_BirchSapling",
    "Black bear hide":             "GEAR_BearHide",
    "Cloth":                       "GEAR_Cloth",
    "Coal":                        "GEAR_Coal",
    "Crow Feather":                "GEAR_CrowFeather",
    "Cured Birch Sapling":         "GEAR_BirchSaplingDried",
    "Cured Gut":                   "GEAR_GutDried",
    "Cured Leather":               "GEAR_LeatherDried",
    "Cured Maple Sapling":         "GEAR_MapleSaplingDried",
    "Cured Moose Hide":            "GEAR_MooseHide",
    "Cured Rabbit Pelt":           "GEAR_RabbitPeltDried",
    "Cured Wolf Pelt":             "GEAR_WolfPeltDried",
    "Fresh Gut":                   "GEAR_Gut",
    "Fresh Leather":               "GEAR_LeatherHide",
    "Fresh Moose Hide":            "GEAR_MooseHide",
    "Fresh Rabbit Pelt":           "GEAR_RabbitPeltDried",
    "Fresh Wolf Pelt":             "GEAR_WolfPelt",
    "Reclaimed Wood":              "GEAR_ReclaimedWoodB",
    "Scrap Metal":                 "GEAR_ScrapMetal",
    "Stick":                       "GEAR_Stick",
    "Stone":                       "GEAR_Stone",
    # Tools
    "Can Opener":                  "GEAR_CanOpener",
    "Firestriker":                 "GEAR_Firestriker",
    "Fishing tackle":              "GEAR_FishingLureA",
    "Hacksaw":                     "GEAR_Hacksaw",
    "Hatchet":                     "GEAR_Hatchet",
    "Heavy Hammer":                "GEAR_Hammer",
    "Hook":                        "GEAR_Hook",
    "Hunting Knife":               "GEAR_Knife",
    "Hunting Rifle":               "GEAR_Rifle",
    "Improvised Hatchet":          "GEAR_Hatchet",
    "Improvised Knife":            "GEAR_KnifeScrapMetal",
    "Kerosene":                    "GEAR_LampFuel",
    "Lantern":                     "GEAR_KeroseneLampB",
    "Lantern Fuel":                "GEAR_LampFuel",
    "Line":                        "GEAR_Line",
    "Magnifying Lens":             "GEAR_MagnifyingLens",
    "Mountaineering Rope":         "GEAR_Rope",
    "Newsprint":                   "GEAR_Newsprint",
    "Newsprint Roll":              "GEAR_NewsprintRoll",
    "Prybar":                      "GEAR_Prybar",
    "Quality tools":               "GEAR_HighQualityTools",
    "Rifle Cleaning Kit":          "GEAR_RifleCleaningKit",
    "Sewing Kit":                  "GEAR_SewingKit",
    "Signal pistol":               "GEAR_FlareGun",
    "Simple Tools":                "GEAR_SimpleTools",
    "Snare":                       "GEAR_Snare",
    "Storm Lantern":               "GEAR_KeroseneLampB",
    "Survival Bow":                "GEAR_Bow",
    "Torch":                       "GEAR_Torch",
    "Travois":                     "GEAR_Travois",
    "Whetstone":                   "GEAR_SharpeningStone",
    # Clothing
    "Backpack":                    "GEAR_TechnicalBackpack",
    "Balaclava":                   "GEAR_Balaclava",
    "Baseball Cap":                "GEAR_BaseballCap",
    "Basic Boots":                 "GEAR_BasicBoots",
    "Basic Gloves":                "GEAR_BasicGloves",
    "Basic Winter Coat":           "GEAR_BasicWinterCoat",
    "Basic Wool Hat":              "GEAR_BasicWoolHat",
    "Basic Wool Scarf":            "GEAR_BasicWoolScarf",
    "Bear Skin Bedroll":           "GEAR_BearSkinBedroll",
    "Bear Skin Coat":              "GEAR_BearSkinCoat",
    "Bedroll":                     "GEAR_BedRoll",
    "Cargo Pants":                 "GEAR_CargoPants",
    "Climbing Socks":              "GEAR_ClimbingSocks",
    "Combat Boots":                "GEAR_CombatBoots",
    "Combat Pants":                "GEAR_CombatPants",
    "Cotton Long Underwear":       "GEAR_LongUnderwear",
    "Cotton Scarf":                "GEAR_CottonScarf",
    "Cotton Socks":                "GEAR_CottonSocks",
    "Cotton Toque":                "GEAR_Toque",
    "Cowichan Sweater":            "GEAR_CowichanSweater",
    "Deerskin Boots":              "GEAR_DeerSkinBoots",
    "Deerskin Pants":              "GEAR_DeerSkinPants",
    "Down Ski Jacket":             "GEAR_DownSkiJacket",
    "Down Vest":                   "GEAR_DownVest",
    "Dress Shirt":                 "GEAR_DressShirt",
    "Driving Gloves":              "GEAR_DrivingGloves",
    "Expedition Parka":            "GEAR_ExpeditionParka",
    "Fisherman's Sweater":         "GEAR_FishermanSweater",
    "Fleece Cowl":                 "GEAR_FleeceCowl",
    "Fleece Mittens":              "GEAR_FleeceMittens",
    "Fleece Sweater":              "GEAR_FleeceSweater",
    "Gauntlets":                   "GEAR_Gauntlets",
    "Heavy Wool Sweater":          "GEAR_HeavyWoolSweater",
    "Hoodie":                      "GEAR_CottonHoodie",
    "Insulated Boots":             "GEAR_InsulatedBoots",
    "Insulated Vest":              "GEAR_InsulatedVest",
    "Jeans":                       "GEAR_Jeans",
    "Leather Shoes":               "GEAR_LeatherShoes",
    "Light Shell":                 "GEAR_LightShell",
    "Long Wool Scarf":             "GEAR_WoolWrap",
    "Mackinaw Jacket":             "GEAR_MackinawJacket",
    "Mariner's Pea Coat":          "GEAR_MarinerPeaCoat",
    "Military Coat":               "GEAR_MilitaryCoat",
    "Mittens":                     "GEAR_Mittens",
    "Moose-hide Cloak":            "GEAR_MooseHideCloak",
    "Moose-hide Satchel":          "GEAR_MooseHideSatchel",
    "Mukluks":                     "GEAR_Mukluks",
    "Old Fashioned Parka":         "GEAR_OldFashionedParka",
    "Plaid Shirt":                 "GEAR_PlaidShirt",
    "Premium Winter Coat":         "GEAR_PremiumWinterCoat",
    "Quality Winter Coat":         "GEAR_QualityWinterCoat",
    "Rabbitskin Mitts":            "GEAR_RabbitSkinMittens",
    "Running Shoes":               "GEAR_BasicShoes",
    "Simple Parka":                "GEAR_LightParka",
    "Ski Boots":                   "GEAR_SkiBoots",
    "Ski Gloves":                  "GEAR_SkiGloves",
    "Ski Jacket":                  "GEAR_SkiJacket",
    "Snow Pants":                  "GEAR_SnowPants",
    "Sport Vest":                  "GEAR_SportVest",
    "Sports Socks":                "GEAR_CottonSocks",
    "Sweatshirt":                  "GEAR_Sweatshirt",
    "T-Shirt":                     "GEAR_TeeShirt",
    "Tin of Coffee":               "GEAR_CoffeeTin",
    "Trail Boots":                 "GEAR_WorkBoots",
    "Turtleneck Sweater":          "GEAR_TurtleneckSweater",
    "Urban Parka":                 "GEAR_UrbanParka",
    "Windbreaker":                 "GEAR_Windbreaker",
    "Wolf Pelt":                   "GEAR_WolfPelt",
    "Wool Ear Wrap":               "GEAR_WoolEarWrap",
    "Wool Long Scarf":             "GEAR_WoolWrap",
    "Wool Mittens":                "GEAR_Mittens",
    "Wool Scarf":                  "GEAR_BasicWoolScarf",
    "Wool Shirt":                  "GEAR_WoolShirt",
    "Wool Socks":                  "GEAR_WoolSocks",
    "Wool Sweater":                "GEAR_WoolSweater",
    "Work Boots":                  "GEAR_WorkBoots",
    "Work Gloves":                 "GEAR_WorkGloves",
    "Work Pants":                  "GEAR_WorkPants",
}

# Items to skip (not actual gear items, or redirect pages)
SKIP_TITLES = {
    "Items", "Light Sources", "Car", "Cargo Container", "Metal Container",
    "Plastic Container", "Safe", "Forge", "Rural Store", "Locket",
    "Polaroid Photo", "Climber's Journal Pages", "Cat Tail Head",
    "Green Birch Sapling", "Cardboard Matches",  # old name for Pack Matches
}


def fetch_category_members(category: str, session: "requests.Session") -> list[str]:
    pages: list[str] = []
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": 500,
        "cmtype": "page",
        "format": "json",
    }
    while True:
        r = session.get(WIKI_API, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        members = data.get("query", {}).get("categorymembers", [])
        pages.extend(m["title"] for m in members)
        cont = data.get("continue", {}).get("cmcontinue")
        if not cont:
            break
        params["cmcontinue"] = cont
        time.sleep(0.25)
    return pages


def load_taxonomy_prefabs(script_dir: Path) -> set[str]:
    """Load known GEAR_ prefabs from tld_taxonomy.py if present."""
    taxonomy_path = script_dir / "tld_taxonomy.py"
    if not taxonomy_path.exists():
        return set()
    ns: dict = {}
    exec(taxonomy_path.read_text(), ns)
    return set(ns.get("TAXONOMY_LOOKUP", {}).keys())


def load_save_prefabs(save_path: Path) -> set[str]:
    """Extract all GEAR_ prefab names from a save file."""
    import base64

    def _lzf(data: bytes) -> bytes:
        out = bytearray()
        i, n = 0, len(data)
        while i < n:
            ctrl = data[i]; i += 1
            if ctrl < 32:
                ln = ctrl + 1; out += data[i:i+ln]; i += ln
            else:
                ln = (ctrl >> 5) + 2
                if ln == 9: ln += data[i]; i += 1
                ref = ((ctrl & 0x1f) << 8) + data[i] + 1; i += 1
                pos = len(out) - ref
                for _ in range(ln): out.append(out[pos]); pos += 1
        return bytes(out)

    def _d(b: bytes) -> bytes:
        for s in (0, 1, 2):
            try: return _lzf(b[s:])
            except: pass
        raise ValueError("LZF failed")

    import json
    raw = _d(save_path.read_bytes())
    outer = json.loads(raw)
    prefabs: set[str] = set()
    for val in outer.get("m_Dict", {}).values():
        if isinstance(val, list):
            scene = json.loads(_d(bytes(val)))
        elif isinstance(val, str):
            try: scene = json.loads(_d(base64.b64decode(val + "==")))
            except: continue
        else:
            continue
        if not isinstance(scene, dict):
            continue
        for key in ("m_GearManagerSerialized", "m_Inventory_Serialized"):
            block = scene.get(key, {})
            if isinstance(block, str):
                import json as _j
                block = _j.loads(block)
            items_key = "m_SerializedItems"
            for item in (block or {}).get(items_key, []):
                if isinstance(item, str):
                    item = json.loads(item)
                p = item.get("m_PrefabName", "")
                if p.startswith("GEAR_"):
                    prefabs.add(p)
    return prefabs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch TLD wiki item list and report taxonomy gaps."
    )
    parser.add_argument("--save", type=Path, help="Path to a save file to cross-reference")
    parser.add_argument("--patch", action="store_true",
                        help="Write missing items to missing_prefabs.json")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    known_prefabs = load_taxonomy_prefabs(script_dir)
    print(f"Loaded {len(known_prefabs)} prefabs from taxonomy.")

    save_prefabs: set[str] = set()
    if args.save:
        if not args.save.exists():
            sys.exit(f"Save file not found: {args.save}")
        save_prefabs = load_save_prefabs(args.save)
        print(f"Loaded {len(save_prefabs)} prefabs from save file.")
        unknown_in_save = save_prefabs - known_prefabs
        if unknown_in_save:
            print(f"\n⚠  {len(unknown_in_save)} prefabs in save NOT in taxonomy:")
            for p in sorted(unknown_in_save):
                print(f"   {p}")
        else:
            print("✓  All save prefabs are in the taxonomy.")

    print(f"\nFetching wiki categories from {WIKI_API} ...")
    session = requests.Session()
    all_wiki_items: dict[str, list[str]] = {}
    for cat in WIKI_CATEGORIES:
        try:
            items = fetch_category_members(cat, session)
            all_wiki_items[cat] = [
                t for t in items
                if t not in SKIP_TITLES and not t.startswith("File:")
            ]
            print(f"  {cat}: {len(all_wiki_items[cat])} items")
        except Exception as e:
            print(f"  {cat}: ERROR — {e}")

    # Resolve wiki names → GEAR_ prefabs
    new_prefabs: dict[str, str] = {}  # prefab -> category
    unmappable: list[str] = []
    for cat, items in all_wiki_items.items():
        for title in items:
            prefab = WIKI_NAME_TO_PREFAB.get(title)
            if prefab and prefab not in known_prefabs:
                new_prefabs[prefab] = cat
            elif not prefab and title not in SKIP_TITLES:
                unmappable.append(f"{title}  (wiki cat: {cat})")

    print(f"\n=== RESULTS ===")
    if new_prefabs:
        print(f"\n🆕 {len(new_prefabs)} new prefabs found on wiki, not in taxonomy:")
        for p, cat in sorted(new_prefabs.items()):
            print(f"   {p:<40} <- {cat}")
    else:
        print("\n✓  No new prefabs detected.")

    if unmappable:
        print(f"\n❓ {len(unmappable)} wiki items with no known GEAR_ mapping:")
        for item in sorted(set(unmappable)):
            print(f"   {item}")

    if args.patch and new_prefabs:
        patch_path = script_dir / "missing_prefabs.json"
        with patch_path.open("w") as f:
            json.dump({
                "new_prefabs": {p: {"wiki_category": c} for p, c in new_prefabs.items()},
                "unmapped_wiki_items": sorted(set(unmappable)),
            }, f, indent=2)
        print(f"\nPatch written to {patch_path}")
        print("Add these prefabs to tld_taxonomy.py TAXONOMY dict to classify them.")


if __name__ == "__main__":
    main()
