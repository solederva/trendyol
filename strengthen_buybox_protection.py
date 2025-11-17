import xml.etree.ElementTree as ET
import random
import string
import hashlib
import logging
from pathlib import Path
from urllib.parse import urlencode

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('buybox_protection.log'),
        logging.StreamHandler()
    ]
)

def generate_random_prefix(length=6):
    """Rastgele prefix üret"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def generate_unique_brand(product_code, name, brand_src):
    """Markayı sabit SDSTEP olarak tut"""
    return "SDSTEP"

def generate_random_title_prefix():
    """Rastgele başlık prefix'i üret - daha agresif"""
    prefixes = [
        "Premium", "Elite", "Luxury", "Classic", "Modern", "Style",
        "Trend", "Fashion", "Comfort", "Quality", "Best", "Top",
        "Exclusive", "Signature", "Ultimate", "Supreme", "Prime",
        "Select", "Choice", "Preferred", "Superior", "Excellent"
    ]
    # Daha uzun ve değişken suffix
    suffix = generate_random_prefix(random.randint(6, 10))
    return f"{random.choice(prefixes)}-{suffix}"

def generate_rotating_brand(product_code, timestamp):
    """Markayı rotasyona sok - her çalıştırmada farklı"""
    brands = ["SDSTEP", "SD-STEP", "SD STEP", "SDSTEP™", "SDSTEP®"]
    # Timestamp'a göre deterministik seçim
    brand_index = hash(timestamp + product_code) % len(brands)
    return brands[brand_index]

def apply_price_manipulation(price_elem, product_code):
    """Fiyata çok küçük manipülasyon uygula"""
    if price_elem is not None and price_elem.text:
        try:
            price = float(price_elem.text)
            # Manipülasyonu ürün koduna göre deterministik yap
            seed = hash(product_code) % 1000
            random.seed(seed)
            manipulation = random.uniform(-0.99, 0.99)
            new_price = round(price + manipulation, 2)
            # Negatif fiyat olmasın
            new_price = max(0.01, new_price)
            price_elem.text = f"{new_price:.2f}"
        except (ValueError, AttributeError):
            pass

def rotate_barcode(barcode_elem, product_code, timestamp):
    """Barkodu her çalıştırmada değiştir"""
    if barcode_elem is not None and barcode_elem.text:
        current_barcode = barcode_elem.text.strip()
        if current_barcode:
            # Timestamp ile yeni hash üret
            new_seed = f"{product_code}_{timestamp}_{current_barcode}"
            new_hash = hashlib.md5(new_seed.encode()).hexdigest()[:12]
            # 2199 prefix ile yeni barkod
            new_barcode = f"2199{new_hash}"
            # EAN-13 check digit hesapla
            def ean_check(num12: str) -> str:
                total = 0
                for idx, c in enumerate(num12):
                    n = int(c)
                    if (idx + 1) % 2 == 0:
                        total += n * 3
                    else:
                        total += n
                return str((10 - (total % 10)) % 10)
            if len(new_barcode) == 12:
                check_digit = ean_check(new_barcode)
                new_barcode += check_digit
            barcode_elem.text = new_barcode

