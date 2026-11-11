# review-status

## 評価の状態

| 保証 | 対応テスト |
|---|---|
| Reviewer は判定のそろった評価を Submit できる | `test_reviewer_submits_and_manager_approves` |
| 判定が途中の評価は Submit できず、API は 400 を返す | `test_submit_needs_complete_verdicts`、`test_submit_refused_while_in_progress` |
| Submitted の評価を Approve できるのは Manager だけである | `test_reviewer_submits_and_manager_approves`、`test_reviewer_cannot_approve` |
| Manager は Approved の評価を Reopen で Draft に戻せる | `test_reviewer_submits_and_manager_approves` |
| 担当でも Manager でもない人が評価の状態を変えようとすると、403 で拒む | `test_others_cannot_act`、`test_action_api_refuses_people_who_cannot_see` |
| 状態の切り替えは誰がしたかとともに記録に新しい順で残る | `test_reviewer_submits_and_manager_approves` |
| 状態の切り替えの記録に日時を残す | `test_state_change_and_memo_are_recorded_with_time` |
| Submit した評価は、評価の一覧で状態が Submitted と出る | `test_submit_and_memo_show_in_record` |

## 記録へのメモ

| 保証 | 対応テスト |
|---|---|
| 記録へのメモは Manager と担当の Reviewer だけが書け、本人は書けない | `test_memo_api` |
| メモは記録に足していく | `test_memo_is_appended_and_empty_is_refused` |
| メモの記録に日時を残す | `test_state_change_and_memo_are_recorded_with_time` |
| 空白だけのメモは受け付けない | `test_memo_is_appended_and_empty_is_refused` |
| メモは評価のページの記録に出る | `test_submit_and_memo_show_in_record` |
