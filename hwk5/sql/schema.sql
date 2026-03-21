CREATE TABLE IF NOT EXISTS request_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    country VARCHAR(128),
    client_ip VARCHAR(64),
    gender VARCHAR(32),
    age_group VARCHAR(32),
    income_group VARCHAR(32),
    is_banned BOOLEAN NOT NULL,
    request_time DATETIME NOT NULL,
    time_of_day VARCHAR(32) NOT NULL,
    requested_file VARCHAR(255) NOT NULL,
    status_code INT NOT NULL
);

CREATE TABLE IF NOT EXISTS error_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    request_time DATETIME NOT NULL,
    requested_file VARCHAR(255) NOT NULL,
    error_code INT NOT NULL
);
