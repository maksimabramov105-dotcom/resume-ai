#!/bin/bash
# github_pages_deploy.sh — Deploy landing page to GitHub Pages
# Prerequisites: git, GitHub account, repo must exist
# Usage: bash github_pages_deploy.sh YOUR_GITHUB_USERNAME YOUR_REPO_NAME
#
# CUSTOM DOMAIN RECOMMENDATION:
# ============================================================
# Best option: resumeai.bot
#   - Price: ~$25-35/year
#   - Register at: porkbun.com (cheapest) or namecheap.com
#   - .bot domains are tech-forward, memorable, relevant
#
# Alternative options:
#   - resumeai.me      (~$10-15/year at namecheap.com)
#   - resumeai.app     (~$20/year) — Google-owned TLD, trusted
#   - autoapply.ru     (~$5/year) — for Russian market
#   - resumeai.ru      (~$5/year)
#
# RECOMMENDED: Buy resumeai.bot at porkbun.com (~$29/year)
# or resumeai.app at Google Domains ($20/year, very professional)
#
# DNS SETUP AFTER PURCHASE:
# Add these records at your domain registrar:
#   A     @         185.199.108.153
#   A     @         185.199.109.153
#   A     @         185.199.110.153
#   A     @         185.199.111.153
#   CNAME www       YOUR_GITHUB_USERNAME.github.io
#
# GitHub Pages Settings → Custom domain → enter: resumeai.bot → Save
# GitHub auto-enables HTTPS after DNS propagates (~10 minutes)
# ============================================================

GITHUB_USER="${1:-YOUR_USERNAME}"
REPO_NAME="${2:-resumeai-landing}"

set -e

echo "🚀 Deploying landing page to GitHub Pages..."
echo "   Repo: github.com/$GITHUB_USER/$REPO_NAME"
echo ""

# Create a temporary deploy directory with just landing files
DEPLOY_DIR=$(mktemp -d)
cp landing/index.html "$DEPLOY_DIR/"
cp landing/robots.txt "$DEPLOY_DIR/"
cp landing/sitemap.xml "$DEPLOY_DIR/"

# Add CNAME file if you have a custom domain
# echo "resumeai.bot" > "$DEPLOY_DIR/CNAME"

cd "$DEPLOY_DIR"
git init
git add .
git commit -m "Deploy landing page $(date '+%Y-%m-%d %H:%M')"

# Push to gh-pages branch
git remote add origin "https://github.com/$GITHUB_USER/$REPO_NAME.git"
git push -f origin HEAD:gh-pages

cd -
rm -rf "$DEPLOY_DIR"

echo "✅ Deployed to GitHub Pages!"
echo ""
echo "Your landing page URL:"
echo "  https://$GITHUB_USER.github.io/$REPO_NAME/"
echo ""
echo "To use custom domain:"
echo "  1. Buy domain (see DNS SETUP instructions above)"
echo "  2. Add DNS records at registrar"
echo "  3. GitHub: Settings → Pages → Custom domain → resumeai.bot"
echo "  4. Wait 10 min, HTTPS auto-activates"
echo ""
echo "To update: run this script again (force-pushes to gh-pages)"
