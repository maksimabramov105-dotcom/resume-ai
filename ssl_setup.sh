#!/bin/bash
# ssl_setup.sh — One-time SSL setup for resumeai.bot
# RUN ONLY AFTER domain DNS is pointing to 72.56.250.53
# Run: bash ssl_setup.sh
#
# PREREQUISITE CHECK:
# Before running, verify DNS is propagated:
#   dig resumeai.bot +short   → should return 72.56.250.53
#   or: curl -I http://resumeai.bot  → should return 200

MY_EMAIL="maxim737@outlook.com"
DOMAIN="resumeai.bot"
WWW_DOMAIN="www.resumeai.bot"
VPS_IP="72.56.250.53"

set -e

echo "🔒 SSL Setup for $DOMAIN"
echo "================================"

# Check DNS propagation first
echo "▶ Checking DNS..."
RESOLVED=$(dig +short $DOMAIN 2>/dev/null | head -1)
if [ "$RESOLVED" != "$VPS_IP" ]; then
  echo "⚠️  DNS not propagated yet."
  echo "   $DOMAIN resolves to: $RESOLVED"
  echo "   Expected: $VPS_IP"
  echo ""
  echo "   Add these DNS records at your registrar:"
  echo "   A     @     $VPS_IP"
  echo "   A     www   $VPS_IP"
  echo "   CNAME www   $DOMAIN"
  echo ""
  echo "   Then wait 5-30 minutes and re-run this script."
  exit 1
fi
echo "  ✅ DNS points to $VPS_IP"

# Install certbot
echo "▶ Installing certbot..."
apt-get update -qq
apt-get install -y certbot python3-certbot-nginx -q
echo "  ✅ Certbot installed"

# Stop nginx briefly for standalone challenge (or use nginx plugin)
echo "▶ Obtaining SSL certificate..."
certbot --nginx \
  -d "$DOMAIN" \
  -d "$WWW_DOMAIN" \
  --non-interactive \
  --agree-tos \
  --email "$MY_EMAIL" \
  --redirect
echo "  ✅ SSL certificate obtained"

# Test renewal
echo "▶ Testing auto-renewal..."
certbot renew --dry-run
echo "  ✅ Auto-renewal test passed"

# Add cron for auto-renewal (runs daily at noon)
(crontab -l 2>/dev/null | grep -v certbot; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
echo "  ✅ Auto-renewal cron added"

# Reload nginx
systemctl reload nginx

echo ""
echo "================================"
echo "✅ SSL active for $DOMAIN"
echo "🔒 HTTPS enabled automatically"
echo "♻️  Auto-renewal configured (daily check)"
echo ""
echo "Test your sites:"
echo "  https://$DOMAIN"
echo "  https://$DOMAIN/app"
echo "================================"
