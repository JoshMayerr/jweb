import os

from google.cloud.sql.connector import Connector


def fetch_all(cursor, title: str, query: str) -> None:
    print(title)
    cursor.execute(query)
    rows = cursor.fetchall()
    for row in rows:
        print(row)
    print()


def main() -> None:
    connector = Connector()
    connection = connector.connect(
        os.environ["INSTANCE_CONNECTION_NAME"],
        "pymysql",
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        db=os.environ["DB_NAME"],
    )

    try:
        with connection.cursor() as cursor:
            fetch_all(
                cursor,
                "Successful vs unsuccessful requests",
                """
                SELECT
                    SUM(CASE WHEN status_code = 200 THEN 1 ELSE 0 END) AS successful_requests,
                    SUM(CASE WHEN status_code <> 200 THEN 1 ELSE 0 END) AS unsuccessful_requests
                FROM request_logs
                """,
            )
            fetch_all(cursor, "Requests from banned countries", "SELECT COUNT(*) AS banned_requests FROM request_logs WHERE is_banned = TRUE")
            fetch_all(
                cursor,
                "Requests by gender",
                "SELECT gender, COUNT(*) AS request_count FROM request_logs GROUP BY gender ORDER BY request_count DESC",
            )
            fetch_all(
                cursor,
                "Top 5 countries",
                """
                SELECT country, COUNT(*) AS request_count
                FROM request_logs
                GROUP BY country
                ORDER BY request_count DESC
                LIMIT 5
                """,
            )
            fetch_all(
                cursor,
                "Most frequent age group",
                """
                SELECT age_group, COUNT(*) AS request_count
                FROM request_logs
                GROUP BY age_group
                ORDER BY request_count DESC
                LIMIT 1
                """,
            )
            fetch_all(
                cursor,
                "Most frequent income group",
                """
                SELECT income_group, COUNT(*) AS request_count
                FROM request_logs
                GROUP BY income_group
                ORDER BY request_count DESC
                LIMIT 1
                """,
            )
    finally:
        connection.close()
        connector.close()


if __name__ == "__main__":
    main()
