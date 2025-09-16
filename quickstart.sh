#!/bin/bash

# Shopify XML Feed Integration - Quick Start Guide
# Bu script, Shopify entegrasyonunu hızlı başlatmanız için örnek komutları içerir

echo "🚀 Shopify XML Feed Integration - Quick Start"
echo "============================================="

echo ""
echo "1️⃣ Kurulum:"
echo "pip install -r requirements.txt"

echo ""
echo "2️⃣ Demo çalıştırma:"
echo "python3 demo.py"

echo ""
echo "3️⃣ Interaktif kurulum:"
echo "python3 setup_shopify.py"

echo ""
echo "4️⃣ İlk ürün yükleme (manuel):"
echo 'python3 shopify_integration.py \'
echo '  --shop-domain mystore.myshopify.com \'
echo '  --access-token your_access_token \'
echo '  --xml-feed data/chekich21_synthetic_bullets_titled_nobrand.xml \'
echo '  --mode initial'

echo ""
echo "5️⃣ Güncelleme kontrolü (manuel):"
echo 'python3 shopify_integration.py \'
echo '  --shop-domain mystore.myshopify.com \'
echo '  --access-token your_access_token \'
echo '  --xml-feed data/chekich21_synthetic_bullets_titled_nobrand.xml \'
echo '  --mode update'

echo ""
echo "6️⃣ Monitoring konfigürasyonu oluşturma:"
echo "python3 feed_monitor.py --config monitor.json --mode create-config"

echo ""
echo "7️⃣ Tek seferlik kontrol:"
echo "python3 feed_monitor.py --config monitor.json --mode once"

echo ""
echo "8️⃣ Sürekli monitoring (daemon):"
echo "python3 feed_monitor.py --config monitor.json --mode daemon"

echo ""
echo "9️⃣ GitHub Actions için gerekli secrets:"
echo "- SHOPIFY_SHOP_DOMAIN: mystore.myshopify.com"
echo "- SHOPIFY_ACCESS_TOKEN: your_shopify_access_token"
echo "- XML_FEED_URL: https://example.com/live-feed.xml"

echo ""
echo "📚 Detaylı bilgi için SHOPIFY_README.md dosyasını okuyun"
echo ""
echo "✅ Sistem hazır! Demo ile başlayabilirsiniz: python3 demo.py"