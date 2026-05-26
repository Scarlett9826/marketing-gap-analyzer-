# tools/

Helper scripts for data preparation. These are stand-alone utilities not
required by the main `mgap` pipeline.

## merge_user_data.py

Merge multiple `raw_user.json`-format files (de-duplicating by `post_id`).

```bash
python tools/merge_user_data.py file1.json file2.json -o merged.json
```

## validate_data.py

Sanity-check `raw_official.json` / `raw_user.json` against the expected schema.

```bash
python tools/validate_data.py path/to/raw_user.json
```
