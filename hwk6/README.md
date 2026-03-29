# HW6

This directory adds the Homework 6 training workflow on top of the Homework 5 Cloud SQL and bucket setup style.

HW6 assumes the normalized tables already exist and have already been populated:

- `ip_addresses`
- `requests`

## Main pieces

- `train_models.py`: reads normalized data from Cloud SQL, trains both models, writes prediction CSVs and `metrics.txt`, uploads them to GCS
- `startup-trainer.sh`: VM startup script that clones the repo and runs the HW6 training job
- `setup.sh`: starts the database, creates the training VM, waits for the uploaded results, and prints them
- `cleanup.sh`: stops the HW6 VM and stops the Cloud SQL instance
- `sql/`: normalized schema and migration SQL

## Model outputs

The training script uploads the following files to `gs://$BUCKET_NAME/hwk6-results/` by default:

- `country_predictions.csv`
- `income_predictions.csv`
- `metrics.txt`

## Setup

Run the setup flow with:

```bash
bash hwk6/setup.sh
```

Useful environment variables:

```bash
PROJECT_ID=...
ZONE=...
REGION=...
BUCKET_NAME=...
DB_INSTANCE_NAME=...
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
GIT_REPO_URL=...
```

`setup.sh` will:

1. start the Cloud SQL instance
2. create the training VM
3. run `hwk6/train_models.py` on the VM
4. wait for the uploaded results
5. print `metrics.txt` and the first few lines of each prediction CSV

## Cleanup

Stop the resources with:

```bash
bash hwk6/cleanup.sh
```

## Logs

If the VM job fails, inspect the VM log with:

```bash
gcloud compute ssh jweb-hwk6-trainer --zone=us-central1-c --command='sudo tail -n 100 /var/log/jweb-hwk6-trainer.log'
```
