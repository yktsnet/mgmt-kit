# sync

## 読み直すファイルの選び方

| 保証 | 対応テスト |
|---|---|
| シートは更新日時が変わったファイルだけを読み直す | `test_only_changed_files_are_read`、`test_nothing_read_when_unchanged`、`test_sync_rereads_only_when_modified_time_changes` |
| ファイルを消すと、その候補者と面接を消す | `test_removed_file_drops_candidate_and_interviews` |
| 同じメールのファイルが2つあれば、新しいほうを読む | `test_duplicate_email_keeps_newer_file` |
| 同じメールの新しいほうのファイルを消すと、古いほうを読む | `test_duplicate_email_keeps_newer_file` |
| 置き場の決まりの外のファイルとロックファイルは読まずにエラーにもしない | `test_files_outside_layout_are_ignored` |

## 読み込みの結果

| 保証 | 対応テスト |
|---|---|
| 読めないファイルはエラーとして報告する | `test_bad_file_is_reported_and_others_still_load` |
| 読めないファイルがあっても、ほかのファイルは読む | `test_bad_file_is_reported_and_others_still_load` |
| 直したファイルは読み直す | `test_fixed_file_is_read_again` |
| 直したファイルのエラーは消す | `test_fixed_file_is_read_again` |
| 読めなかったファイルを、画面に区画として出す | `test_bad_file_is_shown_as_section_on_screen` |
| 画面の右上に、どこからいつ読み込んだかを出す | `test_screen_shows_source_and_load_time` |

## シートの中身の読み方

| 保証 | 対応テスト |
|---|---|
| シートは列や行の順ではなく見出しの文字で読む | `test_headers_are_read_by_label_not_position` |
| 面接は「面接」のシートに行が無くても、「面接N」のシートから読む | `test_interview_sheet_without_row_in_list_is_still_read` |
| 判定の無い「面接N」のシートは面接として数えない | `test_empty_interview_sheet_is_not_an_interview` |
| 版の無い候補者のシートはエラーにする | `test_candidate_needs_version` |
| シートに書いた選考の段階は読まない | `test_stage_in_sheet_is_not_read` |
| 日付は Excel の日付・「2026/03/02」の形・Sheets の通し番号のどれでも読む | `test_to_date` |

## Drive と Sheets

| 保証 | 対応テスト |
|---|---|
| Drive ではサブフォルダとページ送りをたどる | `test_lists_spreadsheets_in_subfolders_across_pages` |
| Drive ではスプレッドシートだけを読む | `test_lists_spreadsheets_in_subfolders_across_pages` |
| Sheets から読んだ候補者は手元の `.xlsx` と同じ形で読む | `test_reads_grid_into_candidate` |
