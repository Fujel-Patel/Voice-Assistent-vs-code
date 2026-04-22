CREATE TABLE IF NOT EXISTS voice_profiles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT UNIQUE NOT NULL,
  embedding BLOB NOT NULL,
  sample_count INTEGER NOT NULL DEFAULT 0,
  profile_strength REAL NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS auth_attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  confidence REAL NOT NULL,
  verified INTEGER NOT NULL,
  threshold REAL NOT NULL,
  mode TEXT NOT NULL,
  created_at TEXT NOT NULL
);
