# Expert bankfull estimates

`expert_bankfull.csv` holds bankfull levels estimated by the author by visual inspection of
the cross-section profiles in QGIS. They will be used to compare the options of the method.
They are not produced by any algorithm and are not golden data of the original method.

| Column | Meaning |
|---|---|
| `source_file` | section file in `tests/data/sections/` (real sections only, no `synthetic.csv`) |
| `section_id` | section id in that file |
| `z_expert` | estimated bankfull level: absolute elevation in metres, same vertical reference as the DTM |
| `note` | free remarks on the estimate |

- One row per real section, sorted by file and id. Comma separator, decimal point, UTF-8.
- An empty `z_expert` means the section has not been estimated yet.
- The file lives outside `tests/data/sections/` because `golden_tools/make_curves.py` reads
  every CSV in that folder.
- Checked by `tests/test_expert_data.py`.