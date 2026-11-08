# Expert bankfull estimates

`expert_bankfull.csv` holds bankfull levels estimated by the author by visual inspection of
the cross-section profiles in QGIS. They will be used to compare the options of the method.
They are not produced by any algorithm and are not golden data of the original method.

| Column | Meaning |
|---|---|
| `source_file` | section file in `tests/data/sections/` (real sections only, no `synthetic.csv`) |
| `section_id` | section id in that file |
| `z_expert_low` | bank top of the inner active channel, where one exists |
| `z_expert_high` | bank top of the main floodplain |
| `note` | free remarks on the estimate |

- Both levels are absolute elevations in metres, same vertical reference as the DTM.
- Where the section has a single bank top, the two columns hold the same value.
- An empty cell means that level has not been estimated yet; every row has at least one of
  the two filled. When both are filled, `z_expert_low` ≤ `z_expert_high`.
- One row per real section, sorted by file and id. Comma separator, decimal point, UTF-8.
- The file lives outside `tests/data/sections/` because `golden_tools/make_curves.py` reads
  every CSV in that folder.
- Checked by `tests/test_expert_data.py`.