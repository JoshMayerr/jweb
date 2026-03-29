CREATE TABLE ip_addresses (
    client_ip VARCHAR(64) NOT NULL PRIMARY KEY,
    country VARCHAR(128) NOT NULL
);

CREATE TABLE requests (
    id INT NOT NULL PRIMARY KEY,
    client_ip VARCHAR(64) NOT NULL,
    gender VARCHAR(32) NOT NULL,
    age INT NULL,
    income VARCHAR(64) NOT NULL,
    is_banned TINYINT(1) NOT NULL,
    time_of_day VARCHAR(32) NOT NULL,
    requested_file TEXT NOT NULL,
    request_time TIMESTAMP NOT NULL,
    CONSTRAINT fk_requests_client_ip
        FOREIGN KEY (client_ip) REFERENCES ip_addresses(client_ip)
);
