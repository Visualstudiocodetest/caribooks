FROM ubuntu:22.04

# Avoid prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies for Python and Node
RUN apt-get update && apt-get install -y \
    curl \
    python3 \
    python3-pip \
    python3-venv \
    build-essential \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (v20)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Backend Setup ---
COPY backend/requirements.txt ./backend/
RUN python3 -m venv /app/venv \
    && /app/venv/bin/pip install --no-cache-dir -r backend/requirements.txt

# --- Frontend Setup ---
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm install

# --- Copy all project files ---
COPY . .

# Build frontend
RUN cd frontend && npm run build

# next.config.js sets output: 'standalone', which produces a self-contained
# server at .next/standalone/server.js with only the node_modules it actually
# needs -- but it does NOT include the static assets or public/ files (Next
# expects the deployer to copy those in). `npm start` (next start) is not
# compatible with this output mode at all -- it prints a warning and serves
# the app without them, so every hashed JS/CSS chunk 404s. Copy them into
# place at build time so the standalone server serves the exact same app the
# build produced.
RUN cd frontend \
    && cp -r .next/static .next/standalone/.next/static \
    && cp -r public .next/standalone/public

# Make startup script executable
# We create a simple wrapper to run both frontend and backend using the venv
# `localhost` inside a container means the container itself, never the Docker
# host -- so backend/.env's MYSQL_HOST=localhost (correct for the native
# startapp.sh workflow) would never reach a MySQL server on the host machine.
# Auto-correct it here so `docker run --env-file backend/.env caribooks` just
# works without the caller needing to remember a MYSQL_HOST override.
RUN echo '#!/bin/bash\n\
if [ "$MYSQL_HOST" = "localhost" ] || [ "$MYSQL_HOST" = "127.0.0.1" ] || [ -z "$MYSQL_HOST" ]; then\n\
  export MYSQL_HOST=host.docker.internal\n\
fi\n\
cd /app/backend\n\
/app/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 &\n\
cd /app/frontend\n\
PORT=3000 HOSTNAME=0.0.0.0 node .next/standalone/server.js\n\
' > /app/run.sh && chmod +x /app/run.sh

# Run as an unprivileged user: nothing after this point needs root, and a
# process compromised via a dependency/RCE bug is far more contained without
# it. Ownership is handed over after all build steps (which do need root to
# install system/npm/pip packages) have already written into /app.
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000 3000

CMD ["/app/run.sh"]
