#!/bin/bash
# add_tracking.sh — Inject real tracking codes into index.html
# Usage: bash add_tracking.sh G-XXXXXXXXXX 12345678
#
# HOW TO GET GOOGLE ANALYTICS 4 ID (G-XXXXXXXXXX):
# ============================================================
# 1. Go to: https://analytics.google.com
# 2. Click "Start measuring" (or Admin gear → Create Property)
# 3. Property name: "ResumeAI Bot" → click Next
# 4. Choose: Web → enter URL: resumeai.bot (or your GitHub Pages URL)
# 5. Click "Create stream"
# 6. Your G- ID appears at top right: copy it (format: G-XXXXXXXXXX)
# Total time: ~3 minutes
#
# HOW TO GET YANDEX METRIKA ID (8-digit number):
# ============================================================
# 1. Go to: https://metrika.yandex.ru
# 2. Click "Добавить счётчик"
# 3. Name: "РезюмеАИ", URL: resumeai.bot
# 4. Click "Создать счётчик"
# 5. Your counter ID appears (8 digits): copy it
# Total time: ~2 minutes
# ============================================================

GOOGLE_ID="$1"
YANDEX_ID="$2"
HTML_FILE="landing/index.html"

if [ -z "$GOOGLE_ID" ] || [ -z "$YANDEX_ID" ]; then
  echo "Usage: bash add_tracking.sh G-XXXXXXXXXX 12345678"
  exit 1
fi

# Replace Google Analytics placeholder
GA_CODE="  <!-- Google Analytics 4 -->\n  <script async src=\"https://www.googletagmanager.com/gtag/js?id=${GOOGLE_ID}\"></script>\n  <script>\n    window.dataLayer = window.dataLayer || [];\n    function gtag(){dataLayer.push(arguments);}\n    gtag('js', new Date());\n    gtag('config', '${GOOGLE_ID}');\n  </script>"

# Replace Yandex Metrika placeholder
YM_CODE="  <!-- Yandex Metrika -->\n  <script type=\"text/javascript\">\n   (function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};\n   m[i].l=1*new Date();\n   for(var j=0;j<document.scripts.length;j++){if(document.scripts[j].src===r){return;}}\n   k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)})\n   (window, document, \"script\", \"https://mc.yandex.ru/metrika/tag.js\", \"ym\");\n   ym(${YANDEX_ID}, \"init\", { clickmap:true, trackLinks:true, accurateTrackBounce:true });\n  </script>\n  <noscript><div><img src=\"https://mc.yandex.ru/watch/${YANDEX_ID}\" style=\"position:absolute; left:-9999px;\" alt=\"\" /></div></noscript>"

# Do replacements
sed -i.bak "s|<!-- GOOGLE_ANALYTICS_PLACEHOLDER -->|${GA_CODE}|" "$HTML_FILE"
sed -i.bak "s|<!-- YANDEX_METRIKA_PLACEHOLDER -->|${YM_CODE}|" "$HTML_FILE"

echo "✅ Tracking codes added to $HTML_FILE"
echo "   Google Analytics: $GOOGLE_ID"
echo "   Yandex Metrika: $YANDEX_ID"
echo ""
echo "Next: deploy updated index.html to your hosting"
