# CS528 HW7

This homework uses Apache Beam to compute:

- top 5 files by outgoing links
- top 5 files by incoming links
- top 5 most frequent word bigrams

The code is intentionally simple because the HTML files are simple and consistent.

## Defaults

- Local input: `/Users/joshmayer/Developer/BU/spring26/cs528/jweb/web/*.html`
- Local output: `/Users/joshmayer/Developer/BU/spring26/cs528/jweb/hwk7/output/local`
- Cloud input: `gs://jweb-content/web/*.html`
- Cloud output: `gs://jweb-content/hwk7/output`

## Local run

Run from the repo root:

```bash
uv run --project hwk7 python hwk7/pipeline.py --runner=DirectRunner
```

Or run from inside `hwk7/`:

```bash
cd hwk7
uv run python pipeline.py --runner=DirectRunner
```

Results are written to:

- `/Users/joshmayer/Developer/BU/spring26/cs528/jweb/hwk7/output/local/outgoing.txt`
- `/Users/joshmayer/Developer/BU/spring26/cs528/jweb/hwk7/output/local/incoming.txt`
- `/Users/joshmayer/Developer/BU/spring26/cs528/jweb/hwk7/output/local/bigrams.txt`

## Cloud run

Replace `YOUR_PROJECT` with your Google Cloud project:

```bash
uv run --project hwk7 python hwk7/pipeline.py \
  --cloud \
  --runner=DataflowRunner \
  --project=YOUR_PROJECT \
  --region=us-central1 \
  --temp_location=gs://jweb-content/hwk7/temp \
  --staging_location=gs://jweb-content/hwk7/staging \
  --job_name=cs528-hw7
```

## Notes

- Links are extracted with a regex for `HREF="123.html"`.
- Text is processed by stripping tags and then tokenizing words.
- Bigrams are consecutive word pairs after lowercasing.
