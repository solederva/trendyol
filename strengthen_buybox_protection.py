import xml.etree.ElementTree as ET
import random
import string
import hashlib
import logging
from pathlib import Path

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
    """Rastgele başlık prefix'i üret"""
    prefixes = [
        "Premium", "Elite", "Luxury", "Classic", "Modern", "Style",
        "Trend", "Fashion", "Comfort", "Quality", "Best", "Top"
    ]
    suffix = generate_random_prefix(4)
    return f"{random.choice(prefixes)}-{suffix}"

def modify_xml_for_buybox_protection(input_file: str, output_file: str):
    """XML'i buybox koruması için değiştir"""
    try:
        logging.info(f"XML işleme başlıyor: {input_file}")
        tree = ET.parse(input_file)
        root = tree.getroot()

        product_count = 0
        for product in root.findall("Product"):
            try:
                product_code = product.find("ProductCode").text.strip() if product.find("ProductCode") is not None else ""
                product_name = product.find("ProductName").text.strip() if product.find("ProductName") is not None else ""
                brand_elem = product.find("Brand")
                brand_src = brand_elem.text.strip() if brand_elem is not None and brand_elem.text else "SDSTEP"

                # 1. Markayı SDSTEP olarak ayarla (hash'siz)
                if brand_elem is not None:
                    brand_elem.text = "SDSTEP"

                # 2. Başlığa rastgele prefix ekle
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

                # 5. Resim URL'lerine ekstra rastgele parametreler ekle
                for i in range(1, 6):
                    img_tag = f"Image{i}"
                    img_elem = product.find(img_tag)
                    if img_elem is not None and img_elem.text:
                        url = img_elem.text
                        if "?" in url:
                            url += f"&rnd={generate_random_prefix(8)}&brand=SDSTEP"
                        else:
                            url += f"?rnd={generate_random_prefix(8)}&brand=SDSTEP"
                        img_elem.text = url

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
