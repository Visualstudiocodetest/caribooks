# Deployment Guide — Oracle Cloud Free Tier (2× AMD VM + Load Balancer + MySQL HeatWave) + Vercel

> **Stack:** Next.js (Vercel) · FastAPI (2× Oracle AMD Micro VM) · OCI Flexible Load Balancer · MySQL HeatWave (Oracle Free)
> **Cost:** $0/month permanently · No cold starts · Zero-downtime deployments · HA with failover

---

## Architecture Overview

```
Internet
    │
    ▼
┌─────────────────────────────┐
│   Vercel (Next.js Frontend) │  CDN worldwide
│   Auto-deploy on git push   │
└─────────────────────────────┘
    │ API calls (HTTPS)
    ▼
┌─────────────────────────────┐
│  OCI Flexible Load Balancer │  Always Free — port 80/443
│  Health checks every 10s    │  SSL termination via Let's Encrypt
└────────────┬────────────────┘
             │
      ┌──────┴──────┐
      ▼             ▼
┌──────────┐  ┌──────────┐
│  VM 1    │  │  VM 2    │  2× AMD Micro (1/8 OCPU, 1 GB RAM)
│ FastAPI  │  │ FastAPI  │  Ubuntu 22.04 · Uvicorn · Nginx
│ :8000    │  │ :8000    │  Same Oracle VCN (private network)
└──────────┘  └──────────┘
      │             │
      └──────┬──────┘
             ▼
┌─────────────────────────────┐
│  MySQL HeatWave Free Node   │  Managed MySQL · 50 GB · Always Free
│  Private subnet (no NAT)    │  Internal OCI network only
└─────────────────────────────┘
```

---

## Prerequisites

- Oracle Cloud account (credit card required for verification, never charged)
- GitHub account with Student Developer Pack (GitHub Pro — 3,000 Actions min/month)
- Vercel account (free, no credit card)
- Domain name (optional — Cloudflare free DNS recommended)

---

## Part 1 — Oracle Cloud Setup

### 1.1 Create the Virtual Cloud Network (VCN)

1. Go to **Networking → Virtual Cloud Networks → Create VCN**
2. Name: `ecommerce-vcn`
3. CIDR block: `10.0.0.0/16`
4. Check **Use DNS Hostnames**
5. Click **Create VCN**

Then add two subnets:

| Subnet | CIDR | Type | Purpose |
|--------|------|------|---------|
| `public-subnet` | `10.0.0.0/24` | Public | VMs + Load Balancer |
| `private-subnet` | `10.0.1.0/24` | Private | MySQL HeatWave |

### 1.2 Configure Security Lists

For **public-subnet**, add ingress rules:

| Protocol | Port | Source | Purpose |
|----------|------|--------|---------|
| TCP | 22 | `0.0.0.0/0` | SSH access |
| TCP | 80 | `0.0.0.0/0` | HTTP |
| TCP | 443 | `0.0.0.0/0` | HTTPS |
| TCP | 8000 | `10.0.0.0/16` | FastAPI (internal only) |

For **private-subnet**, add ingress rules:

| Protocol | Port | Source | Purpose |
|----------|------|--------|---------|
| TCP | 3306 | `10.0.0.0/24` | MySQL from VMs only |

### 1.3 Create the 2 AMD Micro VMs

Go to **Compute → Instances → Create Instance** and repeat **twice**:

- **Image:** Ubuntu 22.04 Minimal
- **Shape:** VM.Standard.E2.1.Micro (Always Free)
- **OCPU:** 1/8 (shared) · **RAM:** 1 GB
- **Subnet:** public-subnet
- **Assign public IP:** Yes
- **SSH key:** Upload your public key

Name them `fastapi-vm1` and `fastapi-vm2`.

Note both **Public IPs** and both **Private IPs** (10.0.0.x) after creation.

### 1.4 Create MySQL HeatWave Free Node

Go to **Databases → MySQL HeatWave → DB Systems → Create**:

- **Name:** `ecommerce-mysql`
- **Shape:** MySQL.Free (Always Free)
- **Admin user:** `admin`
- **Admin password:** (choose a strong password)
- **Subnet:** private-subnet (NOT public)
- **Availability:** Standalone (free tier)

> ⚠️ Note the **Private Endpoint IP** (e.g. `10.0.1.10`) — this is the only address your VMs will use to connect to MySQL.

