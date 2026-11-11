## PR記録: feat: Even out board screens at three widths and show skill counts on B evidence
issue: 02 (02_screens-at-three-widths.md)
PR: https://github.com/yktsnet/mgmt-kit/pull/49

## 変更内容
- `board.css` の共通の部品を3つの幅で揃えた。本文の幅の上限を `--page` に置き、2200px 以上では 1920px・16px にする。評価の一覧の表は区画の幅に広げ、列の割合を揃えた
- 現在地の図の SVG が持つ `.muted` の 11px が同じ文書の表の `td.muted` に当たり、理由の列が小さくなっていたのを打ち消した。図の小さい文字は 12px で描き、幅の上限を 1200px にした
- 760px 以下では、表を区画の中で横に送り行の高さを揃え、図は縮めずに区画の中で横に送り、2つの図を縦に並べる。Items は段階ごとに軸を縦に積む（`data-axis` で軸の名前を出す）。デモのログインは1人を1枚に積む
- 採用の一覧は、狭い画面で「面接・届いていない・次に聞く」を畳み、名前・選考の段階・軸の段階を残す（Crit で案Aに決めた）
- 評価の1人のページで、Evidence に「スキル」と「回数」を含む B の細目（初版では L2 と L4）の根拠の欄に、usage のスキルの回数と期間を出す。期間と数え方は現在地の「使い方」の表と同じ（`usage_report.skills`）

## 保証
- 画面：評価・現在地・採用・デモのログインは 1440・2560・390px で横スクロールが出ない → `tests/test_app.py::test_no_horizontal_scroll`（Playwright と chromium のある環境で動き、無ければ飛ばす）。ほかに `test_wide_screen_stops_at_max_width_with_even_margins`・`test_narrow_now_stacks_charts_with_readable_text`・`test_narrow_hiring_keeps_name_stage_and_axes_visible`・`test_narrow_items_wrap_within_screen`
- 評価：B の細目に限り usage のスキルの回数と期間が出る → `tests/test_reviews_page.py::test_skill_usage_only_on_b_items_counting_skills`・`test_no_skill_usage_without_usage_row`・`test_member_sees_own_skill_usage_on_approved_review`
- 画面の中身 → `test_reviews_roster_rows`・`test_now_sections_for_manager`・`test_now_for_member_without_reviewees`・`test_hiring_page_lists_candidates_per_requisition`・`test_demo_login_lists_people_with_roles_and_tabs`
- 維持：見せる範囲・平均の出し方・段階の決め方は変えていない（既存のテストがすべて通る）

## 静的確認結果
- Playwright のある環境で `python -m pytest -q` が 193 passed。無い環境で 163 passed, 30 skipped
- git diff --name-only --cached:
  board/app/main.py
  board/app/static/board.css
  board/app/templates/candidate.html
  board/app/templates/hiring.html
  board/app/templates/review.html
  board/app/usage_report.py
  board/app/views.py
  board/tests/test_app.py
  board/tests/test_hiring.py
  board/tests/test_now.py
  board/tests/test_reviews_page.py


## 起票時の合意から外れたこと（user 承認済み）
- B の根拠のスキルの回数の期間は、Issue の「usage の最後の日から14日」ではなく、現在地の「使い方」の表と同じ期間にした。そのため `対象` に無い `board/app/main.py` と `board/app/usage_report.py` を変えた
- 3つの幅のテスト（30件）は Playwright と chromium が要り、CI では飛ぶ。CI に入れるのは見送った

## 確認者の判定
| # | 項目 | 判定 |
|---|---|---|
| 1 | 評価の一覧と1人のページに横スクロールが出ない | 合 |
| 2 | 現在地（Manager・担当の無い Member）と1人の推移に横スクロールが出ない | 合 |
| 3 | 採用の一覧と候補者のページに横スクロールが出ない | 合 |
| 4 | デモのログインに横スクロールが出ない | 合 |
| 5 | 2560px で本文が上限で止まり、余白が均等 | 合 |
| 6 | 390px で現在地の図が縦に並び、文字が12px 以上 | 合 |
| 7 | 390px で採用の一覧の名前・段階・軸が切れない | 合 |
| 8 | 390px で Items の文と根拠が折り返す | 合 |
| 9 | B の L2・L4 だけにスキルの回数と期間が出る | 合 |
| 10 | usage に行が無いときは出さない | 合 |
| 11 | Member が自分の Approved の評価で自分の数字だけを見る | 合 |
| 12 | 画面の中身を確かめるテストがある | 合 |
| 13 | `python -m pytest -q` が通る | 合 |

## 手戻り
| 何が起きたか | 失ったもの | 原因の分類 | 仕組みで防げたか |
|---|---|---|---|
| Issue の B の根拠の期間（14日）が、現在地の実際の期間と食い違っていた。user に聞き直した | 1回。5分 | Issue の切り方 | 防げた：起票時に現在地の期間を `usage_report.team` の出力で確かめていれば |
| 現在地の Member の行のテストで、Approved 前の自分の段階が見える前提の期待値を書いて落ちた | 1回。2分 | 実装者の不注意 | 防げない |

---

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
