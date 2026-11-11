# usage

| 保証 | 対応テスト |
|---|---|
| 評価のページで、B の細目のうち Evidence がスキルの回数のものに、利用データのスキルの回数と期間を添える | `test_skill_usage_only_on_b_items_counting_skills` |
| 利用データに無い人の評価にはスキルの回数を添えない | `test_no_skill_usage_without_usage_row` |
| 本人が自分の Approved の評価を見るときも、スキルの回数を添える | `test_member_sees_own_skill_usage_on_approved_review` |
| 利用データは最後の日から14日を集計する | `test_window_counts_back_from_the_last_day`、`test_days_before_the_window_are_left_out` |
| 利用データのメールは小文字にそろえて在籍者と突き合わせる | `test_window_counts_back_from_the_last_day` |
