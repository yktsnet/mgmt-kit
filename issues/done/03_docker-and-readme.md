## PR記録: feat: Run board with docker compose and add setup and human-facing README
issue: 03 (03_docker-and-readme.md)
PR: https://github.com/yktsnet/mgmt-kit/pull/50

## 変更内容
- `board/Dockerfile`・`docker-compose.yml`・`.dockerignore` を足した。何も設定せずに `cd board && docker compose up` でデモが起動する。ビルドの文脈は `board/` で、リポの `ladder/docs/ladder.md` と `usage/tools/usage` は追加の文脈 `repo` からリポの中と同じ位置に写す。DB は volume（`/data/board.db`）に置き、`127.0.0.1:8000` で待ち受ける。`board.env` があれば読み込む
- 本物の Google でログインしたドメインの人を、初めて入ったときに Member として在籍者に載せる。`BOARD_MANAGERS` に書いた人は Manager にし、下げはしない（`settings.register`）。デモでないとき在籍者が0人で始まり、誰も入れなかったため。方針は `decisions.md` の「作り」に書いた（user と決めた）
- `board/docs/setup.md` に、OAuth クライアント・サービスアカウントと Drive のフォルダの共有・利用データ・Docker での渡し方・確かめ方を書いた
- `board/README.md` を人向けにした（画面の写真4枚・役割ごとに見えるもの・データの置き場の図と表・動かし方）。エージェント向けの節は `board/docs/internals.md` へ移し、`CLAUDE.md` の表の先に読むものをそこへ直した
- mgmt-kit の README の道具の表に board を足し、`ladder.md` を「board では定義の正本はアプリの設定で、`ladder.md` は初版の出どころ」と直した
- `board.env`・`secrets/`・`docker-compose.override.yml` を git の ignore の対象にした

## 保証
- 起動：何も設定せずに `docker compose up` でデモが起動する → `.github/workflows/docker.yml` の「Start with no settings」「Open a review through the demo login」
- 保存：コンテナを作り直しても設定が残る → `docker.yml` の「Settings survive recreating the container」（Ben Carter に Hiring を付け、`down`/`up` のあとも残る）
- ログイン：ドメインの人は初めてのログインで Member として載り、`BOARD_MANAGERS` の人は Manager になる → `tests/test_auth.py::test_first_google_login_adds_member_outside_demo`・`test_managers_env_makes_manager_and_never_demotes`。`test_google_login` の在籍者にいない人は 403 から 303 に変えた
- 維持：venv の起動とテストはそのまま通る。`config.py` の既存の環境変数の読み方は変えていない

## 静的確認結果
- `python -m pytest -q` が 195 passed（Playwright のある環境）
- `setup.md` に出る環境変数はすべて `app/config.py` が読む

- `.github/workflows/docker.yml` を足した。Dockerfile・compose・board の実装・board が読む入力が変わったとき、デモの起動と、コンテナを作り直しても DB が残ることを確かめる

## 起票時の合意から外れたこと（user 承認済み）
- ログインの変更に伴い、`対象` に無い `board/app/config.py`・`main.py`・`settings.py`・`tests/test_auth.py`・`board/docs/decisions.md` を変えた。`test_google_login` の在籍者にいない人の期待値を 403 から 303 にした
- `.gitignore` に `board/board.env`・`board/secrets/`・`board/docker-compose.override.yml` を足した
- 起動と保存の保証を固定するため、`対象` に無い `.github/workflows/docker.yml` を足した
- README の GIF は見送り、別の Issue（draft）に回した

## 検証手順
- `board/docs/setup.md` のとおり OAuth クライアント・サービスアカウント・`board.env`・`docker-compose.override.yml` を用意し、`cd board && docker compose up -d --build` を流す
- `BOARD_MANAGERS` に書いた本物の Workspace のアカウントでログインし、設定のタブが出ることと、右上に「Driveから … に読み込み」と出ることを見る

## 確認者の判定
| # | 項目 | 判定 |
|---|---|---|
| 1 | 何も設定せずに起動し、評価の1人のページまで開ける | 合 |
| 2 | 設定が `down`/`up` のあとも残る | 合 |
| 3 | setup.md の手順と環境変数が config.py と合う | 合 |
| 4 | 「動かす」が `docker compose up` から始まる | 合 |
| 5 | README の目的・画面・役割・置き場・起動・sheets.md（GIF は見送り） | 合 |
| 6 | CLAUDE.md の表が internals.md を指す | 合 |
| 7 | mgmt-kit の README の道具の表と ladder.md の位置づけ | 合 |
| 8 | `python -m pytest -q` が通る | 合 |
| 保証 | 起動・保存を固定するテストが無い | 否 → `docker.yml` を足して固定した |
| 保証 | Drive への切り替えを固定するテストが無い | 否（既存から無く、この PR では触れていない） |

## 手戻り
| 何が起きたか | 失ったもの | 原因の分類 | 仕組みで防げたか |
|---|---|---|---|
| デモでないと在籍者が0人で始まり、足す口も無く、本番では誰もログインできないことが作業中に分かった。user に聞いてこの Issue でログインの作りを変えた | 1回。20分 | Issue の切り方 | 防げた：起票時に「人が見るもの」の本番のログインを、デモでない起動で一度通しておけば |
| 確認者が、起動と保存の保証を固定するテストが無いとして「否」を出した。CI のジョブを足した | 1回。10分 | Issue の切り方 | 防げた：Issue の保証節が、Docker の保証をどのテストで固定するかを書いていれば |
| 校正役が「版」を「バージョン」に直し、decisions.md と画面の用語とずれたので戻した | 1回。2分 | 道具の欠け | 防げた：校正役に渡すときに、リポの用語集（版・細目など）を渡せる置き場があれば |

---

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
