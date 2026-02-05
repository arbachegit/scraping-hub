#!/bin/bash
# ===========================================
# Scraping Hub - Setup Script
# Run on DigitalOcean Droplet
# ===========================================

set -e

echo "=== Scraping Hub Setup ==="

# Update system
echo "[1/8] Updating system..."
apt update && apt upgrade -y

# Install dependencies
echo "[2/8] Installing dependencies..."
apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git

# Create app directory
echo "[3/8] Creating app directory..."
mkdir -p /opt/scraping-hub
cd /opt/scraping-hub

# Clone or update repo
echo "[4/8] Cloning repository..."
if [ -d ".git" ]; then
    git pull origin main
else
    git clone https://github.com/arbachegit/scraping-hub.git .
fi

# Create virtual environment
echo "[5/8] Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if not exists
echo "[6/8] Configuring environment..."
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# Scraping Hub Configuration
CORESIGNAL_API_KEY=BzRdg5U74jF4SCZJXnR3NSiXnpaelagv
CORESIGNAL_BASE_URL=https://api.coresignal.com/cdapi/v1
PROXYCURL_API_KEY=your_proxycurl_api_key_here
PROXYCURL_BASE_URL=https://nubela.co/proxycurl/api/v2
FIRECRAWL_API_KEY=fc-01cb38d4fef94a619ab48349df50c89c
FIRECRAWL_BASE_URL=https://api.firecrawl.dev
CORESIGNAL_RATE_LIMIT=100
PROXYCURL_RATE_LIMIT=50
FIRECRAWL_RATE_LIMIT=200
RATE_LIMIT_PERIOD=60
CACHE_TTL=3600
LOG_LEVEL=INFO
ENVIRONMENT=production
EOF
fi

# Install systemd service
echo "[7/8] Installing systemd service..."
cp deploy/scraping-hub.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable scraping-hub
systemctl restart scraping-hub

# Configure Nginx
echo "[8/8] Configuring Nginx..."
cp deploy/nginx.conf /etc/nginx/sites-available/scraping-hub
ln -sf /etc/nginx/sites-available/scraping-hub /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test nginx config
nginx -t

# Get SSL certificate
echo "Getting SSL certificate..."
certbot --nginx -d scraping.iconsai.ai --non-interactive --agree-tos -m admin@iconsai.ai || true

# Restart services
systemctl restart nginx
systemctl restart scraping-hub

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "URL: https://scraping.iconsai.ai"
echo "Login: admin@iconsai.ai / admin123"
echo ""
echo "Commands:"
echo "  systemctl status scraping-hub   # Check status"
echo "  journalctl -u scraping-hub -f   # View logs"
echo "  systemctl restart scraping-hub  # Restart"
