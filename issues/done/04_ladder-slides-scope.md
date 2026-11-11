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
