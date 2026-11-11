# mgmt-kit

採用・育成・評価を、1つの評価基準で回す。3つを別々の制度にせず、同じものを読んで判断する。
読むのは、配った型を回すと出てくる標準化された成果物と、型を回した記録である。

- **軸を決める。** 何を測るかが決まると、標準化が何を揃えるべきかも決まる
- **型を配る。** 標準化された手順をチームで回すと、成果物の形が揃う
- **成果物が見える。** 揃った成果物は、書式の差ではなく中身の差として読める
- **評価ができる。** 読めるものがあって初めて、人がどの段階にいるかを判定できる
- **既存人材と候補者を同じ尺度で測れる。** 軸は共通で、替えるのは評価の材料だけになる

**この5つが繋がっていることに意味がある。** 評価軸だけを作ると、測る材料が出てこない。
標準化だけをやると、回っているかどうかを誰も判定できない。採用だけを別の基準で回すと、
入れた人を育てる段になって尺度が合わない。3つを別々の制度として持つと、
制度の間の食い違いを人が調整し続けることになる。

型を配る側は [sdlc-kit](https://github.com/yktsnet/sdlc-kit) が受け持つ。このリポは評価基準と、成果物と記録を読む2つの道具と、それらを1つの画面で回すアプリを持つ。

| 道具 | 答える問い | 読むもの | 置き場 |
|---|---|---|---|
| ladder | 1人がどの段階にいて、次にどの軸を上げるか | リポジトリの成果物 | `ladder/` |
| usage | 1人が配られた型を回し、仕事を進め、十分に使っているか | Claude Code の利用データ | `usage/` |
| board | 評価・育成・採用を同じ定義でどう回すか | 評価と面接のスプレッドシート、Claude Code の利用データ | [`board/`](board/README.md) |

## 評価で何を見るか

段階は ladder の判定文で決め、成果物を読んで確かめる。usage はそこへ3つの観点を足す。

- **標準化**：スキルの回数と名前で数えられる。評価の軸そのものが標準化を進める試みなので、B 軸（配られた型の運用）にそのまま使える
- **作業の量**：Issue・PR・commit・行数
- **投入の量**：まず絶対数を見て、足りていれば使い方の効率を見る

usage は GitHub で Issue と PR を中心に仕事を進め、Claude Code を使うチームを前提にしており、GitLab や別のエージェントで進めた仕事は評価できない。
3つがそろった姿と崩れ方ごとの打つ手、前提の理由は [あるべき姿](usage/tools/usage/claude-code/README.md#あるべき姿) にある。

候補者には利用データが無いので、usage は在籍者にだけ当てる。

## ladder：評価基準

| | 中身 |
|---|---|
| [ladder/docs/ladder.md](ladder/docs/ladder.md) | 5軸5段階と各セルの判定文、判定の材料にするもの。board では定義の正本はアプリの設定で、`ladder.md` は初版の出どころ |
| [ladder/docs/personas.md](ladder/docs/personas.md) | 各段階の参照ペルソナ。軸の凸凹を持たせた5人 |
| [ladder/docs/scoring.md](ladder/docs/scoring.md) | 在籍者を採点し、次に上げる軸を決めるまでの手順 |
| [ladder/docs/hiring.md](ladder/docs/hiring.md) | 同じ軸を候補者に当てる手順。評価の材料の替え方 |
| [ladder/docs/adapt.md](ladder/docs/adapt.md) | 自社へ持ち込むときの差し替え方 |
| [ladder/docs/ref/sources.md](ladder/docs/ref/sources.md) | 下敷きにした公開ラダーとライセンス |

評価基準の全体を図でつかむためのスライドを [ladder/README.md](ladder/README.md) に置いている。

### 軸が先に来る

標準化を先にやると、揃えるものが「書式」で止まる。何を測るかを決めてから型を配ると、
型は測りたいものが成果物に出る形になる。

**判定文と型の置き場が1対1で対応している。** 型に無い置き場を判定文が指していたら、
どちらかが間違っている。型を配る前にこの評価基準を当てると、判定文の大半が空欄になる。

### 採点を回す

`ladder/.claude/skills/ladder-score/` に、採点する skill が入っている。採点する相手の成果物が
あるリポジトリへ、`docs/` ごとコピーして使う。

```bash
git clone https://github.com/yktsnet/mgmt-kit.git
cp mgmt-kit/ladder/docs/{ladder,scoring,hiring,adapt}.md ~/repos/target/docs/
cp -r mgmt-kit/ladder/.claude/skills/ladder-score ~/repos/target/.claude/skills/
```

採点結果は、5軸の点・段階・次に上げる1軸である。**採点結果は既定でファイルに書かない**ので、
置き場と実名の扱いは、残すと決めた側が先に決める。

## usage：Claude Code の利用状況

Claude Code の利用データをメンバー別に毎日並べる。組織の GitHub Actions の分数も数える。

サンプルは [Claude Code の利用状況](usage/tools/usage/claude-code/README.md) と [Actions の分数](usage/tools/usage/github-actions/README.md) にある。
どちらも架空の10人と8リポのダミーデータから作った。あるべき姿の人と、崩れ方の型ごとの人が入っている。
`scripts/sample-usage.py` がダミーデータを作り、続けて各集計の `render.py` で表とグラフを作り直す。

### 取り込む

`usage/` は取り込み先の配置を写した形になっている。集計を置く管理用のリポジトリへコピーし、サンプルのデータと名簿を消す。

```bash
cp -R mgmt-kit/usage/. <管理用のリポジトリ>/
cd <管理用のリポジトリ>/tools/usage
rm -rf claude-code/{data,members,charts} github-actions/{data,charts} claude-code/github.json
```

そのあとはコピーした `tools/usage/README.md` の「導入の手順」に従い、「組織に合わせて替える値」を直す。

## 勉強会：実務で型を回せない人の育成

[training/](training/README.md) に、客先常駐の社員向けAI勉強会の提案資料を置いている。評価の中での位置づけは [scoring.md の「育成に使うとき」](ladder/docs/scoring.md#育成に使うとき) にある。

## License

MIT
