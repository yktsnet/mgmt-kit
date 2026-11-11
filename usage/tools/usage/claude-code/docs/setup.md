# 集め方と設定

利用状況の数値をどこから集め、表とグラフをどう作り直しているかを書く。運用する人向けである。表の見方は
[README.md](../README.md) にある。

## 何が集まるか

Owner が claude.ai の管理画面（Managed settings）から全員の Claude Code に送信設定を配り、
各自の Claude Code が数値と操作の記録（ログ）を New Relic へ送る。送信はバックグラウンドで行われ、
Claude Code の応答を待たせない。プロンプトと応答の本文は送らない。

ログには、ツールを使った記録（実行したコマンドやファイルのパス）も含まれる。スキルの記録だけを送る設定は
無いので、ログの保存期間を3日に短くしている（下の「ログの保存期間」）。

ターミナル・VS Code 拡張・デスクトップアプリの Code タブ・ブラウザ版（claude.ai/code）の分が
集まる。ブラウザ版は、クラウド環境のネットワーク許可リストに New Relic の送信先が入っている
必要がある。デスクトップアプリの Cowork の分は、Owner の設定が届かないので集まらない。

同じ人が Team 以外のアカウントで使った分は入らない。

Issue の数だけは GitHub から取る。組織の全リポの Issue を検索し、立てた人の GitHub アカウント別に数える。

## データの流れ

```
各メンバーの Claude Code ──(数値を送る)──▶ New Relic
                                              │
GitHub Actions（定時）◀──(前日分を取る)──────────────┘
  ├─ GitHub の検索から、Issue の数が無い日の分を取る
  └─ tools/usage/claude-code/data/<日付>.json に保存し、グラフと表を作り直してコミットする
```

| ファイル | 中身 |
|---|---|
| `collect.py` | New Relic から日本時間の1日単位でメンバー別に取り出し、`data/` に置く |
| `render.py` | `data/` から `charts/` のグラフ、`README.md` の表、`members/` の個人のページを作り直す |
| `data/` | 日ごとの集計。1日1ファイル |
| `members/` | 個人のページ。直近28日に記録のある人の分だけを置く |
| `github.json` | 表の名前（メールアドレスの @ より前）と GitHub アカウントの対応表。人の出入りのたびに直す |

New Relic の無料枠はデータを8日しか残さない。`collect.py` は直近7日の平日のうち `data/` に無い日を
取りに行くので、数日止まっても次の実行で埋まる。8日を超えて止まると、その日は戻らない。
Issue の数は GitHub に残るので、8日を超えて止まっても次の実行で埋まる。

### 送信設定（Managed settings）

リポジトリに置く Secret・Variable と、ワークフローの動き方は、[tools/usage/README.md](../../README.md) の
「必要な設定」「仕組み」にある。

Owner が Managed settings に貼る送信設定は次の形である。キーは New Relic の INGEST - LICENSE の
キーで、`NRAL` で終わる。メンバーの手元の設定から見えるが、送信にしか使えない。

```json
{
  "env": {
    "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
    "OTEL_METRICS_EXPORTER": "otlp",
    "OTEL_LOGS_EXPORTER": "otlp",
    "OTEL_LOG_TOOL_DETAILS": "1",
    "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
    "OTEL_EXPORTER_OTLP_ENDPOINT": "https://otlp.nr-data.net",
    "OTEL_EXPORTER_OTLP_HEADERS": "api-key=<INGEST - LICENSE のキー>",
    "OTEL_METRICS_INCLUDE_SESSION_ID": "false",
    "OTEL_METRICS_INCLUDE_ENTRYPOINT": "true"
  }
}
```

`OTEL_LOGS_EXPORTER` はスキルを使った回数を、`OTEL_LOG_TOOL_DETAILS` は自作のスキルの名前を記録に
残す。`OTEL_LOG_TOOL_DETAILS` が無いと、自作のスキルはどれも `custom_skill` と記録される。
`OTEL_METRICS_INCLUDE_ENTRYPOINT` は、どこから使ったか（ターミナル・VS Code など）を記録に残す。
個人のページの「使った場所」はこの記録から作る。

### ログの保存期間

New Relic の Administration → Data Retention で、Logging の保存期間を3日にしている。変更が
反映されるまで最大24時間かかるので、送信設定でログを送り始める前に設定する。

New Relic の無料枠では、届いたログの一部だけを捨てる設定（drop rule）を使えない。代わりに
保存期間を短くして、コマンドやパスを含むログが残る期間を限っている。

`collect.py` はスキルの回数を前日分のログから取る。Actions が2日以上止まると、その間のスキルの
回数は戻らない。

## まだ取っていないもの

今後取るかどうかを決める候補を置く。

| 候補 | 見えるようになること | 取るのに要るもの |
|---|---|---|
| マージされた PR の数（GitHub から） | 取り込まれた仕事の量。マージされた PR 1件あたりの費用 | `ORG_READ_TOKEN` の token に Pull requests の Read-only を足し、`collect.py` で取る。PR を出さない仕事は成果ゼロに見える |
| リクエストごとの文脈の量（`api_request` イベント） | 長いセッションの肥大を直接測れる | 送信設定でログを送るように変え、配り直す。送る量が桁違いに増え、New Relic の無料枠を超えるかもしれない |
| 7日間の利用上限の使用率 | 利用上限にどれだけ近いか。プランを見直す判断に使える | 記録（OTel）には無く、全員分を自動で集める手段が無い。claude.ai の管理画面に出ていれば取り込める |
| セッション ID | 1セッションあたりのトークンと時間 | 送信設定の `OTEL_METRICS_INCLUDE_SESSION_ID` を `true` にして配り直す |
| セッションの再開の割合（`session.count` の `start_type`） | 新規・再開・続きの比率。古い会話を続けていないか | `collect.py` で取るだけで済む |
| MCP サーバー別の費用 | 使われていない MCP サーバーに費用がかかっていないか | `collect.py` で取るだけで済む |
| 任せている度合い（Claude Code が処理していた時間 ÷ 人が操作していた時間） | まとまった仕事を任せているか | 人が操作していた時間は、ターミナルは記録するが、VS Code 拡張は記録しない。VS Code 拡張を使う人が多いあいだは出せない。使う場所が変わったら出せるよう、`data/` には時間の種類別の記録を残している |
| 30日以内の書き直し（churn） | Claude Code が書いたコードが、すぐに書き直されていないか | GitHub の履歴から計算する仕組み |
