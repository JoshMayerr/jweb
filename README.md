# CS528 HW2 — PageRank on web graph

The program **always** reads HTML files from a local directory (default `./web`). Data is not read directly from Google Cloud Storage; you must download it first using the shell script.

## Running the program

Use `run.sh` to download from GCS and/or run the pipeline.

- **Download and run** (first time or full run):
  ```bash
  ./run.sh
  ```
  or explicitly:
  ```bash
  ./run.sh all
  ```
  This downloads `gs://jweb-content/web/*` into `./web`, then runs the PageRank pipeline.

- **Download only** (e.g. to refresh data or prepare for offline runs):
  ```bash
  ./run.sh download
  ```

- **Run only** (data must already be in `./web`):
  ```bash
  ./run.sh run
  ```

To test that the bucket is set up correctly, run download first (e.g. `./run.sh download`), then run. TAs can use the same flow: download, then run.

## Configuration

You can override the bucket and data directory via environment variables:

```bash
BUCKET=my-bucket DATA_DIR=./my-web ./run.sh
```

Default: `BUCKET=jweb-content`, `DATA_DIR=./web`.

## Running Python directly

If you already have HTML files in a directory:

```bash
python hw2.py --data-dir ./web
```

Optional arguments:

- `--data-dir DIR` — Directory containing `*.html` files (default: `./web`).
- `--test` — Run the self-test (no data directory needed).

## Requirements

- Python 3 with dependencies from `pyproject.toml` (e.g. `uv sync` or `pip install -e .`).
- For `run.sh download`: `gsutil` or `gcloud` (Google Cloud SDK) and access to the bucket.
