DROP TABLE IF EXISTS records;
DROP TABLE IF EXISTS links;

CREATE TABLE records (
    hook TEXT NOT NULL,
    remote_addr TEXT,
    location TEXT,
    platform TEXT,
    browser TEXT,
    browser_version TEXT,
    user_agent TEXT
);

CREATE TABLE links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link TEXT UNIQUE NOT NULL,
    token password NOT NULL
);
