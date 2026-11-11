# login

| 保証 | 対応テスト |
|---|---|
| ログインしていない人が画面を開くと、ログインの画面へ移す | `test_pages_require_login` |
| ログインしていない人が API を呼ぶと、401 を返す | `test_pages_require_login` |
| デモでは、在籍者を選ぶだけでログインできる | `test_demo_login_and_logout` |
| デモでは、Sign out でログアウトできる | `test_demo_login_and_logout` |
| デモのログインは、名簿に無い人を 403 で拒む | `test_demo_login_rejects_unknown_person` |
| デモでないときはデモのログインの入り口を閉じる | `test_demo_entrance_is_closed_outside_demo` |
| デモのログインの画面は在籍者ごとに役割・見えるタブ・担当する人を並べる | `test_demo_login_lists_people_with_roles_and_tabs`、`test_demo_login_lists_what_each_person_can_see` |
| Google のログインは検証に通らなかった人を 403 で拒む | `test_google_login` |
| Google のログインは ID トークンにドメイン（`hd`）の無い個人のアカウントを通さない | `test_verify_google_checks_workspace_domain` |
| Google のログインはメールが確かめられていないアカウントを通さない | `test_verify_google_checks_workspace_domain` |
| Google で初めて入った人は Member として在籍者に載る | `test_first_google_login_adds_member_outside_demo` |
| `BOARD_MANAGERS` に書いた人は入ったときに Manager になる | `test_managers_env_makes_manager_and_never_demotes` |
| Manager に上げた人は入り直しても Member に下がらない | `test_managers_env_makes_manager_and_never_demotes` |
| ログインの Cookie は改ざんしたものと期限を過ぎたものを受け付けない | `test_session_round_trip_and_tamper` |
