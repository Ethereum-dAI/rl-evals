FROM ghcr.io/foundry-rs/foundry:stable AS foundry

FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl jq python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*
COPY --from=foundry /usr/local/bin/cast /usr/local/bin/
WORKDIR /app
