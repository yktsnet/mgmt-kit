"""読み込んだ値を置く SQLite。画面は読み込み口ではなく、ここだけを読む。"""

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
  id TEXT PRIMARY KEY,
  path TEXT NOT NULL,
  modified TEXT NOT NULL,
  kind TEXT NOT NULL,
  error TEXT,
  -- 最後に直した人。Drive からだけ取れる
  modified_by TEXT
);
CREATE TABLE IF NOT EXISTS candidates (
  email TEXT PRIMARY KEY,
  file_id TEXT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  requisition TEXT NOT NULL,
  -- 面接の判定が使う Ladder の版
  version INTEGER NOT NULL,
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
CREATE TABLE IF NOT EXISTS interview_verdicts (
  email TEXT NOT NULL,
  seq INTEGER NOT NULL,
  item TEXT NOT NULL,
  verdict TEXT NOT NULL,
  note TEXT NOT NULL,
  PRIMARY KEY (email, seq, item),
  FOREIGN KEY (email, seq) REFERENCES interviews(email, seq) ON DELETE CASCADE
);
-- 選考の段階と記録はアプリが持つ。シートから作り直す写しではないので、同期では消さない
CREATE TABLE IF NOT EXISTS candidate_stages (
  email TEXT PRIMARY KEY,
  stage TEXT NOT NULL,
  at TEXT NOT NULL,
  by TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS candidate_records (
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL,
  at TEXT NOT NULL,
  by TEXT NOT NULL,
  kind TEXT NOT NULL,
  body TEXT NOT NULL
);
-- ここから下の設定（採用枠・定義・在籍者）はアプリが持つ。シートから作り直す写しではないので、同期では消さない
CREATE TABLE IF NOT EXISTS requisitions (
  name TEXT PRIMARY KEY,
  count INTEGER NOT NULL,
  persona TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS requisition_targets (
  name TEXT NOT NULL REFERENCES requisitions(name) ON DELETE CASCADE,
  axis TEXT NOT NULL,
  value INTEGER NOT NULL,
  PRIMARY KEY (name, axis)
);
-- usage の直近 WINDOW_DAYS 日の合計。人が書く値ではないので、集計のたびに作り直す
CREATE TABLE IF NOT EXISTS usage (
  email TEXT PRIMARY KEY,
  since TEXT NOT NULL,
  until TEXT NOT NULL,
  active_days INTEGER NOT NULL,
  cost_usd REAL NOT NULL,
  active_seconds INTEGER NOT NULL,
  sessions INTEGER NOT NULL,
  commits INTEGER NOT NULL,
  pull_requests INTEGER NOT NULL,
  lines_added INTEGER NOT NULL,
  skills INTEGER NOT NULL,
  issues_opened INTEGER NOT NULL
);
-- 定義。版ごとに5軸×5段階の細目を持つ。前の版も消さず、前の版で付けた評価をそのまま読めるようにする
CREATE TABLE IF NOT EXISTS definition_items (
  version INTEGER NOT NULL,
  axis TEXT NOT NULL,
  level INTEGER NOT NULL,
  key TEXT NOT NULL,
  text TEXT NOT NULL,
  evidence TEXT NOT NULL,
  PRIMARY KEY (version, axis, level, key)
);
-- 在籍者の名簿と、評価する担当（Reviewer）の割り当て。担当は名簿の中の誰か
CREATE TABLE IF NOT EXISTS people (
  email TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  evaluator TEXT,
  -- manager は評価を Approve でき、すべてを見られる
  role TEXT NOT NULL DEFAULT 'member',
  -- 採用（候補者・面接の所見）を見られる。manager は付けなくても見られる
  hiring INTEGER NOT NULL DEFAULT 0
);
-- 評価1件（評価される人1人・期1つ）と、細目ごとの判定
CREATE TABLE IF NOT EXISTS reviews (
  file_id TEXT PRIMARY KEY REFERENCES files(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  period TEXT NOT NULL,
  version INTEGER NOT NULL,
  reviewer TEXT
);
CREATE TABLE IF NOT EXISTS verdicts (
  file_id TEXT NOT NULL REFERENCES reviews(file_id) ON DELETE CASCADE,
  item TEXT NOT NULL,
  verdict TEXT NOT NULL,
  note TEXT NOT NULL,
  PRIMARY KEY (file_id, item)
);
-- 評価の状態と記録はアプリが持つ。シートから作り直す写しではないので、同期では消さない
CREATE TABLE IF NOT EXISTS review_states (
  email TEXT NOT NULL,
  period TEXT NOT NULL,
  state TEXT NOT NULL,
  at TEXT NOT NULL,
  by TEXT NOT NULL,
  PRIMARY KEY (email, period)
);
CREATE TABLE IF NOT EXISTS review_records (
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL,
  period TEXT NOT NULL,
  at TEXT NOT NULL,
  by TEXT NOT NULL,
  kind TEXT NOT NULL,
  body TEXT NOT NULL
);
-- 次に上げる1軸。最も低い軸から出し、Reviewer か Manager が変えたときだけここに残す
CREATE TABLE IF NOT EXISTS growth_plans (
  email TEXT NOT NULL,
  period TEXT NOT NULL,
  axis TEXT NOT NULL,
  at TEXT NOT NULL,
  by TEXT NOT NULL,
  PRIMARY KEY (email, period)
);
"""


def connect(path: Path | str) -> sqlite3.Connection:
    db = sqlite3.connect(path, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    # 候補者と面接はシートから作り直す写しなので、前の形（軸ごとの点）なら作り直す。
    # 行の無い候補者のファイルは同期で読み直される
    cols = {r[1] for r in db.execute("PRAGMA table_info(candidates)")}
    rebuild = bool(cols) and "version" not in cols
    if rebuild:
        db.executescript("DROP TABLE IF EXISTS interviews; DROP TABLE candidates;")
    db.executescript(SCHEMA)
    # 前の形の DB に残る、どこも読まない表と読み込みの記録を消す。記録の誤りは画面に出続けるので一緒に消す
    db.executescript(
        "DROP TABLE IF EXISTS scores; DROP TABLE IF EXISTS staff; DROP TABLE IF EXISTS personas;"
        "DELETE FROM files WHERE kind IN ('scoresheet', 'personas');"
    )
    # 前の形で作った DB に、あとから足した列を足す
    cols = {r[1] for r in db.execute("PRAGMA table_info(files)")}
    if "modified_by" not in cols:
        db.execute("ALTER TABLE files ADD COLUMN modified_by TEXT")
    if "hiring" not in {r[1] for r in db.execute("PRAGMA table_info(people)")}:
        db.execute("ALTER TABLE people ADD COLUMN hiring INTEGER NOT NULL DEFAULT 0")
    return db
