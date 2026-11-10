# mgmt-kit

採用・育成・評価を1つの評価基準で回すためのリポジトリ。何があるかは `README.md` にある。

| 置き場 | 先に読むもの |
|---|---|
| `ladder/` | `ladder/docs/ladder.md` |
| `usage/` | `usage/tools/usage/claude-code/README.md` |
| `board/` | `board/README.md` |

## 作業の進め方

- 作業は Issue から始め、ブランチと PR を経由する。PR の件名は英語、本文は日本語で書く
- board の方針は `board/docs/decisions.md` にある。方針を変えるときは、そこを書き換えてから進める
- 画面に出る変更は、先に画面を作って Crit で見てもらい、形が決まってから画面のテストを書く。画面に出ない部分は先にテストを書いてよい
- board のテストの回し方は `board/README.md` にある。PR の本文に通った件数を書く
- 文書は日本語の、である調で書く。コードのコメントは日本語で、WHY が非自明なときだけ書く
