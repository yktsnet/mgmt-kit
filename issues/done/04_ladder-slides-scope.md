## PR記録: docs: Scope the ladder slides to the rating criteria and split the source of truth
issue: 04 (04_ladder-slides-scope.md)
PR: https://github.com/yktsnet/mgmt-kit/pull/51

## 変更内容
- `ladder/README.md` の冒頭に、board が無くても読める評価基準の説明であることと、board の README へのリンクを書いた
- 「ずれたら ladder.md を正とする」を消し、正本を中身で書き分けた。考え方（軸・段階の決め方・採点の原則）は ladder.md、判定文と判定に読むもの（Evidence）は board で回すときは board の設定で、ladder.md は初版の出どころになる
- `ladder/docs/ladder.md` の冒頭とルートの `README.md` の ladder.md の行を、同じ書き分けに揃えた（`対象` の外。user 承認済み）
- スライド（9枚目を含む）に board が無いと成り立たない書き方は無く、slides.html と PNG は変えていない。PNG の置き場は `scripts/render-slides.sh ladder` が書く `ladder/slides/` だった

## 保証
なし（文書だけの変更で、テストの対象を持たない）

## 確認者の判定
| # | 項目 | 判定 |
|---|---|---|
| 1 | 冒頭に board が無くても読めることと board の README へのリンク | 合 |
| 2 | 「ずれたら ladder.md を正とする」が無く、正本を書き分けている | 合 |
| 3 | 3つの README で正本の書き方が食い違わない | 合 |
| 4 | スライドに board が無いと成り立たない書き方が無い | 合 |
| 5 | `ladder/README.md` のパスが変わっていない | 合 |
| 6 | jp-proofreader にかけている | 判定できない（実行者のセッションで2回かけた。出力はブランチに残らない） |

## 手戻り
| 何が起きたか | 失ったもの | 原因の分類 | 仕組みで防げたか |
|---|---|---|---|
| 確認者が、ladder.md の冒頭の「このリポの正本である」と、Evidence の正本が書かれていないことを挙げた。user に聞いて範囲を広げて直した | 1回。5分 | Issue の切り方 | 防げた：起票時に「正本」を grep し、ladder.md も `対象` に入れていれば |

---

## ladder のスライドを評価基準の説明に絞り、正本の書き分けを直す
id: 04
branch-slug: ladder-slides-scope
status: close
depends: 03
type: cleanup
対象: ladder/README.md、ladder/docs/slides/（`render-slides.sh` が書く PNG。中身を直したときだけ）
目的: `ladder/README.md`（評価基準の説明スライド）を、board が無くても読める評価基準の説明資料にする。board で回したときに成り立たない「ずれたら ladder.md を正とする」を、正本の書き分けに直す。
内容: 冒頭に、評価基準の説明で board が無くても読めることと、回し方は board の README へつなぐ1行を書く。正本を、考え方（軸・段階の決め方・採点の原則）は `ladder.md`、運用で直していく判定文は board の設定と書き分ける。スライドの中身に board が無いと成り立たない書き方があれば直し、PNG を作り直す。
対象外: board で回す仕組みのスライドを足すこと。スライドへの画面の写真の掲載（画面は使いながら変わるので、写真は board の README にだけ置く）。ポートフォリオ側の変更
仮定:
- PNG の置き場は `scripts/render-slides.sh ladder` が書く先とし、実行者が確かめて対象を直す
- board の README の人向けの形は 03 で決まるので、そのあとに入る（`depends: 03`）
確認:
- `ladder/README.md` の冒頭に、board が無くても読めることと、board の README へのリンクがある
- 「ずれたら ladder.md を正とする」が無く、考え方は `ladder.md`、判定文は board の設定という書き分けがある
- `ladder/README.md`・mgmt-kit の README・board の README のあいだで、正本の書き方が食い違っていない
- 9枚目「型を配り、成果物と記録で判定する」を含め、スライドに board が無いと成り立たない書き方が無い。直したなら `scripts/render-slides.sh ladder` で PNG を作り直してコミットに含めている
- `ladder/README.md` のパスが変わっていない（ポートフォリオからのリンクを壊さない）
- 日本語の `.md` の変更を jp-proofreader にかけている。見出しを動かしたら md-reviewer にもかけている
人が見るもの: なし

---

### 保証
保証: なし（文書とスライドの画像だけの変更で、テストの対象を持たない）
