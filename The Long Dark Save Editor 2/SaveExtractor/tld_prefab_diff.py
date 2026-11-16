#!/usr/bin/env python3
"""Check tld_taxonomy.py against save files and the game's own item catalogs.

Lists every GEAR_ prefab name that tld_taxonomy.py does not classify. Run it after
a game update or after installing an item mod. Nothing is modified.

Usage:
    python tld_prefab_diff.py SAVE [SAVE ...]
    python tld_prefab_diff.py --catalog CATALOG.json [--catalog ...]
    python tld_prefab_diff.py SAVE --catalog CATALOG.json --out new_prefabs.csv

A save is checked in full: inventory, loose and scripted world items, searched
containers, and the loot waiting in containers that have not been searched.

The catalogs are the game's authoritative item list. In the game folder:
    tld_Data\\StreamingAssets\\aa\\catalog.json    base game
    tld_dlc\\TFTFT\\DLC01.json                     Tales from the Far Territory
    tld_dlc\\IronRoad\\DLC02.json                  Iron Road

Exit codes:
    0  every prefab is classified
    1  at least one prefab is missing from the taxonomy
    2  an input could not be read
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

from tld_save_reader import read_save
from tld_taxonomy import TAXONOMY_LOOKUP

# A gear prefab inside a Unity addressables catalog, e.g. ".../GEAR_Hatchet.prefab".
CATALOG_GEAR_PREFAB = re.compile(r"/(GEAR_[^/]+?)\.prefab$", re.IGNORECASE)


def prefabs_in_save(path: Path) -> tuple[Counter[str], dict, list[str]]:
    """Return (stacks per prefab, save header, scene keys that failed to decode)."""
    contents = read_save(path, include_unsearched=True)
    stacks = Counter(record.prefab for record in contents.records)
    return stacks, contents.header, contents.failed_scenes


def prefabs_in_catalog(path: Path) -> set[str]:
    """Return the gear prefab names listed in a Unity addressables catalog."""
    catalog = json.loads(path.read_text(encoding="utf-8"))
    internal_ids = catalog.get("m_InternalIds") if isinstance(catalog, dict) else None
    if not isinstance(internal_ids, list):
        raise ValueError("no m_InternalIds list, so this is not an addressables catalog")
    names = set()
    for internal_id in internal_ids:
        match = CATALOG_GEAR_PREFAB.search(internal_id)
        if match:
            names.add(match.group(1).strip())
    return names


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List GEAR_ prefabs that tld_taxonomy.py does not classify.")
    parser.add_argument("save_files", type=Path, nargs="*", metavar="SAVE",
                        help="save file(s), e.g. ...\\Survival\\sandbox15")
    parser.add_argument("--catalog", type=Path, action="append", default=[], metavar="FILE",
                        help="game addressables catalog (JSON); may be given more than once")
    parser.add_argument("--out", type=Path, default=None,
                        help="also write the missing prefabs to this CSV (rewritten on every run)")
    args = parser.parse_args()
    if not args.save_files and not args.catalog:
        parser.error("give at least one save file or --catalog")

    print(f"Taxonomy: {len(TAXONOMY_LOOKUP)} entries")
    missing: dict[str, list[str]] = {}

    for save_file in args.save_files:
        save_path = save_file.expanduser()
        try:
            stacks, header, failed_scenes = prefabs_in_save(save_path)
        except (OSError, ValueError) as error:
            print(f"error: cannot read save {save_path}: {error}", file=sys.stderr)
            return 2
        not_classified = sorted(prefab for prefab in stacks if prefab not in TAXONOMY_LOOKUP)
        for prefab in not_classified:
            missing.setdefault(prefab, []).append(f"{save_path.name} ({stacks[prefab]} stacks)")
        optional_content = ", ".join(map(str, header.get("m_InstalledOptionalContent") or [])) or "none"
        display_name = header.get("m_DisplayName") or header.get("m_InternalName") or "unnamed"
        print(f"save     {save_path.name}: \"{display_name}\", saved {header.get('m_Timestamp')}, "
              f"build {header.get('m_Changelist')}, optional content {optional_content}, "
              f"{len(stacks)} prefabs, {len(not_classified)} missing")
        if failed_scenes:
            print(f"         {len(failed_scenes)} scene(s) could not be decoded, so this save was only "
                  f"partly checked: {', '.join(failed_scenes)}")

    for catalog_file in args.catalog:
        catalog_path = catalog_file.expanduser()
        try:
            names = prefabs_in_catalog(catalog_path)
        except (OSError, ValueError) as error:
            print(f"error: cannot read catalog {catalog_path}: {error}", file=sys.stderr)
            return 2
        not_classified = sorted(name for name in names if name not in TAXONOMY_LOOKUP)
        for prefab in not_classified:
            missing.setdefault(prefab, []).append(catalog_path.name)
        print(f"catalog  {catalog_path.name}: {len(names)} gear prefabs, {len(not_classified)} missing")

    if missing:
        print(f"\n{len(missing)} prefab name(s) missing from tld_taxonomy.py:")
        for prefab in sorted(missing):
            print(f"  {prefab}\t{'; '.join(missing[prefab])}")
    else:
        print("\nEvery prefab is classified.")

    if args.out is not None:
        try:
            with args.out.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["prefab", "found_in"])
                for prefab in sorted(missing):
                    writer.writerow([prefab, "; ".join(missing[prefab])])
        except OSError as error:
            print(f"error: cannot write {args.out}: {error}", file=sys.stderr)
            return 2
        print(f"Wrote {len(missing)} rows to {args.out}")

    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
