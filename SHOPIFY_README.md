# Shopify XML Feed Integration

Bu proje, Trendyol XML feed'inizi Shopify mağazanızla otomatik olarak senkronize etmenizi sağlar. Sistem, ürünlerin ilk yüklenmesini ve sonrasında fiyat/stok değişikliklerinin periyodik takibini gerçekleştirir.

## Özellikler

- **İlk Ürün Yükleme**: XML feed'deki tüm ürünleri Shopify mağazanıza yükler
- **Periyodik Takip**: Belirli aralıklarla XML feed'i kontrol eder
- **Fiyat/Stok Güncelleme**: Değişiklikleri otomatik olarak Shopify'a uygular
- **Varyant Desteği**: Renk, beden gibi ürün varyantlarını destekler
- **Hata Yönetimi**: Otomatik yeniden deneme ve hata raporlama
- **GitHub Actions**: Otomatik çalışma için CI/CD entegrasyonu

## Kurulum

### 1. Gereksinimler

```bash
pip install -r requirements.txt
```

### 2. Shopify API Erişimi

Shopify Admin API'ye erişim için:
1. Shopify admin panelinde "Apps" > "App and sales channel settings" > "Develop apps" 
2. "Create an app" ile yeni uygulama oluşturun
3. "Admin API access" kısmında gerekli izinleri verin:
   - Products: Read/Write
   - Inventory: Read/Write
   - Product listings: Read/Write

### 3. Konfigürasyon

```bash
python setup_shopify.py
```

Bu komut size interaktif olarak soracak:
- Shopify mağaza domain'i (örn: mystore.myshopify.com)
- Admin API access token
- XML feed URL'i
- Takip aralığı (dakika)

## Kullanım

### Manuel Kullanım

#### İlk Ürün Yükleme
```bash
python shopify_integration.py \
  --shop-domain mystore.myshopify.com \
  --access-token your_access_token \
  --xml-feed data/products.xml \
  --mode initial
```

#### Güncelleme (Fiyat/Stok Takibi)
```bash
python shopify_integration.py \
  --shop-domain mystore.myshopify.com \
  --access-token your_access_token \
  --xml-feed data/products.xml \
  --mode update
```

### Otomatik Monitoring

#### Daemon Modu (Sürekli Çalışma)
```bash
python feed_monitor.py --config shopify_config.json --mode daemon
```

#### Tek Seferlik Kontrol
```bash
python feed_monitor.py --config shopify_config.json --mode once
```

#### Durum Kontrolü
```bash
python feed_monitor.py --config shopify_config.json --mode status
```

### GitHub Actions ile Otomatik Çalışma

Repository secrets'e şunları ekleyin:
- `SHOPIFY_SHOP_DOMAIN`: Mağaza domain'i
- `SHOPIFY_ACCESS_TOKEN`: API access token
- `XML_FEED_URL`: Canlı XML feed URL'i (opsiyonel)

Workflow otomatik olarak her 30 dakikada çalışacak ve değişiklikleri takip edecektir.

## Dosya Yapısı

```
├── shopify_integration.py     # Ana Shopify API entegrasyonu
├── feed_monitor.py           # XML feed monitoring daemon'u
├── setup_shopify.py          # İnteraktif kurulum scripti
├── requirements.txt          # Python bağımlılıkları
├── .github/workflows/
│   └── shopify-sync.yml     # GitHub Actions workflow
└── data/
    └── *.xml                # XML feed dosyaları
```

## Konfigürasyon Dosyası Örneği

```json
{
  "xml_feed_url": "https://example.com/feed.xml",
  "shopify": {
    "shop_domain": "mystore.myshopify.com",
    "access_token": "your_access_token"
  },
  "monitor_interval_minutes": 30,
  "max_retry_attempts": 3,
  "retry_delay_seconds": 60,
  "local_xml_cache": "cached_feed.xml",
  "state_file": "sync_state.json",
  "max_sync_errors": 5
}
```

## Nasıl Çalışır?

### 1. İlk Yükleme
- XML feed'deki tüm ürünler Shopify'a yüklenir
- Her ürün için benzersiz hash değeri hesaplanır
- Shopify product ID'leri state dosyasında saklanır

### 2. Periyodik Takip
- Belirli aralıklarla XML feed indirilir
- Her ürün için hash değeri hesaplanır
- Önceki hash ile karşılaştırılır
- Değişen ürünler Shopify'da güncellenir

### 3. Değişiklik Algılama
- Fiyat değişiklikleri
- Stok miktarı değişiklikleri
- Varyant fiyat/stok değişiklikleri
- Yeni ürün eklemeleri

## Hata Yönetimi

- **Rate Limiting**: API çağrıları arasında otomatik bekleme
- **Retry Logic**: Başarısız işlemler otomatik yeniden denenir
- **Error Counting**: Çok fazla hata durumunda sistem durur
- **Logging**: Tüm işlemler detaylı loglanır

## Güvenlik

- API token'ları environment variable veya secrets olarak saklanmalı
- State dosyaları .gitignore'a eklenmelidir
- Log dosyalarında hassas bilgi bulunmamalıdır

## Troubleshooting

### Yaygın Hatalar

1. **API Rate Limit**: 
   - Çözüm: Monitor interval'ı artırın

2. **Shopify API Errors**:
   - Token'ın geçerli olduğundan emin olun
   - Gerekli izinlerin verildiğini kontrol edin

3. **XML Parse Errors**:
   - XML feed'in geçerli olduğunu kontrol edin
   - Encoding sorunları için UTF-8 kullanın

### Log Dosyaları
- `feed_monitor.log`: Monitoring işlemleri
- Console output: Gerçek zamanlı işlem durumu

## Lisans

Bu proje Trendyol XML feed dönüştürme sistemine Shopify entegrasyonu ekler.