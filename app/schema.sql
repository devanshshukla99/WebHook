DROP TABLE IF EXISTS records;
DROP TABLE IF EXISTS links;

CREATE TABLE records (
    hook TEXT NOT NULL,
    remote_addr TEXT NOT NULL,
    location TEXT,
    platform TEXT NOT NULL,
    browser TEXT NOT NULL,
    browser_version TEXT NOT NULL,
    user_agent TEXT NOT NULL
);

CREATE TABLE links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link TEXT UNIQUE NOT NULL,
    token password NOT NULL
);
