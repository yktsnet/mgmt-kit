## usage を運用側の新しい版に揃え、使われなくなった ladder の採点結果・参照ペルソナ・seat を外す
id: 01
branch-slug: usage-and-cleanup
status: close
type: feat
対象: usage/tools/usage/claude-code/render.py、usage/tools/usage/claude-code/README.md、usage/tools/usage/claude-code/members/*.md、usage/tools/usage/claude-code/charts/*、usage/tools/usage/claude-code/docs/seats.md（削除）、usage/tools/usage/claude-code/docs/metrics.md、usage/tools/usage/claude-code/seats.json（削除）、scripts/sample-usage.py、board/app/usage.py、board/app/usage_report.py、board/app/templates/now.html、board/app/templates/now_member.html、board/app/ladder.py（削除）、board/app/main.py、board/app/config.py、board/app/store.py、board/samples/ladder/（削除）、board/scripts/make_samples.py、board/tests/test_ladder.py（削除）、board/tests/test_usage.py、board/tests/test_now.py、board/README.md
目的: mgmt-kit の usage を運用している版と同じ表と数え方にし、board の現在地のタブがその表と同じ列で並ぶようにする。あわせて、どの画面も読まなくなった ladder の採点結果・参照ペルソナと、mgmt-kit では使わない seat の判定を外し、board と usage を直す担当が使われていないものに迷わないようにする。
内容: 取り込み元 `~/github-corp/management/tools/usage/claude-code/render.py` の表（「量と成果」「使い方」）と CLI だけの利用時間の数え方（`cli_time_only`）を持ち込む。mgmt-kit にだけある全員の平均と、board が呼ぶ `period` は残す。seat の節と判定、良い使い方の節は持ち込まない。ダミーから MD を作り直し、現在地の列を新しい表に合わせる。board からは `sync_ladder` と、それが書く `staff`・`scores`・`personas` の表、ダミーの採点結果を外す。
対象外: 取り込み元（運用側）のコードの変更。名簿とデータの持ち込み。`collect.py`（mgmt-kit の版は環境変数を必須にした汎用の形で、取り込み元より新しい）。`ladder/docs/personas.md` と ladder の skill（board の外の持ち物）。画面の幅の見直しと B の根拠（02）
仮定:
- 取り込むのは `render.py` だけで、`collect.py` は mgmt-kit の版を残す（差分は環境変数の扱いだけで、CLI だけの利用時間の数え方は `render.py` 側にある）
- 取り込み元の `usage_table` が詳しい記録の無い人の行を出さない決まりは、そのまま持ち込む
- 採用枠の「参照ペルソナ」は設定で枠に書いた文字を出すだけで、`personas` の表を読まない（#36 の記述と `hiring.py` の現状から置いた）
確認:
- `grep -rni "seat" usage board scripts` が何も返さず、`seats.json` と `docs/seats.md` が無い
- `render.py` に `cli_time_only` があり、`active_by_type` に `cli` を持つ日は、利用時間が `cli` の秒数だけで数えられる（テストで確かめる）
- `render.py` に `period`・`average`・`team_average`・`average_cells` が残り、3人に満たないとき平均を出さない（既存のテストが通る）
- `python scripts/sample-usage.py` で作り直した README.md の表が「量と成果」「使い方」の2つで、seat と良い使い方の節が無い
- 作り直した README.md の「量と成果」「使い方」の各行の値と、デモの現在地のタブ（Manager でログイン）の同じ人・同じ列の値が一致する。突き合わせはテストで行う
- 現在地のタブの2つの表の列が、README.md の同じ名前の表と同じ並びになる
- `grep -rnE "sync_ladder|parse_personas|parse_scoresheet|samples/ladder|BOARD_PERSONAS|FROM staff|FROM scores|FROM personas" board` が何も返さない
- 前の形の DB（`staff`・`scores`・`personas` がある）を開いても起動でき、開いたあとにその3つの表が無い
- デモで起動し、評価・現在地・採用・設定の各画面が 200 で開く
- `cd board && python -m pytest -q` が通る
人が見るもの: なし

---

### 保証
- 新たに宣言する保証:
  - usage：利用時間は、CLI の操作時間が記録されている日はそれだけで数える
  - 現在地：「量と成果」「使い方」の表は、usage の README.md の同じ名前の表と同じ列・同じ値になる
  - 保存：前の形の DB を開くと、使われなくなった `staff`・`scores`・`personas` の表が消える
- 維持する保証:
  - 現在地の図と表に、全員の1人あたりの平均が出る。図の線は5日平均で、3人に満たないときは平均を出さない
  - Member には自分の行だけが出て、平均は全員から出す
  - usage の JSON を読み、MD は読まない。ログインと同じメールで突き合わせる
  - 評価・採用・設定の画面と API の振る舞い（既存のテストがすべて通る）
- 廃止する保証:
  - usage の README.md が seat の節と要る seat の数を出す（`render.py` の seat の判定と、それを確かめるテストを消す）
  - ladder の採点結果（`samples/ladder/*.md`）と `ladder/docs/personas.md` を読み、`staff`・`scores`・`personas` に入れる（`test_ladder.py` を消す）

### usage/tools/usage/claude-code/render.py
取り込み元を下敷きにし、mgmt-kit にだけある関数（`SMOOTH_DAYS`・`AVERAGE_MIN`・`TOP_SKILLS`・`average`・`team_average`・`average_cells`・`period`）を残して作り直す。いまの `standard_table`・`work_table`・`input_table` は、新しい `amount_table`・`usage_table` に置き換わる。`main` から seat と良い使い方の節を書く部分を外す。

### board/app/usage_report.py・usage.py・templates/now*.html
表の行は `render.py` の新しい表と同じ数え方（`cli_time_only` を通した利用時間を含む）で組む。「使い方」の列は新しい `usage_table` に合わせる（いまの board にある「よく使ったスキル」の列は、取り込み元の表に無ければ外す）。`usage.py` の「seat を決めるときと同じ幅」のコメントは、seat を外したあとの理由に書き直す。

### scripts/sample-usage.py
人ごとの seat を外す。作り直した `README.md`・`members/`・`charts/` をコミットに含める。

### board/app/store.py・main.py・config.py
`scores`・`staff`・`personas` の `CREATE TABLE` を外し、前の形の DB を今の形にする手当てに `DROP TABLE IF EXISTS` を足す。`scores` から `origin = 'interview'` を消す行（184行目付近）は要らなくなる。`main.py` 54行目付近の `sync_ladder` の呼び出しと、`Config` の `personas`（と、ほかに読む所が無ければ `ladder_dir`）を外す。`ladder_md` は定義の初版に使うので残す。

### board/tests/test_usage.py
`test_repo_sample_joins_with_ladder_staff` は `staff` の表で突き合わせている。デモの在籍者（`app/demo.py`）とリポの usage のダミーのメールが10人とも一致することを確かめる形に書き換える。

### board/scripts/make_samples.py
`scoresheet` と `samples/ladder/` を書く部分を外す。面接のシートを作る部分は残す。作り直したあと `samples/drive/` に差分が出ないこと。

### board/README.md
データの流れの図から「ladder の採点結果」を外し、モジュールの表から `app/ladder.py` の行を外す。
