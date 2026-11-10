# Claude Code の利用状況

組織のメンバーの Claude Code の利用状況を、メンバー別に毎日集めて並べる。使い方の支援と
seat の配分に使う。

このページは全員を並べて比べる。1人ずつの毎日の推移は、表の名前から開く `members/<名前>.md` にある。
どちらも定時に作り直す。時刻は [tools/usage/README.md](../README.md#仕組み) の「仕組み」にある。

<!-- report:start -->
最終更新：2026-04-24 分まで

図と表はどれも 2026-03-30 〜 2026-04-24 の平日の分で、期間のトークン量の多い順に並べる。
図の破線は全員の1人あたりの5日平均（直前5平日の移動平均）、表の「平均」は全員の1人あたりの平均である。どちらも3人に満たないときは出さない。

### 標準化されたやり方

配られたスキルを回しているか。名前を押すと、スキルごとの回数と割合が個人のページに出る。

| メンバー | スキルの回数 | よく使ったスキル |
|---|--:|---|
| [ben-carter](members/ben-carter.md) | 3回 | `issue-draft` 67%、`issue-work` 33% |
| [alice-walker](members/alice-walker.md) | 50回 | `issue-work` 38%、`issue-draft` 14%、`api-scaffold` 14% |
| [henry-ward](members/henry-ward.md) | 9回 | `issue-work` 56%、`md-writing` 22%、`grasp` 11% |
| [emma-hughes](members/emma-hughes.md) | 35回 | `issue-work` 31%、`issue-draft` 17%、`rework-review` 17% |
| [chloe-evans](members/chloe-evans.md) | 2回 | `rework-review` 50%、`guarantee-audit` 50% |
| [felix-grant](members/felix-grant.md) | 0回 | - |
| [daniel-brooks](members/daniel-brooks.md) | 23回 | `issue-work` 57%、`api-scaffold` 17%、`daily-report` 13% |
| [grace-turner](members/grace-turner.md) | 26回 | `issue-work` 35%、`rework-review` 27%、`jp-writing` 12% |
| [isla-morgan](members/isla-morgan.md) | 13回 | `issue-work` 38%、`rework-review` 15%、`md-writing` 15% |
| [jack-foster](members/jack-foster.md) | 0回 | - |
| **平均** | 16.1回 | - |

### 作業の量

どれも期間の合計である。

![メンバー別の日ごとの commit](charts/team-commits.svg)

| メンバー | commit | PR | 追加した行 | 削除した行 | 立てた Issue | 閉じた Issue |
|---|--:|--:|--:|--:|--:|--:|
| ben-carter | 269 | 3 | 22305 | 3058 | 0 | 0 |
| alice-walker | 291 | 137 | 29228 | 3618 | 92 | 66 |
| henry-ward | 152 | 14 | 16319 | 1688 | - | - |
| emma-hughes | 86 | 31 | 8085 | 939 | 28 | 26 |
| chloe-evans | 75 | 7 | 7589 | 1121 | 11 | 15 |
| felix-grant | 66 | 6 | 5347 | 660 | 0 | 0 |
| daniel-brooks | 75 | 17 | 8315 | 932 | 18 | 16 |
| grace-turner | 29 | 15 | 2929 | 298 | 35 | 29 |
| isla-morgan | 7 | 5 | 657 | 98 | 18 | 26 |
| jack-foster | 7 | 0 | 812 | 79 | 0 | 0 |
| **平均** | 105.7 | 23.5 | 10158.6 | 1249.1 | 22.4 | 19.8 |

### 投入の量

使う量と、使い方の列を並べる。

![メンバー別の日ごとのトークン量](charts/team-daily.svg)

| メンバー | 利用時間 | トークン量 | 1会話あたりのトークン量 | サブエージェントに任せた割合 | Effort | モデル |
|---|--:|--:|--:|--:|---|---|
| ben-carter | 1367分 | 7361.1M | 10.8M | 15% | 1（high） | 1（opus 5.5） |
| alice-walker | 1372分 | 7208.2M | 9.6M | 35% | 4（low, medium, high, xhigh） | 2（opus 5.5, sonnet 5.5） |
| henry-ward | 808分 | 4251.8M | 11.9M | 30% | 2（medium, high） | 2（opus 5.5, sonnet 5.5） |
| emma-hughes | 537分 | 2886M | 8M | 30% | 3（low, medium, high） | 2（opus 5.5, sonnet 5.5） |
| chloe-evans | 435分 | 2505.3M | 52.2M | 15% | 1（high） | 1（opus 5.5） |
| felix-grant | 468分 | 2492.2M | 29M | 8% | 1（medium） | 1（opus 5.5） |
| daniel-brooks | 452分 | 2363.7M | 9.3M | 25% | 2（medium, high） | 2（haiku 4.5, opus 5.5） |
| grace-turner | 122分 | 648.6M | 4.6M | 20% | 2（medium, high） | 2（opus 5.5, sonnet 5.5） |
| isla-morgan | 51分 | 282.7M | 3.2M | 15% | 2（low, medium） | 1（sonnet 5.5） |
| jack-foster | 25分 | 121.7M | 5.8M | 29% | 1（medium） | 1（opus 5.5） |
| **平均** | 564分 | 3012.1M | 10.8M | 25% | - | - |

### seat

直近2週（2026-04-11 〜 2026-04-24、土日を含む）を7日ずつに分け、割合の高い方の週で決める。

| メンバー | いまの seat | Premium の上限に対する割合 | Standard の上限に対する割合 | 要る seat |
|---|---|--:|--:|---|
| ben-carter | Premium | 81% | 405% | Premium |
| alice-walker | Premium | 95% | 473% | Premium |
| henry-ward | Premium | 43% | 213% | Premium |
| emma-hughes | Premium | 29% | 146% | Review |
| chloe-evans | Premium | 30% | 150% | Review |
| felix-grant | Premium | 28% | 138% | Review |
| daniel-brooks | Premium | 22% | 111% | Review |
| grace-turner | Standard | 9% | 45% | Standard |
| isla-morgan | Standard | 3% | 15% | Standard |
| jack-foster | Standard | 1% | 7% | 要らない |
| kate-hill | Premium | - | - | 記録が届いているかを確かめる |

要る seat の数：Premium 3・Standard 2・Review 4・決められない 1（いまの名簿は Premium 8・Standard 3）

Premium の上限は Standard の 5 倍である。Standard の上限の2倍以内（100% を超え 200% 以下）の人は Review としている。
<!-- report:end -->

## あるべき姿

次の3つがそろっている人が、あるべき姿である。

この見方は、GitHub で Issue と PR を中心に仕事を進め、エージェントに Claude Code を使うことを前提にしている。
利用データは Claude Code の送信設定から、Issue の数は GitHub の検索から集めるので、GitLab などほかの置き場で
進める仕事や、別のエージェントで進めた仕事は表に出ない。そうした人は、この表で評価しない。

### 1. 標準化：配られたやり方で仕事をしている

スキルを毎日使っていて、使ったスキルの名前に配布したフローのスキル（Issue を立てる、次の作業を選ぶ、
作業を進める）が並んでいる。スキルをほとんど使っていない人は、Claude Code を使っていても型の外で仕事をしている。
足りない手順を自分でスキルにした人は、そのスキルの名前がほかのメンバーのページにも出る。

見るところ：標準化されたやり方の表と、個人のページの「スキル」

### 2. 作業の量：その仕事が、型どおりの形で出てきている

作業を Issue にして、PR を出し、Issue を閉じている。commit が多いのに PR が少ない人は、変更が PR の流れに
乗っていない。Issue を立てない人は Issue 駆動の型に乗っておらず、立てても閉じない人は作業を型の中で終えていない。

見るところ：作業の量の表

### 3. 投入の量：まず十分に使い、そのうえで使い方を作業に合わせている

最初に、平日は毎日、仕事の中心として使っている。使う量が少ない人は、型を回す以前の段階にいる。
量が足りている人について、使い方を見る。

- 1つの会話を長く続けず、作業ごとに区切っている。作業が変わるときは `/clear`（それまでの会話を消す）し、長い作業の途中は `/compact`（会話を要約して縮める）している
- 作業に合わせて Effort とモデルを切り替えている
- 調べ物やテストはサブエージェントに任せている
- 使った量に見合った作業が出ている

見るところ：投入の量の表と、個人のページの「毎日の推移」

### 崩れ方と打つ手

| 崩れ方 | 出方 | 打つ手 |
|---|---|---|
| 量は多いが型に乗っていない | たくさん使って commit も多いが、スキル・PR・Issue が少ない | 使う量ではなく、やり方を型に乗せる |
| 型に乗っているが量が少ない | スキルも Issue も回っているが、使う時間が短い | 型はできているので、使う量を増やす |
| どちらも少ない | スキルも作業も投入も少ない | まず毎日使うところから始める |

## 文書

| 文書 | 中身 |
|---|---|
| [docs/metrics.md](docs/metrics.md) | 各項目が何を数え、何を数えないか |
| [docs/seats.md](docs/seats.md) | seat の判定の規則、上限の置き方、名簿の書き方 |
| [docs/setup.md](docs/setup.md) | 何が集まるか、データの流れ、送信設定、まだ取っていないもの |
