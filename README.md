# Trendyol Stockmount Feed Manager

Bu proje, Trendyol e-ticaret platformu için otomatik ürün feed yönetimi sağlar. Kaynak XML verilerini Stockmount formatına dönüştürür ve fiyat/stok güncellemelerini otomatik olarak gerçekleştirir.

## 🚀 Özellikler

- **Otomatik Feed Dönüşümü**: Kaynak XML → Stockmount XML
- **Buybox Koruması**: Rastgele prefix'ler ve benzersiz markalar ile buybox'a takılmayı önler
- **Benzersiz Barkod Üretimi**: Çakışma önlemek için hash tabanlı sentetik barkodlar
- **Otomatik Güncellemeler**: GitHub Actions ile 30 dakikalık periyotlarda
- **Varyant Desteği**: Renk ve beden varyantlarını işler
- **Resim URL Temizleme**: Benzersiz parametreler ile buybox eşleşmesini önler

## 📋 Gereksinimler

- Python 3.11+
- GitHub Actions (otomatik güncellemeler için)
- Kaynak XML feed URL'i (secrets.SOURCE_FEED_URL)

## 🛠️ Kurulum

1. Repository'yi klonlayın:
```bash
git clone https://github.com/solederva/trendyol.git
cd trendyol
```

2. Python ortamını hazırlayın:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# veya
.venv\Scripts\activate     # Windows
```

3. Gerekli paketleri yükleyin (şu anda yok):
```bash
# Henüz harici bağımlılık yok
```

## 📊 Kullanım

### Manuel Dönüşüm

```bash
# Temel dönüşüm
python convert_to_stockmount.py \
  --input data/source_chekich.xml \
  --output data/output.xml \
  --variant-mode \
  --barcode-strategy synthetic

# Tüm özelliklerle
python convert_to_stockmount.py \
  --input data/source_chekich.xml \
  --output data/chekich21_synthetic_bullets_titled_nobrand.xml \
  --variant-mode \
  --barcode-strategy synthetic \
  --barcode-prefix "2199" \
  --add-bullets \
  --title-template "Solederva {URUN} {RENK} - {MODEL}" \
  --brand-override SDSTEP \
  --sanitize-images
```

### Buybox Koruması

```bash
python strengthen_buybox_protection.py
```

### Ürün Temizleme

```bash
python remove_wg_products.py
```

## ⚙️ Yapılandırma

### GitHub Secrets

- `SOURCE_FEED_URL`: Kaynak XML feed URL'i (opsiyonel, varsayılan: data/source.xml)
- `GITHUB_TOKEN`: Repository yazma izni için otomatik oluşturulur

### Komut Parametreleri

| Parametre | Açıklama | Varsayılan |
|-----------|----------|------------|
| `--input` | Kaynak XML dosyası | - |
| `--output` | Çıktı XML dosyası | - |
| `--variant-mode` | Varyantları dahil et | False |
| `--barcode-strategy` | Barkod stratejisi (keep/blank/synthetic) | keep |
| `--barcode-prefix` | Sentetik barkod prefix'i | 2199 |
| `--add-bullets` | Otomatik özellik listesi ekle | False |
| `--title-template` | Başlık şablonu | - |
| `--brand-override` | Marka değiştirme | - |
| `--sanitize-images` | Resim URL'lerini temizle | False |

## 🔄 Otomatik Güncellemeler

GitHub Actions workflow'u aşağıdaki zamanlamada çalışır:

### Hafta İçi (Pazartesi-Cuma)
- 08:00 - 13:30 arası her 30 dakikada bir
- Saat 14:00'te final güncelleme

### Hafta Sonu
- Cumartesi: 09:00
- Pazar: 09:00

## 🛡️ Buybox Koruması

Sistem aşağıdaki yöntemlerle buybox'a takılmayı önler:

1. **Rastgele Başlık Prefix'leri**: Her ürün için benzersiz prefix
2. **Hash Tabanlı Markalar**: Ürün bazlı benzersiz marka kodları
3. **Gelişmiş Kategori Yapısı**: Rastgele alt kategoriler
4. **Benzersiz Resim URL'leri**: Çoklu parametreler
5. **Sentetik Barkodlar**: Çakışma önleyen benzersiz kodlar

## 📁 Dosya Yapısı

```
trendyol/
├── .github/workflows/
│   └── publish-feed.yml          # GitHub Actions workflow
├── data/
│   ├── source.xml               # Kaynak feed
│   ├── source_chekich.xml       # WG ürünleri filtrelenmiş
│   └── chekich21_*.xml          # Çıktı dosyaları
├── convert_to_stockmount.py     # Ana dönüşüm script'i
├── strengthen_buybox_protection.py # Buybox koruması
├── remove_wg_products.py        # Ürün filtreleme
├── fix_duplicate_barcodes.py    # Barkod düzeltme
└── README.md                    # Bu dosya
```

## 🔍 Sorun Giderme

### Yaygın Hatalar

1. **"SOURCE_FEED_URL secret tanımlı değil"**
   - GitHub repository secrets'ına SOURCE_FEED_URL ekleyin
   - Veya varsayılan data/source.xml dosyasını kullanın

2. **Buybox'a takılma**
   - `strengthen_buybox_protection.py` script'ini çalıştırın
   - Workflow otomatik olarak bu korumayı uygular

3. **Barkod çakışması**
   - `fix_duplicate_barcodes.py` script'ini kullanın
   - `--barcode-strategy synthetic` parametresi ile otomatik önleme

### Log'ları İnceleme

GitHub Actions sekmesinden workflow çalıştırma log'larını inceleyin.

## 📈 İstatistikler

- **Aktif Ürün**: ~150+ ürün
- **Günlük Güncellemeler**: Hafta içi 15-16, hafta sonu 1'er
- **Buybox Koruması**: %100 benzersiz ürün tanımlayıcıları

## 🤝 Katkıda Bulunma

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Pull Request oluşturun

## 📄 Lisans

Bu proje özel kullanım içindir.

## 📞 İletişim

Sorularınız için repository issues'ını kullanın.