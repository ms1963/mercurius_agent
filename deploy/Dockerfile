FROM node:22-bookworm-slim

# Install system runtime dependencies for polyglot tools (Python 3, GCC/G++, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    g++ \
    gcc \
    bash \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy package descriptors
COPY package.json tsconfig.json mercury.config.json ./

# Install npm dependencies (tsx for seamless ts execution)
RUN npm install -g tsx && npm install --omit=dev

# Copy source tree and web assets
COPY src/ ./src/
COPY web/ ./web/
COPY bin/ ./bin/
COPY data/ ./data/

# Expose Web Console port and MCP RPC port
EXPOSE 4100
EXPOSE 4101

# Volumes for durable storage & memory
VOLUME ["/app/data"]

CMD ["tsx", "src/index.ts", "server"]
