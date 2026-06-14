# Deployment Guide — Oracle Cloud Free Tier (1 AMD VM + MySQL) + Vercel

> **Stack:** Next.js (Vercel) · FastAPI (1× Oracle AMD Micro VM, Uvicorn + Nginx) · MySQL (Oracle Free) · HTTPS via Let's Encrypt on `caribooks.duckdns.org`
> **Cost:** $0/month permanently · No cold starts

> ℹ️ **No load balancer, single backend VM.** A redundant setup (multiple VMs behind a load balancer) remains a possible evolution if traffic grows.

---

## Architecture Overview

```
Internet
    │
    ▼
┌─────────────────────────────┐
│   Vercel (Next.js Frontend) │  CDN worldwide · caribooks.vercel.app
│   Auto-deploy on git push   │
└─────────────────────────────┘
    │ API calls (HTTPS)
    ▼
┌─────────────────────────────────────────────┐
│  Oracle Cloud VM — caribooks.duckdns.org     │  1× AMD Micro (1/8 OCPU, 1 GB RAM)
│  Nginx (:443 TLS, Let's Encrypt) ─► Uvicorn  │  Ubuntu 22.04
│  FastAPI :8000 (127.0.0.1) · systemd · Docker│
└──────────────────────┬──────────────────────┘
                       │ private VCN (port 3306)
                       ▼
┌─────────────────────────────┐
│  MySQL (Oracle Free)        │  Private subnet — internal OCI network only
└─────────────────────────────┘
```

---

## Prerequisites

- Oracle Cloud account (credit card required for verification, never charged)
- GitHub account with Student Developer Pack (GitHub Pro — 3,000 Actions min/month)
- Vercel account (free, no credit card)
- A free **DuckDNS** subdomain (`caribooks.duckdns.org`) pointing to the VM public IP

---

## Part 1 — Oracle Cloud Setup

### 1.1 Create the Virtual Cloud Network (VCN)

1. Go to **Networking → Virtual Cloud Networks → Create VCN**
2. Name: `caribooks-vcn`
3. CIDR block: `10.0.0.0/16`
4. Check **Use DNS Hostnames**
5. Click **Create VCN**

Then add two subnets:

| Subnet | CIDR | Type | Purpose |
|--------|------|------|---------|
| `public-subnet` | `10.0.0.0/24` | Public | Backend VM |
| `private-subnet` | `10.0.1.0/24` | Private | MySQL |

### 1.2 Configure Security Lists

For **public-subnet**, add ingress rules:

