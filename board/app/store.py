"""読み込んだ値を置く SQLite。画面は読み込み口ではなく、ここだけを読む。"""

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
  id TEXT PRIMARY KEY,
  path TEXT NOT NULL,
  modified TEXT NOT NULL,
  kind TEXT NOT NULL,
  error TEXT
);
CREATE TABLE IF NOT EXISTS candidates (
  email TEXT PRIMARY KEY,
  file_id TEXT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  requisition TEXT NOT NULL,
  stage TEXT NOT NULL,
  applied TEXT,
  source TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS interviews (
  email TEXT NOT NULL REFERENCES candidates(email) ON DELETE CASCADE,
  seq INTEGER NOT NULL,
  date TEXT,
  interviewer TEXT NOT NULL,
  note TEXT NOT NULL,
  PRIMARY KEY (email, seq)
);
-- 人と軸ごとの点。出どころ（interview・ladder）を分けて持ち、画面で並べる
CREATE TABLE IF NOT EXISTS scores (
  email TEXT NOT NULL,
  origin TEXT NOT NULL,
  axis TEXT NOT NULL,
  value INTEGER NOT NULL,
  PRIMARY KEY (email, origin, axis)
);
CREATE TABLE IF NOT EXISTS requisitions (
  name TEXT PRIMARY KEY,
  file_id TEXT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
  count INTEGER NOT NULL,
  persona TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS requisition_targets (
  name TEXT NOT NULL REFERENCES requisitions(name) ON DELETE CASCADE,
  axis TEXT NOT NULL,
  value INTEGER NOT NULL,
  PRIMARY KEY (name, axis)
);
"""


def connect(path: Path | str) -> sqlite3.Connection:
    db = sqlite3.connect(path, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(SCHEMA)
    return db
