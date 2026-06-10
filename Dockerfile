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

# Make startup script executable
# We create a simple wrapper to run both frontend and backend using the venv
RUN echo '#!/bin/bash\n\
cd /app/backend\n\
/app/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 &\n\
cd /app/frontend\n\
npm start -- -p 3000\n\
' > /app/run.sh && chmod +x /app/run.sh

EXPOSE 8000 3000

CMD ["/app/run.sh"]
