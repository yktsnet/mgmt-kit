# settings

## 設定の画面と設定を変えられる人

| 保証 | 対応テスト |
|---|---|
| 設定の画面は定義の細目、Reviewer の割り当て、採用枠を出す | `test_settings_shows_definition_assignments_and_requisitions` |
| Manager は在籍者の役割と Reviewer を設定できる | `test_role_and_reviewer_change`、`test_people_rules` |
| 設定の画面と設定の API は Manager のほかには 403 になる | `test_settings_is_manager_only`、`test_settings_api_is_manager_only` |

## 定義の版

| 保証 | 対応テスト |
|---|---|
| 評価か面接が使った版の細目は直せない | `test_version_used_by_reviews_is_locked_until_new_version`、`test_version_used_by_a_review_is_locked`、`test_version_used_by_candidates_is_locked` |
| New version で次の版を作ると、その版は直せる | `test_version_used_by_reviews_is_locked_until_new_version`、`test_version_used_by_a_review_is_locked` |
| 新しい版を直しても、前の版は変わらない | `test_version_used_by_reviews_is_locked_until_new_version`、`test_version_used_by_a_review_is_locked` |

## 定義の細目

| 保証 | 対応テスト |
|---|---|
| 細目は直せる | `test_save_add_and_delete_items` |
| 細目は足せる | `test_save_add_and_delete_items` |
| 細目は消せる | `test_save_add_and_delete_items` |
| 足した細目には次の記号を振る | `test_save_add_and_delete_items` |
| マスの最後の細目は消せない | `test_last_item_of_a_cell_cannot_be_deleted` |
| 細目の無いマスがある定義はエラーにする | `test_cell_without_items_is_an_error` |

## 在籍者と採用枠の値

| 保証 | 対応テスト |
|---|---|
| 自分を自分の Reviewer にはできない | `test_role_and_reviewer_change`、`test_people_rules` |
| 役割は manager と member のほかを受け付けない | `test_people_rules` |
| 採用枠の人数を保存できる | `test_requisition_rules` |
| 採用枠の求める高さに、段階を超える値を受け付けない | `test_requisition_rules` |

## 初版の定義

| 保証 | 対応テスト |
|---|---|
| 初版の定義は `ladder.md` から作る | `test_ladder_md_covers_every_cell` |
| 初版の定義は25マスすべてに細目がある | `test_ladder_md_covers_every_cell` |
| `ladder.md` の判定文は句点ごとに細目に分ける | `test_split_statement_by_period` |
| デモでないときは在籍者0人と `ladder.md` の v1 の定義で始まる | `test_seed_builds_v1_from_ladder_md_once` |
| 起動をくり返しても、初版の定義は増えない | `test_seed_builds_v1_from_ladder_md_once` |
