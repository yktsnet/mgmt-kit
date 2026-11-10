# board

board を直す担当が、どこに何があり、何を守るかを知るための文書。

ladder の5軸で、評価・現在地・採用を1つのウェブアプリで回す。方針と決めたことは
[docs/decisions.md](docs/decisions.md) にある。FastAPI と Jinja2 の HTML で作り、フロントエンドのビルドは持たない。

## 動かす

```bash
cd board
python -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/uvicorn app.main:create_app --factory --port 8000
```

何も設定しなければ、`samples/` のダミーを読むデモで起動する。ログインの画面で在籍者を選んで入る。
環境変数は `app/config.py` にある。

## データの流れ

```text
Drive のシート / samples/drive/*.xlsx ─(sources/)─> sync.py ─> SQLite <─ settings.py・workflow.py・hiring.py（アプリが持つ値）
ladder の採点結果・usage の JSON ──────────────────────────────> SQLite
                                                                 │
                                         views.py（画面に出す値を組み立てる）
                                                                 │
                                         main.py（ルートと権限）─> templates/・static/
```

- **シートは写しとして読む。** `sync.py` が更新日時の変わったファイルだけを読み直し、`candidates`・`interviews`・`interview_verdicts`・`reviews`・`verdicts` を作り直す。シートの形の正本は [docs/sheets.md](docs/sheets.md)
- **アプリが持つ値は同期で消さない。** 定義と版・在籍者・採用枠・評価の状態と記録・次に上げる軸・選考の段階と記録。表は `app/store.py` にあり、どれが写しでどれがアプリの持ち物かを表の上に書いてある
- **画面は SQLite だけを読む。** 読み込み口が落ちても、前に読めた値で画面を出す

## モジュール

| ファイル | 受け持ち |
|---|---|
| `app/main.py` | ルート・ログインの確認・権限の確認。画面は `render`、書き込みの API は `apply` を通す |
| `app/access.py` | 誰が何を見られるか。一覧・1人のページ・現在地・API は、どれもここの決まりで絞る |
| `app/views.py` | 画面に出す値を SQLite から組み立てる。HTML は知らない |
| `app/store.py` | SQLite の表と、前の形の DB を今の形にする手当て |
| `app/sync.py` | 読み込み口と SQLite を突き合わせ、変わったファイルだけを読み直す |
| `app/sources/` | 読み込み口。`xlsx_folder.py`（手元のフォルダ）と `drive.py`（Drive と Sheets の API）が同じ形で返す |
| `app/parse.py` | 見出しの文字でシートを読む部品と、採用枠の確認 |
| `app/review.py` | 評価のシートを読み、細目の判定から軸の段階と本人の段階を決める |
| `app/hiring.py` | 候補者のシートを読み、面接の判定を細目ごとに合わせて段階を決める。選考の段階と記録 |
| `app/workflow.py` | 評価の状態（Draft → Submitted → Approved）と記録、次に上げる軸 |
| `app/definition.py` | 定義の細目と版。初版は `ladder/docs/ladder.md` から作る |
| `app/settings.py` | 設定を直す。直す前に読むときと同じ決まりで確かめる。デモの初期値を入れる |
| `app/people.py` | 在籍者と Reviewer の割り当ての確認 |
| `app/ladder.py` | ladder の採点結果と参照ペルソナの読み込み |
| `app/usage.py`・`app/usage_report.py` | usage の JSON の集計と、現在地に出す図と表。図と表は usage の `render.py` を呼ぶ |
| `app/demo.py` | デモの在籍者・採用枠・選考の段階 |
| `scripts/make_samples.py` | `templates/` と `samples/` を作り直す |

## 決まり

- **段階の決め方は1か所にある。** 決め方は [docs/sheets.md](docs/sheets.md) の「評価」、実装は `review.axis_result` で、評価も採用もこれを使う
- **版を直せるかは `settings.version_in_use` で確かめる。** 直せない条件は [docs/decisions.md](docs/decisions.md) にある
- **誤りは `SheetError` で返す。** 読み込みでは1ファイルだけを飛ばして画面に出し、API では 400 にする。権限が無いときは 403 にする
- **時刻は UTC の ISO 形式で持ち、画面で手元の時刻にする**（`main._when`）
- **シートの形を変えたら、`docs/sheets.md`・`scripts/make_samples.py`・`samples/` を一緒に直す。** `samples/` は `python scripts/make_samples.py` で作り直す

## テスト

`tests/` は、読み込み口・定義と版・細目からの段階・usage・ID トークン・見せる範囲（`test_access.py`）を確かめる。
アプリのテストはデモの在籍者でログインして確かめる。誰が誰の Reviewer かは `app/demo.py` にある。
