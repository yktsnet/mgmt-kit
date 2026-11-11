# 本番の設定

board を本物の Google につなぐ手順。ログインは Sign in with Google で、Drive のシートはサービスアカウントで読む。2つは別の資格情報で、片方だけでも動く。設定はどれも環境変数で渡し、読むのは `app/config.py` である。

## 1. ログイン（Sign in with Google）

Google Cloud のコンソールで、組織の Google Workspace に属するプロジェクトを選ぶ。

1. 「API とサービス」の「OAuth 同意画面」で、ユーザーの種類を「内部」にする
2. 「認証情報」で「OAuth クライアント ID」を作る。種類は「ウェブ アプリケーション」にする
3. 「承認済みの JavaScript 生成元」に、board を開く URL の生成元（例: `https://board.example.com`）を足す
4. 「承認済みのリダイレクト URI」に、生成元のあとに `/auth/google` を付けた URL を足す
5. 作ったクライアント ID を控える

| 環境変数 | 値 |
|---|---|
| `BOARD_GOOGLE_CLIENT_ID` | 5 で控えたクライアント ID |
| `BOARD_ALLOWED_DOMAIN` | 入れる Google Workspace のドメイン（例: `example.com`）。ID トークンの `hd` がこれと一致するアカウントだけを通す |
| `BOARD_MANAGERS` | Manager にする人のメール。複数ならカンマで区切る |
| `BOARD_SESSION_KEY` | ログインの Cookie に署名する鍵。長いランダムな文字列にする。空だと起動のたびに作り直し、全員のログインが切れる |

在籍者は0人で始まるので、最初の Manager は `BOARD_MANAGERS` で決める。誰が入れて、入った人がどう在籍者に載るかは [decisions.md](decisions.md) の「作り」にある。

デモでないときは、ログインの Cookie に Secure が付く。`localhost` 以外で開くなら、board の前に HTTPS を終端するリバースプロキシを置く。

## 2. Drive のシートを読む（サービスアカウント）

1. 同じプロジェクトで、Google Drive API と Google Sheets API を有効にする
2. 「IAM と管理」の「サービス アカウント」でサービスアカウントを作り、JSON の鍵を作ってダウンロードする
3. シートを置く Drive のフォルダを作り、サービスアカウントのメールに「閲覧者」で共有する。フォルダの中の形は [sheets.md](sheets.md) にある
4. フォルダの URL の末尾（`folders/` のあと）を、フォルダの ID として控える

| 環境変数 | 値 |
|---|---|
| `BOARD_SOURCE` | `drive` |
| `BOARD_DRIVE_FOLDER_ID` | 4 で控えたフォルダの ID |
| `BOARD_SERVICE_ACCOUNT_KEY` | 2 の JSON の鍵のパス |
| `BOARD_SYNC_INTERVAL` | 画面を開いたときに読み直すまでの秒数。省くと 60 |

`BOARD_SOURCE` が `drive` のときは、デモ用のログインとデモの在籍者を使わない。手元の `.xlsx` を読んだまま Google でログインしたいときは、`BOARD_DEMO=0` を足す。

## 3. Claude Code の利用データ

何も設定しなければ、リポに同梱したダミーの利用データを読む。本物のデータを読むには、`usage/` を取り込んだ管理用のリポジトリの `tools/usage/claude-code` を `BOARD_USAGE_DIR` に渡す。board はその中の `data/` と `github.json` と `render.py` を読み、`render.py` は1つ上の `chart.py` を読む。

## 4. Docker で起動する

`board/` に `board.env` を置き、1〜3 の環境変数を書く。`docker-compose.yml` は、このファイルがあれば読み込み、無ければデモで起動する。

```bash
BOARD_GOOGLE_CLIENT_ID=<クライアント ID>
BOARD_ALLOWED_DOMAIN=example.com
BOARD_MANAGERS=manager@example.com
BOARD_SESSION_KEY=<ランダムな文字列>
BOARD_SOURCE=drive
BOARD_DRIVE_FOLDER_ID=<フォルダの ID>
BOARD_SERVICE_ACCOUNT_KEY=/secrets/service-account.json
```

鍵と利用データは、`board/` に `docker-compose.override.yml` を置いてコンテナに渡す。`docker compose` はこのファイルを自動で重ねる。

```yaml
services:
  board:
    environment:
      BOARD_USAGE_DIR: /usage/claude-code
    volumes:
      - ./secrets:/secrets:ro
      - <管理用のリポジトリ>/tools/usage:/usage:ro
```

鍵は `board/secrets/service-account.json` に置く。`board.env`・`secrets/`・`docker-compose.override.yml` は git の ignore の対象で、コミットされない。

```bash
cd board
docker compose up -d --build
```

`docker-compose.yml` は `127.0.0.1:8000` で待ち受ける。外から開くときは、リバースプロキシをこのポートへつなぐ。

## 5. 確かめる

1. `BOARD_MANAGERS` に書いたアカウントでログインし、設定のタブが出ることを見る
2. ページの右上に「Driveから … に読み込み」と出て、読めなかったファイルの区画が出ていないことを見る
3. 評価のタブに、フォルダのシートの評価が並ぶことを見る