### 1.5 Create the Flexible Load Balancer

Go to **Networking → Load Balancers → Create Load Balancer**:

- **Name:** `fastapi-lb`
- **Visibility:** Public
- **Bandwidth:** 10 Mbps (Always Free)
- **Subnet:** public-subnet

**Backend Set configuration:**
- Policy: Round Robin
- Health Check: HTTP · Port 8000 · Path `/health` · Interval 10s · Timeout 3s

**Backends (add both VMs):**
- `10.0.0.X:8000` (VM1 private IP)
- `10.0.0.Y:8000` (VM2 private IP)

**Listener:**
- Port 80 · HTTP → forward to backend set

Note the **Load Balancer Public IP** — this is your API endpoint.

---

## Part 2 — FastAPI Setup on Both VMs

> Run these commands on **both VM1 and VM2** via SSH.

### 2.1 Initial Server Setup

```bash
# Connect to VM
ssh ubuntu@<VM_PUBLIC_IP>

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip git nginx

# Create app directory and user
sudo useradd -m -s /bin/bash appuser
sudo mkdir -p /app
sudo chown appuser:appuser /app
```

### 2.2 Clone and Configure the App

```bash
sudo su - appuser
git clone https://github.com/<YOUR_USERNAME>/<YOUR_REPO>.git /app
cd /app

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
### 2.3 Environment Variables

```bash
# Create /app/.env
cat <<EOF > /app/.env
DATABASE_URL=mysql+pymysql://admin:<PASSWORD>@10.0.1.10:3306/ecommerce
SECRET_KEY=<YOUR_SECRET_KEY>
ENVIRONMENT=production
EOF
chmod 600 /app/.env
```
### 2.3 Environment Variables

```bash
# Create /app/.env
cat <<EOF > /app/.env
DATABASE_URL=mysql+pymysql://admin:<PASSWORD>@10.0.1.10:3306/ecommerce
SECRET_KEY=<YOUR_SECRET_KEY>
ENVIRONMENT=production
EOF
chmod 600 /app/.env
```

### 2.4 FastAPI App Structure

Your FastAPI app must include a `/health` endpoint for the load balancer health check:

```python
# main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init DB connection pool
    yield
    # Shutdown: close pool

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Your routes
@app.get("/api/products")
async def get_products():
    ...
```

### 2.5 Systemd Service

```bash
# Exit appuser, back to ubuntu
exit

sudo nano /etc/systemd/system/fastapi.service
```

```ini
[Unit]
Description=FastAPI E-commerce Backend
After=network.target

