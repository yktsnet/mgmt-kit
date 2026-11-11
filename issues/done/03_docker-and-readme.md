## board を docker compose で起動でき、本物の Google につなぐ手順と人向けの README がそろった形にする
id: 03
branch-slug: docker-and-readme
status: close
depends: 02
type: feat
対象: board/Dockerfile（新規）、board/docker-compose.yml（新規）、board/.dockerignore（新規）、board/docs/setup.md（新規）、board/README.md、board/docs/（エージェント向けの節を移すなら移し先を新規）、CLAUDE.md、README.md
目的: board を公開できる形にする。何も設定せずに `docker compose up` だけでデモが起動し、手順のとおりに設定すれば本物の Google（Sign in with Google と Drive）につながる。外から来た人が README で、何のための道具で何が見えるかをつかめるようにする。
内容: Dockerfile と docker-compose.yml を足し、DB を volume に置く。本番の設定の手順を `board/docs/setup.md` に書く。`board/README.md` を人向けにし、いまのエージェント向けの節（データの流れ・モジュール・決まり）は `board/docs/` へ移す。mgmt-kit の README の道具の表に board を足し、`ladder.md` を定義の正本とする記述を直す。
対象外: `ladder/README.md` の位置づけ（04）。画面の作りの見直し（02）。CI（05）。main を守るブランチの設定
仮定:
- エージェント向けの節は `board/docs/` へ移し、`board/README.md` を人向けにする（#37 で「移してもよい」とした案を取った）。移したら `CLAUDE.md` の表の `board/` の行の先に読むものを移し先へ直す
- 画面の写真と GIF は 02 で直したあとの画面で撮る（そのため `depends: 02`）
- 本番の手順は `board/docs/setup.md` 1本にまとめる
確認:
- 何も設定せずに `cd board && docker compose up` で起動し、デモのログインから評価の1人のページまで開ける
- 設定の画面で何かを変え、`docker compose down` と `up` のあとも残っている（DB が volume にある）
- `board/docs/setup.md` に、OAuth クライアントと `BOARD_GOOGLE_CLIENT_ID`・`BOARD_ALLOWED_DOMAIN`・`BOARD_SESSION_KEY`、サービスアカウントと Drive のフォルダの共有と `BOARD_SOURCE=drive`・`BOARD_DRIVE_FOLDER_ID`・`BOARD_SERVICE_ACCOUNT_KEY` の手順がある。手順に出る環境変数がすべて `board/app/config.py` で読まれている
- `board/README.md` の「動かす」が `docker compose up` を先に書いた形になっている
- `board/README.md` に、何のための道具か、画面（評価・現在地・採用・設定）と役割ごとに見えるもの、データの置き場（設定・状態・記録はアプリ、判定・候補者・面接は Drive のシート）、起動の仕方、`board/docs/sheets.md` への入口があり、図と GIF が入っている
- `CLAUDE.md` の表の `board/` の行が、エージェント向けの節の移し先を指している
- mgmt-kit の README の道具の表に board があり、`ladder.md` を定義の正本とする記述が「board では定義の正本はアプリの設定で、`ladder.md` は初版の出どころ」という形に直っている
- `cd board && python -m pytest -q` が通る
人が見るもの: 手順のとおりに設定し、本物の Google のアカウントでログインでき、Drive のシートが読み込まれることを1回通して確かめる

---

### 保証
- 新たに宣言する保証:
  - 起動：何も設定せずに `docker compose up` で、デモ（手元の `.xlsx` とデモのログイン）が起動する
  - 保存：コンテナを作り直しても、設定・評価の状態・選考の段階・記録が消えない
- 維持する保証:
  - venv で uvicorn を起動する手順でも動く（既存のテストがすべて通る）
  - 環境変数で Google と Drive に切り替える振る舞い（`config.py` の読み方を変えない）

### board/Dockerfile・docker-compose.yml
Python 3.12。DB（`board/data/board.db`）の置き場を volume にする。何も設定しなければデモで起動する。

### board/README.md・board/docs/
README は人向けにする。ポートフォリオでの語り方は「非エンジニアは使い慣れたスプレッドシートを書くだけで、つなぐのはエンジニアリングの側」という形にする。

### README.md
道具の表に board を足す。`ladder.md` の位置づけの記述を直す。`ladder/README.md` の位置づけは 04 で直すので触れない。

### 文書の校正
新しい `.md` と見出しの変更を、jp-proofreader と md-reviewer にかける。
