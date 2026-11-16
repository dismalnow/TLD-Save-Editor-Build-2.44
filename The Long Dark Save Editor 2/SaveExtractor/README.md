# SaveExtractor

Python tools that read The Long Dark survival saves (game v2.44 and later). They only
read: no save file is ever written. Standard library only, Python 3.9 or newer.

| File | What it does |
|---|---|
| `tld_save_reader.py` | Lists every item in a save, as a summary or a CSV |
| `tld_taxonomy.py` | The item table: category for each `GEAR_` prefab, and where the prefab comes from |
| `tld_prefab_diff.py` | Checks the item table against saves and the game's own item catalogs |

The wiki helper lives in `..\tld_mediawiki_api\tld_wiki_updater.py`.

Run the commands below from this folder. From anywhere else, put this folder's full
path in front of the script name, or Python will not find the script.

## Read a save

```powershell
$save = "$env:LOCALAPPDATA\Hinterland\TheLongDark\Survival\sandbox1"
python tld_save_reader.py $save --summary
python tld_save_reader.py $save --out items.csv
python tld_save_reader.py $save --out items.csv --include-unsearched
```

`--csv` without `--out` writes `<save>.csv` next to the save, which is inside the game's
save folder. Use `--out` to write somewhere else.

`--include-unsearched` adds the loot waiting in containers you have not opened yet. That
is a spoiler, so it is off by default.

### CSV columns

| Column | Meaning |
|---|---|
| `region`, `location` | Where the item is. `region` is blank when it cannot be determined |
| `location_type` | `player_inventory`, `floor`, `scripted` (placed by the game, not interactive yet), `container`, `container_unsearched` |
| `container` | Container name, for items in containers |
| `category`, `subcategory` | From `tld_taxonomy.py`. `Unknown` means the prefab is not in the table |
| `item`, `prefab` | Readable name and the `GEAR_` prefab name |
| `count`, `condition_pct` | Stack size and condition. Both are unknown for unsearched loot |
| `x`, `y`, `z` | Position in the scene |
| `source` | `base`, `DLC01` (Tales from the Far Territory), `DLC02` (Iron Road), `mod:<pack>`, or `legacy` |

## Keep the item table current

Run this after a game update or after adding an item mod. It exits with 0 when every
prefab is classified and lists the missing names otherwise.

```powershell
$game = "C:\Program Files (x86)\Steam\steamapps\common\TheLongDark"   # your game folder
python tld_prefab_diff.py `
  --catalog "$game\tld_Data\StreamingAssets\aa\catalog.json" `
  --catalog "$game\tld_dlc\TFTFT\DLC01.json" `
  --catalog "$game\tld_dlc\IronRoad\DLC02.json"

python tld_prefab_diff.py (Get-ChildItem "$env:LOCALAPPDATA\Hinterland\TheLongDark\Survival\sandbox*" -Exclude *.csv).FullName
```

The catalogs are the authoritative list of game items. Saves add the items that mods
define. Add each missing name to `TAXONOMY_LOOKUP`, and to `DLC_PREFABS` or `MOD_PREFABS`
when it is not a base game item.

## Where the item table comes from

Checked on 2026-11-16 against game v2.60 (changelist 189457):

- the game's addressables catalogs: 710 gear prefabs (438 base, 246 DLC01, 26 DLC02)
- `Helpers\ItemDictionary.cs` in this repository: 473 names, current to game v2.27
- 15 real saves, one of them a developer-console `add_all_gear` dump
- five ModComponent packs: FoodPackByTKG, RetroFood, ItemPiles, MoreWood, LitharsRidge

The categories are a grouping for reports. They are not the game's inventory categories.

## Known gaps

- `region` stays blank for the two mine transition zones and for reused interiors
  (such as `TrailerC`) in a save that has visited more than one region.
- Water is reported as one stack. The volume is not read.
- Saves from before 2018 use a different format and are not supported.
