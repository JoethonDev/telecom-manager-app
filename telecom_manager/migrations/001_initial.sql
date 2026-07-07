CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '',
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ssh_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_note TEXT,
    sni TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS vmess_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    uuid TEXT UNIQUE NOT NULL,
    sni TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS vless_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    uuid TEXT UNIQUE NOT NULL,
    sni TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS usage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    type TEXT NOT NULL,
    bytes_in INTEGER DEFAULT 0,
    bytes_out INTEGER DEFAULT 0,
    logged_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_usage_logged_at ON usage_log(logged_at);

CREATE TABLE IF NOT EXISTS monitoring_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cpu_pct REAL NOT NULL DEFAULT 0,
    mem_pct REAL NOT NULL DEFAULT 0,
    disk_pct REAL NOT NULL DEFAULT 0,
    sampled_at INTEGER NOT NULL
);

INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES ('schema_version', '5', 0);
