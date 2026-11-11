# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app/board
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# board はリポの ladder.md（定義の初版）と usage の集計を、リポの中の位置で読む。
# ビルドの文脈は board/ なので、リポのほかの部分は追加の文脈 repo から写す
COPY --from=repo ladder/docs/ladder.md /app/ladder/docs/ladder.md
COPY --from=repo usage/tools/usage /app/usage/tools/usage
COPY . .

# 設定・評価の状態・選考の段階・記録は SQLite にある。コンテナを作り直しても残るよう volume に置く
ENV BOARD_DB=/data/board.db
VOLUME /data
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
