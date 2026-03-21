# HW5

This directory extends Homework 4 with Cloud SQL MySQL logging and simple timing summaries.

HW5 is configured to serve HTTP on port `80` in GCP.

## Main pieces

- `first_service/`: web server that serves from GCS, logs requests to MySQL, and prints timing summaries
- `second_service/`: unchanged forbidden-country subscriber service
- `cloud_function/`: hourly function that stops the Cloud SQL instance
- `init_db.py`: creates the MySQL schema from `sql/schema.sql`
- `stats.py`: prints the required homework statistics
- `setup.sh`: creates/starts the Cloud SQL instance and both HW5 VMs, then deploys the Cloud Function
- `cleanup.sh`: stops the HW5 VMs and stops the Cloud SQL instance

## Local commands

Sync dependencies:

```bash
uv sync --project hwk5/first_service
uv sync --project hwk5/second_service
uv sync --project hwk5/cloud_function
```

Create schema:

```bash
INSTANCE_CONNECTION_NAME=... DB_NAME=... DB_USER=... DB_PASSWORD=... \
uv run --project hwk5/first_service hwk5/init_db.py
```

Run the stats query helper:

```bash
INSTANCE_CONNECTION_NAME=... DB_NAME=... DB_USER=... DB_PASSWORD=... \
uv run --project hwk5/first_service hwk5/stats.py
```
