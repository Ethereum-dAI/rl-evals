FROM ghcr.io/foundry-rs/foundry:stable AS foundry

FROM python:3.12-slim
COPY --from=foundry /usr/local/bin/anvil /usr/local/bin/cast /usr/local/bin/
WORKDIR /chain
COPY node.py setup.json ./
EXPOSE 8545
CMD ["python", "-u", "node.py"]
