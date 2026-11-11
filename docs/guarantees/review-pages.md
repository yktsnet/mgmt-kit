# review-pages

## 評価の一覧

| 保証 | 対応テスト |
|---|---|
| 評価の一覧は Reviewer ごとに分ける | `test_reviews_grouped_by_reviewer_with_status` |
| 評価の一覧は Reviewer ごとに人数と Submitted・Approved の数を出す | `test_reviews_grouped_by_reviewer_with_status` |
| 評価の一覧の行は状態・軸ごとの段階・本人の段階を出す | `test_reviews_roster_rows` |
| 評価の一覧の行は、判定が途中なら判定の済んだ数と総数を出す | `test_reviews_roster_rows` |
| 評価の一覧はその人が見られる人だけを並べる | `test_review_list_is_narrowed` |
| 「Reviewer 未割り当て」の区画は Manager にだけ出す | `test_unassigned_group_only_for_manager` |

## 評価の1人のページ

| 保証 | 対応テスト |
|---|---|
| 評価の1人のページは Reviewer・本人の段階・細目ごとの判定と根拠を出す | `test_review_detail_shows_levels_and_verdicts` |
| 評価の1人のページは、シートを最後に編集した日時と人を出す | `test_review_page_shows_sheet_modified_time_and_editor` |
| 評価の1人のページは、評価がどの版で付いたかを出す | `test_review_page_shows_ladder_version` |
| シートがまだ無い人の評価のページは「評価のシートがまだ無い」と出す | `test_not_started_has_no_sheet` |
| 在籍者でない人の評価のページは 404 になる | `test_not_started_has_no_sheet` |

## 評価の1人のページを開ける人

| 保証 | 対応テスト |
|---|---|
| Manager はすべての人の評価のページを開ける | `test_review_page` |
| Reviewer は担当する人の評価のページを開ける | `test_review_page` |
| 担当外の人の評価のページは Manager のほかには 403 になる | `test_review_page` |
| 本人は自分の評価のページを Approved になるまで開けない | `test_review_page` |
| Approved の評価が Reopen されると、本人は再び開けなくなる | `test_reopened_review_is_hidden_from_self_again` |
| 本人が自分の評価を見るとき、記録は出さない | `test_own_review_is_visible_once_approved_without_records` |

## 評価のタブとトップの送り先

| 保証 | 対応テスト |
|---|---|
| 見られる評価が無い人には評価の一覧が 403 になる | `test_review_tab_is_hidden_when_nothing_to_see` |
| 見られる評価が無い人には評価のタブを出さない | `test_review_tab_is_hidden_when_nothing_to_see` |
| トップは、評価を見られる人を評価の一覧へ送る | `test_home_goes_to_reviews`、`test_review_tab_is_hidden_when_nothing_to_see` |
| トップは、評価を見られない人を現在地へ送る | `test_review_tab_is_hidden_when_nothing_to_see` |
