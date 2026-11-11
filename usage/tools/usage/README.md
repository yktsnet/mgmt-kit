# 利用状況の集計

組織の利用状況と費用を、データ源ごとに集めて表とグラフにする。

| 集計 | 答える問い | データ源 |
|---|---|---|
| [Claude Code の利用状況](claude-code/README.md) | メンバーが Claude Code をどう使い、どれだけ成果を出しているか | New Relic と GitHub の Issue |
| [GitHub Actions の分数](github-actions/README.md) | 今月の Actions の分数が、無料枠と予算に届きそうか | 組織の各リポジトリの実行記録 |

## 仕組み

`.github/workflows/usage.yml` の1つのジョブが、火曜から土曜の 1:00 JST に、集計ごとの `collect.py` と
`render.py` を順に動かし、変わった分をコミットする。1つの集計が失敗しても、ほかの集計の反映とコミットは続ける。

グラフの配色と SVG の部品は `chart.py` にあり、どの集計の `render.py` もこれを使う。

## 必要な設定

リポジトリの **Settings → Secrets and variables → Actions** に置く。

| 名前 | 種類 | 使う集計 | 中身 |
|---|---|---|---|
| `NEW_RELIC_USER_KEY` | Secret | Claude Code | New Relic の User key（`NRAK-` で始まる）。データを読むのに使う |
| `NEW_RELIC_ACCOUNT_ID` | Variable | Claude Code | New Relic のアカウント ID。New Relic は保存用のアカウントも自動で作るので、どちらを読むかを指定する |
| `EMAIL_DOMAIN` | Variable | Claude Code | Claude の Team のアカウントのメールアドレスのドメイン（`example.com` など）。ほかのアカウントで試した分を数えないために絞る |
| `GITHUB_ORG` | Variable | Claude Code、GitHub Actions | GitHub の組織の名前 |
| `ORG_READ_TOKEN` | Secret | Claude Code、GitHub Actions | 組織の全リポジトリを読める fine-grained token。作り方は下の「token を作る」にある |

## 導入の手順

組織の Owner にしかできない作業がある。上から順に進める。

1. **New Relic を用意する**（集計を運用する人）：アカウントを作り、データを読む User key と、送信に使う INGEST - LICENSE のキーを出す。ログの保存期間を先に3日へ短くする。理由と設定の場所は [claude-code/docs/setup.md](claude-code/docs/setup.md#ログの保存期間) にある
2. **token を作る**（Owner）：下の「token を作る」のとおりに作り、`ORG_READ_TOKEN` に置く
3. **メンバーに知らせる**（Owner）：集めることを承認し、メンバー全員に伝える。送信設定を配ると、各メンバーが次に Claude Code を起動したときに承認を求める画面が1回出る。説明より先にこの画面が出ないよう、配る前に知らせる
4. **送信設定を配る**（Owner）：claude.ai の **Organization settings → Claude Code → Managed settings** に送信設定を貼って保存する。中身は [claude-code/docs/setup.md](claude-code/docs/setup.md#送信設定managed-settings) にある。送信用のキーを含むので、Issue やチャットに貼らずに Owner へ直接渡す
5. **名簿を書く**（集計を運用する人）：`claude-code/github.json` に各メンバーの GitHub アカウントを書く。対応表の役割は [claude-code/docs/setup.md](claude-code/docs/setup.md#データの流れ) にある

メンバーへの知らせには、次の4点を入れる。

- 集めるのはトークン量・利用時間・会話の数・commit の数などの数値と、スキルやツールを使った記録である
- プロンプトと応答の本文は送らない
- ツールを使った記録には実行したコマンドやファイルのパスが入るが、New Relic に3日だけ残って消える
- 設定を配ったあとに Claude Code を起動すると承認を求める画面が1回出るので、承認する

### token を作る

token は作った人に見えるリポジトリしか読めない。組織の全リポジトリが見える Owner のアカウントで作る。

自分のアカウントの **Settings → Developer settings → Personal access tokens → Fine-grained tokens** で作る。
組織の設定画面には作る場所が無い。

- **Resource owner**：組織
- **Repository access**：All repositories
- **Repository permissions**：Issues と Actions を Read-only（Metadata の Read-only は自動で付く）
- **有効期限**：選べる最長。切れると、Issue の数と Actions の分数が集まらなくなる

組織が fine-grained token に承認を求める設定なら、**Organization settings → Personal access tokens → Pending requests** で承認する。
権限は作った本人にしか変えられない。権限を足しても token の値は変わらないので、Secret を置き直す必要は無い。

## 組織に合わせて替える値

| 値 | 置き場 | 既定の値と根拠 |
|---|---|---|
| Actions の無料枠と予算の段 | `github-actions/render.py` の `FREE_MINUTES`・`TIERS_USD` | [github-actions/docs/metrics.md](github-actions/docs/metrics.md#見込みと段) の「見込みと段」 |
| 1日の区切りと定時実行の時刻 | 各 `collect.py` の `JST`、`.github/workflows/usage.yml` の `cron` | 日本時間 |

データの受け先は New Relic を実装例にしている。Claude Code は OpenTelemetry の形式で送るので、
送信設定の送信先を替えれば別の受け先にも送れる。そのときは `claude-code/collect.py` のうち、New Relic に
問い合わせる部分（`nerdgraph`・`query_day` と、NRQL で書いた `METRICS`・`BREAKDOWNS`）を替える。
