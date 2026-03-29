INSERT IGNORE INTO ip_addresses (client_ip, country)
SELECT DISTINCT client_ip, country
FROM request_logs;

INSERT IGNORE INTO requests (
    id,
    client_ip,
    gender,
    age,
    income,
    is_banned,
    time_of_day,
    requested_file,
    request_time
)
SELECT
    id,
    client_ip,
    gender,
    age,
    income,
    is_banned,
    time_of_day,
    requested_file,
    request_time
FROM request_logs;
