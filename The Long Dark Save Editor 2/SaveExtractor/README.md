# SaveExtractor

Python tools that read The Long Dark survival saves (game v2.44 and later). They only
read: no save file is ever written. Standard library only, Python 3.9 or newer.

| File | What it does |
|---|---|
| `tld_save_reader.py` | Lists every item in a save, as a summary or a CSV |
| `tld_taxonomy.py` | The item table: category for each `GEAR_` prefab, and where the prefab comes from |
| `tld_prefab_diff.py` | Checks the item table against saves and the game's own item catalogs |
| `tld_save_codec.py` | Decodes a save and encodes it again, exactly. Its `verify` command checks that a save rebuilds byte for byte |
| `test_tld_save_codec.py` | Tests for `tld_save_codec.py` |

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

## Check that a save can be rebuilt exactly

`tld_save_codec.py` decodes every layer of a save, encodes it again, and compares the
result with the original file, byte for byte. It is the safety check for any future tool
that changes a save: an edit can only be trusted if an unedited save comes back identical.

```powershell
python tld_save_codec.py verify "$env:LOCALAPPDATA\Hinterland\TheLongDark\Survival"
python tld_save_codec.py verify "$env:LOCALAPPDATA\Hinterland\TheLongDark\Survival\sandbox1"
```

Given a folder, it checks the save files directly inside it (`sandbox1`, `challenge3`,
`ep1sandbox2` and so on) and ignores everything else. Allow about a second per save.

```text
sandbox1     1,096,887 bytes   20 entries    7,400 documents  IDENTICAL
sandbox15      180,665 bytes    6 entries    2,786 documents  IDENTICAL
2 of 2 saves rebuild byte for byte.
```

| Result | Meaning |
|---|---|
| `IDENTICAL` | The rebuilt save is byte for byte the original |
| `FAILED` | It is not. The next line says why |

Exit code 0 means every save was identical, 1 means at least one failed, and 2 means a
path was wrong.

Two things make an exact rebuild possible:

- Numbers are kept exactly as the game wrote them. The game writes forms such as
  `6.204471E-05`, which Python's `json` module would write back as `6.204471e-05`.
- The compressor is a port of `Helpers\CLZF.cs` in this repository. It produces the same
  bytes as the game's own compressor.

A document that cannot be written back identically is refused. Nothing is changed silently.

Checked on 2026-11-20: 15 of 15 real saves rebuild byte for byte. They span game
changelists 157357 to 189457 (v2.60).

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

## Run the tests

```powershell
python -m unittest -v
```

The tests build their own small saves, so they need no game files. To check your real
saves as well, point `TLD_SAVE_DIR` at their folder first:

```powershell
$env:TLD_SAVE_DIR = "$env:LOCALAPPDATA\Hinterland\TheLongDark\Survival"
python -m unittest -v
```

The expected compressor output in the tests comes from the C# compressor in this
repository, `Helpers\CLZF.cs`.

## Known gaps

- `region` stays blank for the two mine transition zones and for reused interiors
  (such as `TrailerC`) in a save that has visited more than one region.
- Water is reported as one stack. The volume is not read.
- Saves from before 2018 use a different format and are not supported.
- No save checked so far contains text outside plain ASCII. If the game writes such text
  in a form `tld_save_codec.py` does not reproduce, `verify` reports `FAILED` for that save.
