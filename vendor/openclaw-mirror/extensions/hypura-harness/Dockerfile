FROM python:3.11-slim

# LoRA 学習用 GPU サポート (bitsandbytes は CUDA が必要)
# cuda base image ではなく slim を使い、必要な CUDA ライブラリのみ追加
# Note: lora-watcher と ai-scientist-lite はこの同じイメージを使う

WORKDIR /app

# システム依存ライブラリ
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python 依存関係
COPY scripts/pyproject.toml scripts/
RUN pip install --no-cache-dir uv && \
    cd scripts && uv pip install --system ".[lora]"

# アプリケーションコード
COPY scripts/ .
COPY config/ /app/config/

# デフォルト設定
ENV HARNESS_CONFIG=/app/config/harness.atlas.docker.json
ENV PYTHONUNBUFFERED=1

EXPOSE 18794

# デフォルトは harness デーモン (docker-compose で command を上書き可能)
CMD ["uvicorn", "harness_daemon:app", "--host", "0.0.0.0", "--port", "18794"]
