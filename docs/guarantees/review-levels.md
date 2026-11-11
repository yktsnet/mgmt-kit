# review-levels

| 保証 | 対応テスト |
|---|---|
| 軸の細目が L2〜L5 ですべて ○ なら、軸は L5 になる | `test_all_pass_reaches_l5` |
| ある段階に × があれば、軸はその1つ下の段階で止まり、上に空欄があっても変わらない | `test_fail_stops_below_even_with_blanks`、`test_fail_at_l2_is_l1` |
| 判定に空欄が残る段階に届くと、軸は未決定になる | `test_blank_cell_is_pending` |
| L2 に未観測があれば、軸は未観測になる | `test_unobserved_at_l2_is_unobserved_axis` |
| L3 以上に未観測があれば、軸はその1つ下の段階で止まる | `test_unobserved_above_l2_stops_there` |
| 本人の段階は A と B の低いほうになる | `test_person_level_is_lower_of_a_and_b` |
| A か B のどちらかが決まらなければ、本人の段階は決まらない | `test_person_level_is_lower_of_a_and_b` |
| 評価のシートのテンプレートは L2〜L5 の細目だけを並べる | `test_template_skips_l1` |
| 判定の `o` は ○ として読む | `test_parse_review_accepts_typed_variants` |
| シートのメールは小文字にそろえて読む | `test_parse_review_accepts_typed_variants` |
| シートの版は `v1` の形でも読む | `test_parse_review_accepts_typed_variants` |
| 判定が ○・×・未観測 のどれでもなければ、エラーにする | `test_bad_verdict_is_an_error` |
