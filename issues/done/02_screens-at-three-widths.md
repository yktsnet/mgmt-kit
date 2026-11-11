## board の画面を3つの幅で見直して作りを揃え、評価の B の根拠にスキルの回数を添える
id: 02
branch-slug: screens-at-three-widths
status: close
depends: 01
type: feat
対象: board/app/static/board.css、board/app/templates/base.html、board/app/templates/reviews.html、board/app/templates/review.html、board/app/templates/_level.html、board/app/templates/now.html、board/app/templates/now_member.html、board/app/templates/hiring.html、board/app/templates/candidate.html、board/app/templates/login.html、board/app/views.py、board/tests/test_reviews_page.py、board/tests/test_now.py、board/tests/test_hiring.py、board/tests/test_app.py
目的: Crit の「全体スクショ取ってほしい。極端で変」（#26）に応え、どの画面も同じ区画・表・見出しの作りで、1440px・2560px・390px のどれでも余白・幅・文字の大きさが極端に偏らないようにする。あわせて、評価の1人のページで B の根拠に usage の数字を並べる（decisions.md の「Claude Code の利用状況」）。
内容: `board.css` の共通の部品（`.wrap`・`.frame`・`.head`・`.report`・`.scroll`・見出し）を3つの幅で破綻しない形に揃え、評価・現在地・採用・デモのログインの全体を3つの幅で撮って直す。1人のページの Items で、Evidence がスキルの使用回数を指す B の細目に限り、根拠の欄に usage の数字を添える。形が決まったら画面の中身を確かめるテストを書く。
対象外: usage の表の列と数え方（01）。選考の段階の進め方と見せる範囲（#39 で決めた）。Sign in with Google の経路。自作のスキルが「ほかのメンバーに使われた回数」の集計（usage の JSON にスキルの作り手が無い）
仮定:
- 「Evidence がスキルの使用回数のもの」は、定義の版の Evidence に「スキル」と「回数」を含む細目とする。いまの初版では B の L2 と L4 が当たる。L4 にも、その人が期間内に使ったスキルの回数を添える
- 添える数字は現在地と同じ期間（usage の最後の日から14日）のスキルの合計で、期間も一緒に出す
- 390px で採用の一覧の表をどう収めるか（列を絞るか、行を縦に積むか）は、実行者が案を撮って Crit で選んでもらう
確認:
- 評価の一覧と1人のページは、1440px・2560px・390px のどれでも横スクロールが出ない（`document.documentElement.scrollWidth <= innerWidth`）
- 現在地（Manager と、担当の無い Member）と1人の推移のページは、3つの幅のどれでも横スクロールが出ない
- 採用の一覧と候補者のページ（Manager）は、3つの幅のどれでも横スクロールが出ない
- デモのログインは、3つの幅のどれでも横スクロールが出ない
- 2560px で本文の幅が上限で止まり、左右の余白が均等になる
- 390px で、現在地の2つの図が縦に並び、図の文字が12px 以上で出る
- 390px で、採用の一覧の各候補者の名前・選考の段階・軸の段階が切れずに読める
- 390px で、評価と候補者のページの Items の細目の文と根拠が画面の幅で折り返し、切れない
- 評価の1人のページで、B の L2 と L4 の細目の根拠の欄に、その人のスキルの回数と期間が出る。ほかの細目には出ない
- usage にその人の行が無いとき、B の根拠の欄に数字を出さず、ほかの表示は変わらない
- Member が自分の Approved の評価を開いたときも、自分の数字だけが出る
- 評価・現在地・採用・ログインの各画面で、見出し・区画・表の行が期待どおりに出ることを確かめるテストがある（要素の有無だけでなく中身まで）
- `cd board && python -m pytest -q` が通る
人が見るもの: 4つの画面の3つの幅の全体の画面写真を Crit で見てもらい、OK をもらう

---

### 保証
- 新たに宣言する保証:
  - 画面：評価・現在地・採用・デモのログインは、1440px・2560px・390px のどれでも横スクロールが出ない
  - 評価：1人のページで、Evidence がスキルの使用回数を指す B の細目に限り、根拠の欄にその人の usage のスキルの回数と期間が出る
- 維持する保証:
  - 見せる範囲（`test_access.py`）。Member は担当する人の評価と Approved の自分の評価だけを見られ、自分の評価の記録は見られない。採用は Hiring を付けた人と Manager だけが見られる
  - 現在地で Member には自分の行だけが出て、平均は全員から出す（3人に満たないときは出さない）
  - 段階の決め方（`review.axis_result`）と評価の状態の切り替え。聞かなかった細目と未観測の書き分け

### board/app/static/board.css・base.html
共通の部品を先に直す。`.wrap` の `max-width: 1680px` は 2560px で左右の余白が偏る原因の候補。390px では `.top .inner` のタブ・`.pagehead`・`.frame > .head` の折り返しを見る。

### board/app/views.py・review.html
Items の行に usage の数字を持たせる。数字は `usage` の表（`board/app/usage.py` が作る）から引き、見せる範囲は `access.py` の決まりに従う。

### 実装順序
1. 共通の部品を直し、4つの画面を3つの幅で撮って直す（screen-operator）
2. B の根拠を足す
3. Crit で OK をもらってから、画面の中身のテストを書く