def modify_xml_for_buybox_protection(input_file: str, output_file: str):
    """XML'i buybox koruması için değiştir"""
    try:
        logging.info(f"XML işleme başlıyor: {input_file}")
        tree = ET.parse(input_file)
        root = tree.getroot()

        # Timestamp for deterministic but rotating values
        import time
        current_timestamp = str(int(time.time()))

        product_count = 0
        repo_raw_base = "https://raw.githubusercontent.com/solederva/trendyol/main/"
        processed_dir = Path("data/processed_images")
        for product in root.findall("Product"):
            try:
                product_code = product.find("ProductCode").text.strip() if product.find("ProductCode") is not None else ""
                product_name = product.find("ProductName").text.strip() if product.find("ProductName") is not None else ""
                brand_elem = product.find("Brand")
                brand_src = brand_elem.text.strip() if brand_elem is not None and brand_elem.text else "SDSTEP"

                # 1. MARKA ROTASYONU - Her çalıştırmada farklı marka kullan
                if brand_elem is not None:
                    brand_elem.text = generate_rotating_brand(product_code, current_timestamp)

                # 2. BAŞLIK MANİPÜLASYONU - Daha agresif prefix'ler
                if product.find("ProductName") is not None:
                    random_prefix = generate_random_title_prefix()
                    current_name = product.find("ProductName").text
                    # Eğer zaten prefix varsa değiştir, yoksa ekle
                    if " | " in current_name:
                        base_name = current_name.split(" | ", 1)[1]
                        new_name = f"{random_prefix} | {base_name}"
                    else:
                        new_name = f"{random_prefix} | {current_name}"
                    product.find("ProductName").text = new_name

                # 3. FİYAT MANİPÜLASYONU - Çok küçük farklarla değiştir
                price_elem = product.find("Price")
                apply_price_manipulation(price_elem, product_code)

                # 4. BARKOD ROTASYONU - Her çalıştırmada farklı barkod
                barcode_elem = product.find("Barcode")
                rotate_barcode(barcode_elem, product_code, current_timestamp)

                # Varyant barkodlarını da döndür
                variants = product.find("Variants")
                if variants is not None:
                    for variant in variants.findall("Variant"):
                        variant_barcode = variant.find("Barcode")
                        if variant_barcode is not None:
                            variant_code = variant.find("VariantCode")
                            variant_id = variant_code.text if variant_code is not None else f"{product_code}_variant"
                            rotate_barcode(variant_barcode, variant_id, current_timestamp)
                if product.find("ProductName") is not None:
                    random_prefix = generate_random_title_prefix()
                    current_name = product.find("ProductName").text
                    # Eğer zaten prefix varsa değiştir, yoksa ekle
                    if " | " in current_name:
                        base_name = current_name.split(" | ", 1)[1]
                        new_name = f"{random_prefix} | {base_name}"
                    else:
                        new_name = f"{random_prefix} | {current_name}"
                    product.find("ProductName").text = new_name

                # 3. Kategori bilgisini değiştir (rastgele alt kategori ekle)
                if product.find("Category") is not None:
                    current_category = product.find("Category").text
                    # CDATA içinden çıkar
                    current_category = current_category.replace("&gt;", ">").replace("&lt;", "<")
                    if ">" in current_category:
                        parts = current_category.split(">")
                        if len(parts) >= 2:
                            # Rastgele alt kategori ekle
                            sub_categories = ["Premium", "Comfort", "Sport", "Casual", "Classic", "Modern"]
                            random_sub = random.choice(sub_categories)
                            parts.insert(-1, random_sub)
                            new_category = " > ".join(parts)
                            product.find("Category").text = new_category

                # 4. Açıklamaya benzersiz gizli element ekle
                if product.find("Description") is not None:
                    desc = product.find("Description").text or ""
                    unique_id = generate_random_prefix(16)
                    hidden_element = f'<p style="display:none;">SDSTEP-{unique_id}</p>'
                    # Eğer zaten gizli element varsa değiştir
                    if '<p style="display:none;">' in desc:
                        desc = desc.split('<p style="display:none;">')[0] + hidden_element
                    else:
                        desc += hidden_element
                    product.find("Description").text = desc

                # 5. RESİMLERİ KALDIR - Buybox resim taramasını önle
                # Trendyol resimleri tarayıp aynı resimleri buybox'a dahil ediyor
                # Çözüm: Tüm resimleri kaldır - eksik resim buybox'a girmeyi önler
                for i in range(1, 6):
                    tag = f"Image{i}"
                    img_elem = product.find(tag)
                    if img_elem is not None:
                        # Resim elementini tamamen kaldır
                        product.remove(img_elem)
                        logging.debug(f"Resim kaldırıldı: {tag} for product {product_code}")

                product_count += 1

            except Exception as e:
                logging.error(f"Ürün işleme hatası: {e}")
                continue

        # XML'i kaydet
        tree.write(output_file, encoding="utf-8", xml_declaration=True)
        logging.info(f"İşlem tamamlandı: {product_count} ürün işlendi, çıktı: {output_file}")

    except Exception as e:
        logging.error(f"XML işleme hatası: {e}")
        raise

if __name__ == "__main__":
    input_file = "data/chekich21_synthetic_bullets_titled_nobrand.xml"
    output_file = "data/chekich21_synthetic_bullets_titled_nobrand.xml"  # Aynı dosyaya yaz

    try:
        modify_xml_for_buybox_protection(input_file, output_file)
        logging.info("Buybox koruması başarıyla güçlendirildi.")
    except Exception as e:
        logging.error(f"Script hatası: {e}")
        exit(1)
