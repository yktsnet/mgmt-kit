# hiring

| 保証 | 対応テスト |
|---|---|
| 候補者の選考は「応募」から始まる | `test_stage_starts_at_first_and_moves_forward` |
| 選考の段階は1つずつ進め、飛ばせない | `test_cannot_skip_stages` |
| 段階を変えると、誰がしたかとともに記録に残る | `test_stage_starts_at_first_and_moves_forward` |
| 不採用にした候補者は直前の段階に戻せる | `test_closed_candidate_can_be_reopened_to_previous_stage` |
| 内定の候補者は入社か辞退にだけ進められる | `test_offer_cannot_be_rejected_and_joined_is_final` |
| 入社した候補者の段階はそれ以上動かせない | `test_offer_cannot_be_rejected_and_joined_is_final` |
| 候補者の軸の段階は細目ごとに最も新しい面接の判定を採り、評価と同じ決め方で出す | `test_latest_interview_wins_per_item` |
| 面接で聞いていない軸は未決定、未観測と書いた軸は未観測として分ける | `test_axis_not_asked_is_pending_and_unobserved_is_none` |
| 採用の一覧は採用枠ごとに求める高さと候補者の軸の段階を並べる | `test_hiring_page_lists_candidates_per_requisition` |
| 求める高さに届いていない軸を「届いていない」に、未決定の軸を「次に聞く」に出す | `test_openings_compare_target_and_count_stages` |
| 採用枠ごとに、選考の段階ごとの人数を数える | `test_openings_compare_target_and_count_stages` |
| 設定に無い採用枠の候補者は最後の区画にまとめて出す | `test_candidate_requisition_missing_from_settings_is_listed_apart` |
| 採用のページと採用の操作は Manager と Hiring を付けた人のほかには 403 になる | `test_hiring_pages` |
| 設定で Hiring を付けた人は採用を開ける | `test_hiring_flag_is_set_in_settings` |
| 採用のタブは採用を見られる人にだけ出す | `test_hiring_tab_shows_only_for_those_who_can_see` |
