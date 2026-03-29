import os
from pathlib import Path

import pandas as pd
import pymysql
from google.cloud import storage
from google.cloud.sql.connector import Connector
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

RANDOM_SEED = int(os.environ.get("RANDOM_SEED", "42"))
RESULTS_PREFIX = os.environ.get("RESULTS_PREFIX", "hwk6-results")
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/tmp/hwk6-results"))


def fetch_training_data() -> pd.DataFrame:
    connector = Connector()
    connection = connector.connect(
        os.environ["INSTANCE_CONNECTION_NAME"],
        "pymysql",
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        db=os.environ["DB_NAME"],
        cursorclass=pymysql.cursors.DictCursor,
    )

    query = """
        SELECT
            r.id,
            r.client_ip,
            i.country,
            r.gender,
            r.age,
            r.income,
            r.is_banned,
            r.time_of_day,
            r.requested_file,
            r.request_time
        FROM requests AS r
        JOIN ip_addresses AS i
            ON r.client_ip = i.client_ip
        ORDER BY r.id
    """

    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
    finally:
        connection.close()
        connector.close()

    return pd.DataFrame(rows)


def choose_stratify_target(target: pd.Series) -> pd.Series | None:
    if target.nunique() < 2:
        return None
    if target.value_counts().min() < 2:
        return None
    return target


def build_model() -> Pipeline:
    return Pipeline(
        [
            ("vectorizer", DictVectorizer(sparse=True)),
            ("classifier", DecisionTreeClassifier(random_state=RANDOM_SEED)),
        ]
    )


def train_and_save_predictions(
    data_frame: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
    output_name: str,
) -> tuple[float, int]:
    working_frame = data_frame[feature_columns + [target_column]].copy()
    if "age" in working_frame.columns:
        working_frame["age"] = working_frame["age"].fillna(-1).astype(int)

    target = working_frame[target_column].astype(str)
    if len(working_frame) < 5:
        raise ValueError(f"Not enough rows to train {target_column} model. Need at least 5 rows.")
    if target.nunique() < 2:
        raise ValueError(f"Need at least two target classes to train {target_column} model.")

    features = working_frame[feature_columns].copy()
    feature_records = features.to_dict(orient="records")

    x_train, x_test, y_train, y_test = train_test_split(
        feature_records,
        target,
        test_size=0.2,
        random_state=RANDOM_SEED,
        stratify=choose_stratify_target(target),
    )

    model = build_model()
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    accuracy = accuracy_score(y_test, predictions)

    prediction_frame = pd.DataFrame(x_test)
    prediction_frame[f"actual_{target_column}"] = list(y_test)
    prediction_frame[f"predicted_{target_column}"] = list(predictions)
    prediction_frame.to_csv(OUTPUT_DIR / output_name, index=False)
    return accuracy, len(working_frame)


def upload_file(bucket: storage.Bucket, local_path: Path) -> None:
    blob = bucket.blob(f"{RESULTS_PREFIX}/{local_path.name}")
    blob.upload_from_filename(str(local_path))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data_frame = fetch_training_data()
    if data_frame.empty:
        raise ValueError("No rows found in normalized tables.")

    storage_client = storage.Client()
    bucket = storage_client.bucket(os.environ["BUCKET"])

    country_accuracy, country_rows = train_and_save_predictions(
        data_frame,
        feature_columns=["client_ip"],
        target_column="country",
        output_name="country_predictions.csv",
    )
    print(f"Country model accuracy: {country_accuracy:.4f}")

    income_accuracy, income_rows = train_and_save_predictions(
        data_frame,
        feature_columns=[
            "client_ip",
            "country",
            "gender",
            "age",
            "is_banned",
            "time_of_day",
            "requested_file",
        ],
        target_column="income",
        output_name="income_predictions.csv",
    )
    print(f"Income model accuracy: {income_accuracy:.4f}")

    metrics_path = OUTPUT_DIR / "metrics.txt"
    metrics_path.write_text(
        "\n".join(
            [
                f"country_model_accuracy={country_accuracy:.4f}",
                f"country_model_rows={country_rows}",
                f"income_model_accuracy={income_accuracy:.4f}",
                f"income_model_rows={income_rows}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    for filename in ["country_predictions.csv", "income_predictions.csv", "metrics.txt"]:
        upload_file(bucket, OUTPUT_DIR / filename)

    print(f"Uploaded results to gs://{os.environ['BUCKET']}/{RESULTS_PREFIX}/")


if __name__ == "__main__":
    main()
