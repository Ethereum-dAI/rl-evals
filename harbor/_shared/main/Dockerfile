FROM ghcr.io/foundry-rs/foundry:stable AS foundry

FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl jq python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*
COPY --from=foundry /usr/local/bin/cast /usr/local/bin/
# Python tooling for ABI work and RPC calls, on PATH as the default python3.
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir \
    web3 eth-abi eth-account eth-utils hexbytes requests
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app
