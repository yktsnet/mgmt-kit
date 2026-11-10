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
-- 在籍者。ladder の採点結果1ファイルにつき1人で、名前はファイル名（usage の名簿と同じ、メールの @ より前）
CREATE TABLE IF NOT EXISTS staff (
  email TEXT PRIMARY KEY,
  file_id TEXT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  period TEXT NOT NULL,
  level INTEGER
);
CREATE TABLE IF NOT EXISTS personas (
  level INTEGER NOT NULL,
  axis TEXT NOT NULL,
  value INTEGER NOT NULL,
  PRIMARY KEY (level, axis)
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
  -- manager は評価を Approve できる
  role TEXT NOT NULL DEFAULT 'member'
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
"""


def connect(path: Path | str) -> sqlite3.Connection:
    db = sqlite3.connect(path, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(SCHEMA)
    return db
