import os
import sys

from google.cloud.sql.connector import Connector


def main() -> None:
    instance_connection_name = os.environ["INSTANCE_CONNECTION_NAME"]
    db_user = os.environ["DB_USER"]
    db_password = os.environ["DB_PASSWORD"]
    db_name = os.environ["DB_NAME"]

    connector = Connector()
    connection = connector.connect(
        instance_connection_name,
        "pymysql",
        user=db_user,
        password=db_password,
        db=db_name,
    )

    schema_path = os.path.join(os.path.dirname(__file__), "sql", "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as handle:
        schema_sql = handle.read()

    try:
        with connection.cursor() as cursor:
            for statement in [part.strip() for part in schema_sql.split(";") if part.strip()]:
                cursor.execute(statement)
        connection.commit()
    finally:
        connection.close()
        connector.close()

    print("Initialized HW5 MySQL schema.", file=sys.stderr)


if __name__ == "__main__":
    main()
