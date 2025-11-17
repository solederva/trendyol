# Trendyol Stockmount Feed Manager

Bu proje, Trendyol e-ticaret platformu için otomatik ürün feed yönetimi sağlar. Kaynak XML verilerini Stockmount formatına dönüştürür ve fiyat/stok güncellemelerini otomatik olarak gerçekleştirir.

## 🚀 Özellikler

- **Otomatik Feed Dönüşümü**: Kaynak XML → Stockmount XML
- **Buybox Koruması**: Rastgele prefix'ler ve benzersiz markalar ile buybox'a takılmayı önler
- **Benzersiz Barkod Üretimi**: Çakışma önlemek için hash tabanlı sentetik barkodlar
- **Otomatik Güncellemeler**: GitHub Actions ile 30 dakikalık periyotlarda (08:00-18:00 arası)
- **Varyant Desteği**: Renk ve beden varyantlarını işler
- **Resim URL Temizleme**: Benzersiz parametreler ile buybox eşleşmesini önler
- **Temiz Repository**: Gereksiz dosyalar kaldırılmış, sadece üretim dosyaları mevcut

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
# Harici bağımlılık yok - sadece standart kütüphaneler kullanılıyor
```

## 📊 Kullanım

### Manuel Dönüşüm

```bash
# Temel dönüşüm
python convert_to_stockmount.py \
  --input data/source_chekich.xml \
  --output data/output.xml \
  --variant-mode \
  --barcode-strategy synthetic \
  --barcode-prefix "2199" \
  --add-bullets \
  --title-template "Solederva {URUN} {RENK} - {MODEL}" \
  --brand-override SDSTEP \
  --sanitize-images
```

### Otomatik İşlem Akışı

1. **Kaynak Feed İndirme**: `SOURCE_FEED_URL` secret'ından XML indirilir
2. **WG Ürün Filtreleme**: `remove_wg_products.py` ile WG ürünleri çıkarılır
3. **Stockmount Dönüşümü**: Ana conversion script'i çalıştırılır
4. **Buybox Koruması**: Rastgele prefix'ler ve benzersiz parametreler eklenir
5. **Git Commit**: Değişiklikler otomatik olarak commit edilir

### Dosya Yapısı

```
trendyol/
├── convert_to_stockmount.py          # Ana dönüşüm script'i
├── strengthen_buybox_protection.py   # Buybox koruma script'i
├── remove_wg_products.py             # WG ürün filtreleme
├── fix_duplicate_barcodes.py         # Barkod düzeltme (yedek)
├── product_codes_to_delete.txt       # Silinecek ürün listesi
├── data/
│   ├── source.xml                    # Kaynak feed (otomatik indirilir)
│   ├── source_chekich.xml            # WG ürünleri filtrelenmiş
│   └── chekich21_synthetic_bullets_titled_nobrand.xml  # Final feed
├── .github/workflows/
│   └── publish-feed.yml              # Otomatik workflow
├── .gitignore                        # Git ignore kuralları
└── README.md                         # Bu dokümantasyon
```

## ⚙️ Konfigürasyon

### GitHub Secrets

- `SOURCE_FEED_URL`: Kaynak XML feed'in URL'i
- `GITHUB_TOKEN`: Repository yazma izni için (otomatik)

### Workflow Zamanlaması

- **Hafta içi**: 08:00-18:00 arası her 30 dakikada (21 güncelleme/gün)
- **Hafta sonu**: 08:00-18:00 arası her 30 dakikada (21 güncelleme/gün)
- **Toplam**: Haftada 147 otomatik güncelleme

## 🔧 Gelişmiş Kullanım

### Sadece Dönüşüm (Buybox Koruması Olmadan)

```bash
python convert_to_stockmount.py \
  --input data/source_chekich.xml \
  --output data/output.xml \
  --variant-mode
```

### Sadece Buybox Koruması

```bash
python strengthen_buybox_protection.py
```

### Log Dosyaları

- `conversion.log`: Dönüşüm işlemleri
- `buybox_protection.log`: Buybox koruma işlemleri

## 📈 İstatistikler

- **157 ürün** işleniyor
- **3 kategori**: SPOR AYAKKABI, DERİ AYAKKABI, BOT
- **Varyant sayısı**: Renk + Beden kombinasyonları
- **Güncelleme sıklığı**: 30 dakikada bir (çalışma saatleri)
- **Feed URL**: https://raw.githubusercontent.com/solederva/trendyol/main/data/chekich21_synthetic_bullets_titled_nobrand.xml

## 🐛 Sorun Giderme

### Workflow Başarısız Olursa

1. GitHub Actions loglarını kontrol edin
2. Kaynak feed URL'inin geçerli olduğunu doğrulayın
3. Disk alanının yeterli olduğunu kontrol edin

### Stok Uyumsuzluğu

- Kaynak feed'in güncel olup olmadığını kontrol edin
- Workflow'un son çalıştığı zamanı kontrol edin
- Manuel güncelleme için workflow'u trigger edin

## 📝 Notlar

- Repository düzenli olarak temizlenir (gereksiz dosyalar kaldırılır)
- Sadece üretim için gerekli dosyalar tutulur
- Otomatik commit'ler "chore(feed):" prefix'i ile yapılır
- Buybox koruması için benzersiz parametreler kullanılır
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

- `SOURCE_FEED_URL`: Kaynak XML feed'in URL'i
- `GITHUB_TOKEN`: Repository yazma izni için (otomatik)

### Workflow Zamanlaması

- **Hafta içi**: 08:00-18:00 arası her 30 dakikada (21 güncelleme/gün)
- **Hafta sonu**: 08:00-18:00 arası her 30 dakikada (21 güncelleme/gün)
- **Toplam**: Haftada 147 otomatik güncelleme

## 🔧 Gelişmiş Kullanım

### Sadece Dönüşüm (Buybox Koruması Olmadan)

```bash
python convert_to_stockmount.py \
  --input data/source_chekich.xml \
  --output data/output.xml \
  --variant-mode
```

### Sadece Buybox Koruması

```bash
python strengthen_buybox_protection.py
```

### Log Dosyaları

- `conversion.log`: Dönüşüm işlemleri
- `buybox_protection.log`: Buybox koruma işlemleri

## 📈 İstatistikler

- **157 ürün** işleniyor
- **3 kategori**: SPOR AYAKKABI, DERİ AYAKKABI, BOT
- **Varyant sayısı**: Renk + Beden kombinasyonları
- **Güncelleme sıklığı**: 30 dakikada bir (çalışma saatleri)
- **Feed URL**: https://raw.githubusercontent.com/solederva/trendyol/main/data/chekich21_synthetic_bullets_titled_nobrand.xml

## 🐛 Sorun Giderme

### Workflow Başarısız Olursa

1. GitHub Actions loglarını kontrol edin
2. Kaynak feed URL'inin geçerli olduğunu doğrulayın
3. Disk alanının yeterli olduğunu kontrol edin

### Stok Uyumsuzluğu

- Kaynak feed'in güncel olup olmadığını kontrol edin
- Workflow'un son çalıştığı zamanı kontrol edin
- Manuel güncelleme için workflow'u trigger edin

## 📝 Notlar

- Repository düzenli olarak temizlenir (gereksiz dosyalar kaldırılır)
- Sadece üretim için gerekli dosyalar tutulur
- Otomatik commit'ler "chore(feed):" prefix'i ile yapılır
- Buybox koruması için benzersiz parametreler kullanılır

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