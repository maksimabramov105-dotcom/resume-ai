#!/bin/bash
# setup_nginx.sh — Install and configure Nginx for ResumeAI
# Safe to run multiple times (idempotent).

set -e
echo "⚙️  Setting up Nginx..."

# Install if not present
if ! command -v nginx &>/dev/null; then
  apt-get update -qq && apt-get install -y nginx -q
  echo "  ✅ Nginx installed"
else
  echo "  ✅ Nginx already installed"
fi

# Deploy config
cp /opt/resumeaibot/nginx_resumeai.conf /etc/nginx/sites-available/resumeai
ln -sf /etc/nginx/sites-available/resumeai /etc/nginx/sites-enabled/resumeai
rm -f /etc/nginx/sites-enabled/default

# Test
nginx -t

# Reload
systemctl enable nginx
systemctl reload nginx || systemctl start nginx

echo ""
echo "✅ Nginx configured."
echo "   Landing page:  http://$(curl -s ifconfig.me 2>/dev/null || echo 72.56.250.53)"
echo "   AutoApply app: http://$(curl -s ifconfig.me 2>/dev/null || echo 72.56.250.53)/app"
