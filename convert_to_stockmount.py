import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

# Kaynak alan -> Stockmount alan mapping açıklaması:
# Product_code -> ProductCode (ürün ana kodu)
# Name -> ProductName
# Stock (toplam) -> Quantity (varyantsız modda veya fallback)
# Price -> Price
# CurrencyType -> Currency (TRL -> TL dönüştürülür)
# Tax -> TaxRate
# Barcode (ürün genel barkod) -> Barcode (yoksa ilk variant barkodu kullanılabilir)
# Kategori hiyerarşisi: mainCategory > category > subCategory -> Category ( > ile birleştirilmiş)
# Description -> Description (HTML olduğundan CDATA korunacak)
# Image1..Image5 -> Image1..Image5
# Brand -> Brand
# Model (kaynakta yok) -> Model (boş bırakılır)
# buying_price kullanılmıyor (isteğe göre maliyet için tutulabilir, şimdilik atla)
# Volume (kaynakta yok) -> Volume (opsiyonel, yoksa yazma)
# Variant yapısı:
#   Kaynak: variants/variant/spec[@name='Renk'] -> VariantName1=Renk VariantValue1=değer
#            spec[@name='Beden'] -> VariantName2=Beden VariantValue2=değer
#   variant/productCode veya variant/barcode alanı -> VariantCode (öncelik variant/barcode, boşsa productCode)
#   variant/quantity -> VariantQuantity
#   variant/price (0.00 ise ana ürün Price kullanılabilir) -> VariantPrice
# Not: Varyantlı modda ana <Quantity> toplam variant quantity toplamı olabilir, ya da ilk varyant quantity'si. Örnekten bağımsız toplamı kullanıyoruz.

CURRENCY_MAP = {"TRL": "TL", "TRY": "TL", "TL": "TL"}

def text(elem: Optional[ET.Element]) -> str:
    return elem.text.strip() if elem is not None and elem.text else ""

def build_category(product: ET.Element) -> str:
    parts = []
    for tag in ["mainCategory", "category", "subCategory"]:
        val = text(product.find(tag))
        if val:
            parts.append(val)
    return " > ".join(parts)

def extract_images(product: ET.Element):
    images = {}
    for i in range(1, 6):
        tag = f"Image{i}"
        images[tag] = text(product.find(tag))
    return images

def parse_variants(product: ET.Element):
    variants_parent = product.find("variants")
    if variants_parent is None:
        return []
    out = []
    for v in variants_parent.findall("variant"):
        specs = {s.get("name"): (s.text or "").strip() for s in v.findall("spec")}
        renk = specs.get("Renk", "")
        beden = specs.get("Beden", "")
        quantity = text(v.find("quantity")) or "0"
        price_raw = text(v.find("price"))
        barcode_val = text(v.find("barcode")) or text(v.find("productCode")) or text(v.find("variantId"))
        out.append({
            "raw_barcode": barcode_val,
            "renk": renk,
            "beden": beden,
            "quantity": quantity,
            "price": price_raw,
        })
    return out

def convert_product(product: ET.Element, variant_mode: bool):
    product_code = text(product.find("Product_code")) or text(product.find("Product_id"))
    name = text(product.find("Name"))
    total_stock = text(product.find("Stock"))
    price = text(product.find("Price"))
    currency = CURRENCY_MAP.get(text(product.find("CurrencyType")) or "", "TL")
    tax = text(product.find("Tax"))
    barcode = text(product.find("Barcode"))
    description_elem = product.find("Description")
    description = description_elem.text if description_elem is not None and description_elem.text else ""
    category_path = build_category(product)
    images = extract_images(product)
    # Marka override talebi: tüm ürünlerde 'solederva'
    brand = "solederva"

    raw_variants = parse_variants(product)
    has_variants = variant_mode and len(raw_variants) > 0

    variants_output = []
    if has_variants:
        from collections import defaultdict
        def append_suffix(code: str) -> str:
            if not code:
                return code
            return code if code.endswith("21") else code + "21"

        renk_groups = defaultdict(list)
        for rv in raw_variants:
            renk_groups[rv["renk"].strip()].append(rv)
        renk_index_map = {renk: str(idx + 1) for idx, renk in enumerate(sorted(renk_groups.keys()))}

        for rv in raw_variants:
            renk = rv["renk"].strip()
            beden = rv["beden"].strip()
            group_idx = renk_index_map.get(renk, "1")
            # Öncelik: variant barkodu varsa onu (21 eklenmiş) VariantCode yap.
            base_variant_barcode = rv["raw_barcode"].strip()
            # VariantCode üretim fallback zinciri:
            # 1) base_variant_barcode (+21) varsa onu kullan
            # 2) Yoksa ProductCode + '_' + groupIdx + (beden varsa '_' + beden) kombinasyonu
            if base_variant_barcode:
                vcode = append_suffix(base_variant_barcode)
            else:
                comp = f"{product_code}_{group_idx}"
                if beden:
                    comp += f"_{beden}"
                vcode = comp
            vprice = rv["price"].strip()
            if not vprice or vprice in {"0", "0.0", "0.00"}:
                vprice = price
            qty_raw = rv["quantity"].strip()
            try:
                qty_int = int(float(qty_raw)) if qty_raw else 0
            except ValueError:
                qty_int = 0
            if qty_int < 0:
                qty_int = 0
            variants_output.append({
                "VariantCode": vcode,
                "VariantQuantity": str(qty_int),
                "VariantPrice": vprice,
                "VariantName1": "Renk" if renk else "",
                "VariantValue1": renk,
                "VariantName2": "Beden" if beden else "",
                "VariantValue2": beden,
            })
        quantity = str(sum(int(v.get("VariantQuantity", "0")) for v in variants_output))
    else:
        quantity = total_stock or "0"

    # Barkod kuralı: Ürün barkodu boş ise ilk varyant barkodu kullanılabilir.
    # Sonuna '21' eklenecek (eğer zaten 21 ile bitmiyorsa).
    def append_suffix(code: str) -> str:
        if not code:
            return code
        return code if code.endswith("21") else code + "21"

    if not barcode:
        # İlk anlamlı variant barkodu (raw_barcode) kullan
        for rv in raw_variants:
            if rv.get("raw_barcode"):
                barcode = rv["raw_barcode"]
                break
    barcode = append_suffix(barcode)

    prod_data = {
        "ProductCode": product_code,
        "ProductName": name,
        "Quantity": quantity,
        "Price": price,
        "Currency": currency,
        "TaxRate": tax,
        "Barcode": barcode,
        "Category": category_path,
        "Description": description,
        "Brand": brand,
        "Model": "",
        "Volume": "",
        "Images": images,
        "Variants": variants_output if has_variants else []
    }
    return prod_data


