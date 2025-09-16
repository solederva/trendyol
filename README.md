# Trendyol XML Feed Tools

Bu repository, Trendyol XML feed'lerinin farklı formatlara dönüştürülmesi ve Shopify entegrasyonu için geliştirilen araçları içerir.

## Özellikler

- **XML Feed Dönüştürme**: Trendyol XML formatını Stockmount formatına dönüştürme
- **Shopify Entegrasyonu**: XML feed'leri Shopify mağazasına otomatik yükleme ve güncelleme
- **Periyodik Takip**: Canlı XML feed'lerin düzenli olarak takip edilmesi
- **Fiyat/Stok Güncelleme**: Değişikliklerin otomatik tespiti ve uygulanması
- **GitHub Actions**: Otomatik çalışma için CI/CD desteği

## Shopify Entegrasyonu

Shopify mağazanız için XML feed entegrasyonu kurulumu:

1. [SHOPIFY_README.md](SHOPIFY_README.md) dosyasını okuyun
2. Gerekli bağımlılıkları yükleyin: `pip install -r requirements.txt`
3. Kurulum scriptini çalıştırın: `python setup_shopify.py`
4. İlk ürün yükleme: `python shopify_integration.py --mode initial ...`
5. Otomatik takip: `python feed_monitor.py --mode daemon ...`

## XML Dönüştürme (Stockmount)