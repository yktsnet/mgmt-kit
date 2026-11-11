# board

ladder の5軸で、評価・育成・採用を1つのウェブアプリで回す。画面・役割・Docker での起動は [トップの README](../README.md) にある。ここには board を直す人向けのことだけを置く。

## Docker を使わずに動かす

Python 3.12 で venv に入れて起動する。

```bash
cd board
python -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/uvicorn app.main:create_app --factory --port 8000
```

## 文書

| 文書 | 中身 |
|---|---|
| [docs/internals.md](docs/internals.md) | どこに何があり、直すときに何を守るか |
| [docs/decisions.md](docs/decisions.md) | board の方針と、そう決めた理由 |
| [docs/sheets.md](docs/sheets.md) | 評価・候補者・面接のシートの形。テンプレートは `templates/` にある |
| [docs/setup.md](docs/setup.md) | 本物の Google のアカウントでログインし、Drive のシートを読むまでの手順 |