def build_stockmount_xml(products_data):
    root = ET.Element("Products")
    for pdata in products_data:
        p_el = ET.SubElement(root, "Product")
        def se(tag, value):
            el = ET.SubElement(p_el, tag)
            if value:
                el.text = value
        se("ProductCode", pdata["ProductCode"])        
        se("ProductName", pdata["ProductName"])        
        se("Quantity", pdata["Quantity"])              
        se("Price", pdata["Price"])                    
        se("Currency", pdata["Currency"])              
        se("TaxRate", pdata["TaxRate"])               
        se("Barcode", pdata["Barcode"])               
        # Category + Description CDATA için manuel ekleme gerekecek, önce placeholder
        cat_el = ET.SubElement(p_el, "Category")
        desc_el = ET.SubElement(p_el, "Description")
        # Images
        for i in range(1, 6):
            tag = f"Image{i}"
            se(tag, pdata["Images"].get(tag))
        se("Brand", pdata["Brand"])                    
        se("Model", pdata["Model"])                    
        se("Volume", pdata["Volume"])                  
        if pdata["Variants"]:
            vars_el = ET.SubElement(p_el, "Variants")
            for v in pdata["Variants"]:
                v_el = ET.SubElement(vars_el, "Variant")
                for t in ["VariantCode","VariantQuantity","VariantPrice","VariantName1","VariantValue1","VariantName2","VariantValue2"]:
                    el = ET.SubElement(v_el, t)
                    if v[t]:
                        el.text = v[t]
        # CDATA ekleme (ElementTree default desteklemediği için string post-process)
        cat_el.text = pdata["Category"]
        desc_el.text = pdata["Description"]
    return root


def serialize_with_cdata(root: ET.Element) -> str:
    # Önce düz serialize
    raw = ET.tostring(root, encoding="utf-8").decode("utf-8")
    import re, html

    # Category ve Description içeriklerini orijinal HTML'e geri döndür (escape kaldır) ve CDATA ile sar
    def repl(m):
        tag = m.group(1)
        content = m.group(2)
        if not content.strip():
            return f"<{tag}></{tag}>"
        unescaped = html.unescape(content)
        return f"<{tag}><![CDATA[{unescaped}]]></{tag}>"

    raw = re.sub(r"<(Category|Description)>(.*?)</\\1>", repl, raw, flags=re.DOTALL)

    # Pretty print: ek olarak her kapanıştan sonra newline yerleştir
    # Çok büyük dosya olduğundan minimal pretty (></Product><Product -> >\n</Product>\n<Product)
    raw = raw.replace('</Product><Product>', '</Product>\n  <Product>')
    raw = raw.replace('<Products><Product>', '<Products>\n  <Product>')
    raw = raw.replace('</Product></Products>', '</Product>\n</Products>')

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + raw + '\n'


def main():
    parser = argparse.ArgumentParser(description="Kaynak XML'i Stockmount formatına dönüştür")
    parser.add_argument("--input", required=True, help="Kaynak XML dosyası (standart.xml)")
    parser.add_argument("--output", required=True, help="Oluşacak Stockmount XML dosyası")
    parser.add_argument("--variant-mode", action="store_true", help="Varyantları yaz (varsayılan kapalı)")
    args = parser.parse_args()

    source_path = Path(args.input)
    if not source_path.is_file():
        print(f"Kaynak dosya bulunamadı: {source_path}", file=sys.stderr)
        sys.exit(1)

    tree = ET.parse(str(source_path))
    root = tree.getroot()

    products_data = []
    for product in root.findall("Product"):
        pdata = convert_product(product, variant_mode=args.variant_mode)
        products_data.append(pdata)

    out_root = build_stockmount_xml(products_data)
    xml_str = serialize_with_cdata(out_root)
    Path(args.output).write_text(xml_str, encoding="utf-8")
    print(f"Olusturuldu: {args.output} ({len(products_data)} ürün)")

if __name__ == "__main__":
    main()
