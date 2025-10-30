import xml.etree.ElementTree as ET
import hashlib
import re
from pathlib import Path

def generate_unique_barcode(base: str, prefix: str = "2199", length: int = 13) -> str:
    """Benzersiz sentetik barkod üret. Base farklı olursa farklı barkod."""
    if length < 8:
        length = 8
    h = hashlib.sha256(base.encode("utf-8")).hexdigest()
    digits = ''.join(str(int(ch, 16) % 10) for ch in h)
    core = (prefix + digits)[:length-1]
    # EAN-13 check digit
    def ean_check(num12: str) -> str:
        total = 0
        for idx, c in enumerate(num12):
            n = int(c)
            if (idx + 1) % 2 == 0:
                total += n * 3
            else:
                total += n
        return str((10 - (total % 10)) % 10)
    if length >= 12 and core.isdigit():
        check = ean_check(core[:length-1])
        return core[:length-1] + check
    return core.ljust(length, '0')

def fix_barcodes_in_xml(input_file: str, output_file: str):
    tree = ET.parse(input_file)
    root = tree.getroot()

    used_barcodes = set()

    for product in root.findall("Product"):
        product_code = product.find("ProductCode").text.strip() if product.find("ProductCode") is not None else ""
        product_name = product.find("ProductName").text.strip() if product.find("ProductName") is not None else ""
        brand = product.find("Brand").text.strip() if product.find("Brand") is not None else ""

        # Ürün barkodu
        product_base = f"{product_code}_{product_name}_{brand}"
        new_product_barcode = generate_unique_barcode(product_base)
        while new_product_barcode in used_barcodes:
            new_product_barcode = generate_unique_barcode(product_base + str(len(used_barcodes)))
        used_barcodes.add(new_product_barcode)
        if product.find("Barcode") is not None:
            product.find("Barcode").text = new_product_barcode

        # Varyant barkodları
        variants = product.find("Variants")
        if variants is not None:
            for variant in variants.findall("Variant"):
                variant_code = variant.find("VariantCode").text.strip() if variant.find("VariantCode") is not None else ""
                renk = ""
                beden = ""
                for i in range(1, 3):
                    name_tag = variant.find(f"VariantName{i}")
                    value_tag = variant.find(f"VariantValue{i}")
                    if name_tag is not None and value_tag is not None:
                        if name_tag.text == "Renk":
                            renk = value_tag.text or ""
                        elif name_tag.text == "Beden":
                            beden = value_tag.text or ""

                variant_base = f"{product_code}_{variant_code}_{renk}_{beden}"
                new_variant_barcode = generate_unique_barcode(variant_base, prefix="2198")  # Farklı prefix varyantlar için
                while new_variant_barcode in used_barcodes:
                    new_variant_barcode = generate_unique_barcode(variant_base + str(len(used_barcodes)), prefix="2198")
                used_barcodes.add(new_variant_barcode)
                if variant.find("Barcode") is not None:
                    variant.find("Barcode").text = new_variant_barcode

    # XML'i kaydet
    tree.write(output_file, encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    input_file = "data/chekich21_synthetic_bullets_titled_nobrand.xml"
    output_file = "data/chekich21_synthetic_bullets_titled_nobrand.xml"  # Aynı dosyaya yaz
    fix_barcodes_in_xml(input_file, output_file)
    print("Barkodlar düzeltildi ve benzersiz yapıldı.")