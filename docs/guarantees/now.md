# now

## 現在地のページ

| 保証 | 対応テスト |
|---|---|
| 現在地は「次に上げる1軸」「日ごとのトークン量」「日ごとの commit」「量と成果」「使い方」の順に並べる | `test_now_sections_for_manager`、`test_page_shows_md_equivalent_charts_and_tables` |
| B が L1 のまま L2 に届かない人がいると、その人数と名前を出す | `test_page_shows_md_equivalent_charts_and_tables` |
| 「量と成果」「使い方」の表は usage の README の表と同じ見出しと値を出す | `test_now_tables_match_usage_readme`、`test_now_for_member_without_reviewees` |

## 次に上げる軸

| 保証 | 対応テスト |
|---|---|
| 次に上げる軸の既定は、決まっている軸のうち最も低いものになる | `test_next_axis_is_lowest_decided_axis` |
| 次に上げる軸の既定は、最も低い軸が複数あれば A に近いほうを採る | `test_next_axis_is_lowest_decided_axis` |
| 次に上げる軸をまだ決めていなければ、決める人の名前に「（未決定）」を添える | `test_page_shows_md_equivalent_charts_and_tables` |
| 評価がまだ無い人の次に上げる軸は「評価が出てから」と出す | `test_now_for_member_without_reviewees` |
| 次に上げる軸を決めると、現在地に出る | `test_reviewer_sets_next_axis_and_it_is_recorded` |
| 次に上げる軸を決めると、評価の記録に残る | `test_reviewer_sets_next_axis_and_it_is_recorded` |
| 担当の Reviewer と Manager のほかが次に上げる軸を決めようとすると、400 で拒む | `test_growth_api_refuses_member_who_does_not_review`、`test_others_cannot_set_next_axis` |

## 全員の平均

| 保証 | 対応テスト |
|---|---|
| 図と表に、全員の1人あたりの平均を並べる | `test_charts_and_tables_show_team_average` |
| Member にも全員の平均を出す | `test_member_sees_average_of_everyone_but_only_own_lines` |
| 平均の線は直前5日の移動平均にする | `test_average_is_smoothed_and_needs_three_people` |
| 平均は3人以上のときだけ出す | `test_average_is_smoothed_and_needs_three_people` |
| 在籍者が2人以下のとき、画面に平均を出さない | `test_no_average_on_screen_with_two_people` |

## 1人の現在地のページ

| 保証 | 対応テスト |
|---|---|
| 1人の現在地のページは評価へのリンクと日ごとの図を出す | `test_member_page_links_review_and_shows_trend` |
| 在籍者でない人の1人の現在地のページは 404 になる | `test_member_page_links_review_and_shows_trend` |
| 1人の現在地のページは本人・Manager・担当の Reviewer のほかには 403 になる | `test_now_member_page` |

## 役割ごとに見せる範囲

| 保証 | 対応テスト |
|---|---|
| Member にはほかの人の線と行を出さない | `test_member_sees_average_of_everyone_but_only_own_lines` |
| 現在地の行は Manager には全員、Reviewer には自分と担当する人、Member には自分だけを出す | `test_now_rows_are_narrowed` |
| Member の現在地には、自分の1人のページへのリンクだけを出す | `test_usage_tables_on_now_are_narrowed` |
| 現在地から自分の評価へのリンクは Approved になってから出す | `test_own_level_on_now_waits_for_approval` |
| 担当も Hiring も無い Member には現在地のタブだけを出す | `test_plain_member_sees_only_now_tab` |