| Protocol | Port | Source | Purpose |
|----------|------|--------|---------|
| TCP | 22 | `0.0.0.0/0` | SSH access |
| TCP | 80 | `0.0.0.0/0` | HTTP (Let's Encrypt challenge + redirect) |
| TCP | 443 | `0.0.0.0/0` | HTTPS (public API) |

For **private-subnet**, add ingress rules:

| Protocol | Port | Source | Purpose |
|----------|------|--------|---------|
| TCP | 3306 | `10.0.0.0/24` | MySQL from the VM only |

> Port 8000 (Uvicorn) is **not** exposed publicly — Uvicorn binds to `127.0.0.1:8000` and is reached only through Nginx.

### 1.3 Create the AMD Micro VM

Go to **Compute → Instances → Create Instance**:

- **Image:** Ubuntu 22.04 Minimal
- **Shape:** VM.Standard.E2.1.Micro (Always Free)
- **OCPU:** 1/8 (shared) · **RAM:** 1 GB
- **Subnet:** public-subnet
- **Assign public IP:** Yes (use a **reserved** public IP so it does not change)
- **SSH key:** Upload your public key

Name it `caribooks-vm`. Note its **Public IP** and **Private IP** (`10.0.0.x`).

### 1.4 Create the MySQL Database (Oracle Free)

Go to **Databases → MySQL HeatWave → DB Systems → Create**:

- **Name:** `caribooks-mysql`
- **Shape:** MySQL.Free (Always Free)
- **Admin user:** `admin`
- **Admin password:** (choose a strong password)
- **Subnet:** private-subnet (NOT public)
- **Availability:** Standalone (free tier)

> ⚠️ Note the **Private Endpoint IP** (e.g. `10.0.1.10`) — the only address the VM uses to connect to MySQL.

### 1.5 Point DuckDNS to the VM

1. Sign in to [duckdns.org](https://www.duckdns.org) and create the subdomain `caribooks`.
2. Set its IP to the VM's **reserved public IP** (`caribooks.duckdns.org` → VM IP).
3. (Recommended) Install the DuckDNS updater cron on the VM so the record follows the IP:
   ```bash
   mkdir -p ~/duckdns && cd ~/duckdns
   echo 'echo url="https://www.duckdns.org/update?domains=caribooks&token=<YOUR_TOKEN>&ip=" | curl -k -o ~/duckdns/duck.log -K -' > duck.sh
   chmod 700 duck.sh
   (crontab -l 2>/dev/null; echo "*/5 * * * * ~/duckdns/duck.sh >/dev/null 2>&1") | crontab -
   ```

---

## Part 2 — FastAPI Setup on the VM

### 2.1 Initial Server Setup

```bash
# Connect to the VM
ssh ubuntu@<VM_PUBLIC_IP>

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python, Nginx and Certbot
sudo apt install -y python3.11 python3.11-venv python3-pip git nginx certbot python3-certbot-nginx

# Create app directory and user
sudo useradd -m -s /bin/bash appuser
sudo mkdir -p /app
sudo chown appuser:appuser /app
```

### 2.2 Clone and Configure the App

```bash
sudo su - appuser
git clone https://github.com/Visualstudiocodetest/caribooks.git /app
cd /app

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

### 2.3 Environment Variables

```bash
# Create /app/.env
cat <<EOF > /app/.env
DATABASE_URL=mysql+pymysql://admin:<PASSWORD>@10.0.1.10:3306/caribooks
SECRET_KEY=<YOUR_SECRET_KEY>
ENVIRONMENT=production
FRONTEND_BASE_URL=https://caribooks.vercel.app
# PostFinance, Google OAuth, etc.
EOF
chmod 600 /app/.env
```

### 2.4 Health Endpoint

The FastAPI app already exposes a `/health` endpoint (used for monitoring and uptime checks):

```python
@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

### 2.5 Systemd Service

```bash
# Exit appuser, back to ubuntu
exit

sudo nano /etc/systemd/system/fastapi.service
```

```ini
[Unit]
Description=CARIBOOKS FastAPI Backend
After=network.target

[Service]
User=appuser
WorkingDirectory=/app/backend
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

> Alternatively, the app can be run with **Docker** (`docker compose up -d`); the systemd unit above is the lightweight option for a single Always-Free VM.

### 2.6 Nginx Reverse Proxy + HTTPS

```bash
sudo nano /etc/nginx/sites-available/caribooks
```

```nginx
server {
    listen 80;
    server_name caribooks.duckdns.org;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/caribooks /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Issue and auto-renew the Let's Encrypt certificate (adds the :443 server block)
sudo certbot --nginx -d caribooks.duckdns.org --redirect
```

Certbot rewrites the Nginx config to serve **HTTPS on port 443** and redirect HTTP → HTTPS. Renewal is automatic via the `certbot.timer` systemd timer.

---

## Part 3 — Vercel Frontend (Next.js)

### 3.1 Connect GitHub to Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New Project**
2. Import the GitHub repository
3. Framework: **Next.js** (auto-detected)
4. Root directory: `frontend/`

### 3.2 Environment Variables in Vercel

In **Project Settings → Environment Variables**, add:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_BACKEND_BASE_URL` | `https://caribooks.duckdns.org` |
| `BACKEND_BASE_URL` | `https://caribooks.duckdns.org` |

### 3.3 Automatic Deployments

Every push to `main` → Vercel auto-deploys the frontend. No GitHub Actions needed for the frontend — Vercel's GitHub integration handles it natively.

---

## Part 4 — CI/CD GitHub Actions

### 4.1 GitHub Secrets to Configure

Go to your repo **Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|--------|-------|
| `VM_PUBLIC_IP` | The VM public IP |
| `SSH_PRIVATE_KEY` | Your SSH private key (`cat ~/.ssh/id_rsa`) |
| `SSH_USER` | SSH user (`ubuntu`) — optional |

### 4.2 Deploy Workflow

A GitHub Actions workflow (`.github/workflows/deploy.yml`) deploys to the single VM by SSHing into it and running:

- `git pull origin main`
- ensure Python 3.11 and `venv` are installed
- install/refresh dependencies with `/app/venv/bin/pip install -r backend/requirements.txt`
- restart the `fastapi` systemd service (`sudo systemctl restart fastapi`)
- wait for `https://caribooks.duckdns.org/health` to return HTTP 200

---

## Part 5 — CORS Configuration (Next.js ↔ FastAPI)

```python
# backend/main.py — CORS middleware
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://caribooks.vercel.app",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Part 6 — Monitoring & Logs

```bash
# View FastAPI logs
sudo journalctl -u fastapi -f

# Check service status
sudo systemctl status fastapi

# View Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Test health endpoint
curl https://caribooks.duckdns.org/health
```

---

## Always Free Resources — Summary

| Resource | Quota | Limit |
|----------|-------|-------|
| AMD Micro VM | 1 instance | 1/8 OCPU, 1 GB RAM |
| Boot volume | up to 200 GB | — |
| MySQL (Oracle Free) | 1 standalone node | 50 GB data + 50 GB backup |
| Outbound traffic | 10 TB/month | — |
| Vercel (Next.js) | Unlimited deploys | Hobby plan |
| GitHub Actions | 3,000 min/month | Student Pro |
| DuckDNS | Free subdomain | — |

---

## Troubleshooting

**VM not responding after deploy:**
```bash
sudo systemctl status fastapi
sudo journalctl -u fastapi --since "5 minutes ago"
```

**HTTPS / certificate issues:**
- Ensure ports 80 and 443 are open in the Security List
- Confirm `caribooks.duckdns.org` resolves to the VM public IP
- Re-run `sudo certbot --nginx -d caribooks.duckdns.org` and check `sudo certbot renew --dry-run`

**MySQL connection refused:**
- Verify the MySQL private endpoint IP in `/app/.env`
- Confirm the VM is in the same VCN as the database
- Check the private-subnet Security List allows TCP 3306 from the public-subnet CIDR

**GitHub Actions SSH timeout:**
- Use a **reserved** public IP in OCI so it does not change
- Verify SSH port 22 is open in the Security List
