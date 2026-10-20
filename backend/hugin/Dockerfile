FROM debian:bookworm-slim
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y hugin-tools enblend && rm -rf /var/lib/apt/lists/*
WORKDIR /work