[Service]
User=appuser
WorkingDirectory=/app
EnvironmentFile=/app/.env
ExecStart=/app/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable fastapi
sudo systemctl start fastapi
sudo systemctl status fastapi
```

### 2.6 Nginx Reverse Proxy

```bash
sudo nano /etc/nginx/sites-available/fastapi
```

```nginx
server {
    listen 8000;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 60s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
```

> **Note:** The Load Balancer talks directly to port 8000 on the VMs' private IPs. Nginx here acts as a proxy with logging and headers, while Uvicorn binds to `127.0.0.1:8000` locally.

```bash
sudo ln -s /etc/nginx/sites-available/fastapi /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Part 3 — Vercel Frontend (Next.js)

### 3.1 Connect GitHub to Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New Project**
2. Import your GitHub repository
3. Framework: **Next.js** (auto-detected)
4. Root directory: `frontend/` (or root if monorepo)

### 3.2 Environment Variables in Vercel

In **Project Settings → Environment Variables**, add:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_BACKEND_BASE_URL` | `http://<LOAD_BALANCER_IP>` |

### 3.3 Automatic Deployments

Every push to `main` → Vercel auto-deploys the frontend. No GitHub Actions needed for the frontend — Vercel's GitHub integration handles it natively.

---

## Part 4 — CI/CD GitHub Actions (Zero-Downtime Rolling Deploy)

### 4.1 GitHub Secrets to Configure

Go to your repo **Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|--------|-------|
| `VM1_PUBLIC_IP` | VM1 public IP |
| `VM2_PUBLIC_IP` | VM2 public IP |
| `SSH_PRIVATE_KEY` | Your SSH private key (`cat ~/.ssh/id_rsa`) |
| `SSH_USER` | SSH user (ubuntu) — optional |

### 4.2 Rolling Deploy Workflow

A GitHub Actions workflow is provided at `.github/workflows/deploy.yml`. It performs a rolling deploy by SSHing into each VM and running these steps on each host:

- `git pull origin main`
- ensure Python 3.11 and `venv` are installed
- create/refresh `/app/venv` and install dependencies with `/app/venv/bin/pip install -r requirements.txt`
- restart the `fastapi` systemd service (`sudo systemctl restart fastapi`)
- wait for the `/health` endpoint to return HTTP 200 before proceeding to the next VM

Required GitHub Secrets: `VM1_PUBLIC_IP`, `VM2_PUBLIC_IP`, `SSH_PRIVATE_KEY` (and optionally `SSH_USER`). See the workflow file for the exact commands used.

---

## Part 5 — Project File Structure

```
your-repo/
├── .github/
│   └── workflows/
│       └── deploy.yml          ← CI/CD rolling deploy (Part 4)
├── frontend/                   ← Next.js app
│   ├── app/
│   ├── components/
│   ├── package.json
│   └── next.config.js
├── backend/                    ← FastAPI app
│   ├── main.py                 ← App entry point with /health
│   ├── routers/
│   │   ├── products.py
│   │   ├── orders.py
│   │   └── auth.py
│   ├── models.py               ← SQLAlchemy models
│   ├── database.py             ← MySQL connection (SQLAlchemy)
│   ├── requirements.txt
│   └── .env                    ← NOT committed to git
├── .gitignore
└── README_Deployment.md        ← This file
```

### database.py (SQLAlchemy + MySQL HeatWave)

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_size=5,        # Max 5 connections per worker (2 workers × 2 VMs = 20 max)
    max_overflow=2,
    pool_pre_ping=True, # Auto-reconnect on stale connections
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### requirements.txt

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
sqlalchemy>=2.0.0
pymysql>=1.1.0
cryptography>=42.0.0
python-dotenv>=1.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
```

---

## Part 6 — CORS Configuration (Next.js ↔ FastAPI)

```python
# main.py — add CORS middleware
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-project.vercel.app",
        "https://yourdomain.com",   # if custom domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Part 7 — SSL/HTTPS (Optional but Recommended)

To add HTTPS on the Load Balancer using Let's Encrypt:

1. Point your domain DNS `A` record → Load Balancer public IP
2. On **one** VM, generate the certificate:
   ```bash
   sudo apt install certbot
   sudo certbot certonly --standalone -d api.yourdomain.com
   ```
3. Upload the certificate to **OCI Load Balancer → Certificates**
4. Add an HTTPS Listener on port 443 with the uploaded certificate
5. Update `NEXT_PUBLIC_API_URL` in Vercel to `https://api.yourdomain.com`

---

## Part 8 — Monitoring & Logs

```bash
# View FastAPI logs on any VM
sudo journalctl -u fastapi -f

# Check service status
sudo systemctl status fastapi

# View Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Test health endpoint manually
curl http://localhost:8000/health
```

---

## Always Free Resources — Summary

| Resource | Quota | Limit |
|----------|-------|-------|
| AMD Micro VMs | 2 instances | 1/8 OCPU, 1 GB RAM each |
| Boot volumes | 200 GB total | 100 GB per VM |
| Flexible Load Balancer | 1 instance | 10 Mbps bandwidth |
| MySQL HeatWave | 1 standalone node | 50 GB data + 50 GB backup |
| Outbound traffic | 10 TB/month | — |
| Vercel (Next.js) | Unlimited deploys | Hobby plan |
| GitHub Actions | 3,000 min/month | Student Pro |

---

## Troubleshooting

**VM not responding after deploy:**
```bash
sudo systemctl status fastapi
sudo journalctl -u fastapi --since "5 minutes ago"
```

**Load Balancer shows VM as unhealthy:**
- Check `/health` endpoint responds with HTTP 200
- Verify Security List allows TCP 8000 from `10.0.0.0/16`
- Check Uvicorn is bound to `127.0.0.1:8000` and Nginx to `0.0.0.0:8000`

**MySQL connection refused:**
- Verify MySQL private endpoint IP in `.env`
- Confirm VM is in the same VCN as HeatWave
- Check private-subnet Security List allows TCP 3306 from public-subnet CIDR

**GitHub Actions SSH timeout:**
- Confirm VM public IP hasn't changed (use reserved public IP in OCI to be safe)
- Verify SSH port 22 is open in the Security List
