import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional
import hashlib
import re

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

def normalize_variant_color(value: str) -> str:
    """Renk normalizasyonu:
    - Parantez içi kodları kaldır: "ANTRASIT-BYZ(57-10)" -> "ANTRASIT-BYZ"
    - "/" çevresini '-' yap: "BEYAZ / SAX MAVI" -> "BEYAZ-SAX MAVI"
    - Yaygın kısaltmaları genişlet: BYZ->BEYAZ, SYH->SIYAH, SAX->SAKS, LAC->LACIVERT, vb.
    - Boşlukları sadeleştir, tire etrafındaki boşlukları temizle.
    """
    import re
    s = (value or "").strip()
    if not s:
        return s
    # Büyük harfe çevir (eşleştirmeyi kolaylaştırmak için)
    s = s.upper()
    # Parantez içi tüm içerikleri temizle (sondaki varyant kodları vs.)
    s = re.sub(r"\s*\([^)]*\)", "", s)
    # "/" -> "-" (çevresindeki boşluklarla)
    s = re.sub(r"\s*/\s*", "-", s)
    # Tire etrafındaki boşlukları kaldır
    s = re.sub(r"\s*-\s*", "-", s)
    # Fazla boşlukları sadeleştir
    s = re.sub(r"\s+", " ", s).strip()

    # Kısaltma eşleştirme tablosu
    mapping = {
        "SYH": "SIYAH",
        "SİYAH": "SIYAH",  # olası i varyasyonu
        "BYZ": "BEYAZ",
        "BLC": "SIYAH",  # olası yabancı kısaltma (black)
        "BLK": "SIYAH",
        "LAC": "LACIVERT",
        "LACI": "LACIVERT",
        "LACV": "LACIVERT",
        "ANTR": "ANTRASIT",
        "ANT": "ANTRASIT",
        "HKI": "HAKI",
        "HAK": "HAKI",
        "KRMZ": "KIRMIZI",
        "KRM": "KIRMIZI",
        "MAV": "MAVI",
        "SAX": "SAKS",
        "KAHVE": "KAHVERENGI",
    }

    # Yalnızca harf/rakam gruplarını hedefleyerek kısaltmaları genişlet
    def repl_token(m):
        tok = m.group(0)
        return mapping.get(tok, tok)

    s = re.sub(r"[A-Z0-9]+", repl_token, s)

    # Son temizlik (çift tire, baş/son tire vs.)
    s = re.sub(r"-+", "-", s)
    s = s.strip(" -")
    return s

def normalize_product_code_prefix(value: str) -> str:
    """ProductCode başı 'MN' ise 'SD' ile değiştir."""
    if not value:
        return value
    v = value.strip()
    if v.upper().startswith("MN"):
        return "SD" + v[2:]
    return v

def parse_variants(product: ET.Element):
    variants_parent = product.find("variants")
    if variants_parent is None:
        return []
    out = []
    for v in variants_parent.findall("variant"):
        specs = {s.get("name"): (s.text or "").strip() for s in v.findall("spec")}
        renk = normalize_variant_color(specs.get("Renk", ""))
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

def generate_synthetic_barcode(base: str, prefix: str, length: int = 13) -> str:
    """Deterministik sentetik barkod üret. EAN-13 formatına benzeyecek şekilde prefix + hash.
    Not: Gerçek GS1 barkodu olmayabilir; buybox eşleşmesinden kaçınma amaçlıdır.
    length parametresi minimum 8 kabul edilir; varsayılan 13.
    """
    if length < 8:
        length = 8
    # Hash'ten numerik dizi elde et
    h = hashlib.sha256(base.encode("utf-8")).hexdigest()
    digits = ''.join(str(int(ch, 16) % 10) for ch in h)
    core = (prefix + digits)
    core = core[:length-1]  # son haneyi check digit için ayır
    # Basit EAN-13 benzeri check digit hesapla (resmi olmayabilir ama format hissi verir)
    def ean_check(num12: str) -> str:
        total = 0
        for idx, c in enumerate(num12):
            n = int(c)
            if (idx + 1) % 2 == 0:  # even position
                total += n * 3
            else:
                total += n
        return str((10 - (total % 10)) % 10)
    if length >= 12 and core.isdigit():
        check = ean_check(core[:length-1])
        return core[:length-1] + check
    # Fallback: core pad
    return core.ljust(length, '0')

def extract_features_for_bullets(name: str, description_html: str) -> list:
    """Basit kural tabanlı özellik çıkarımı. Daha gelişmiş regex eklenebilir."""
    feats = []
    lower = description_html.lower()
    if 'vegan' in lower:
        feats.append('Vegan Deri Malzeme')
    if 'ortopedik' in lower:
        feats.append('Ortopedik Destekli İç Taban')
    if 'pamuk' in lower:
        feats.append('Nefes Alabilir Pamuk Astar')
    if 'kaymaz' in lower:
        feats.append('Kaymaz Taban')
    if 'topuk' in lower:
        feats.append('Konfor Topuk Tasarımı')
    # Ürün adına göre ek örnek
    if 'loafer' in name.lower():
        feats.append('Loafer Günlük Kullanıma Uygun')
    # Tekrarları kaldır
    uniq = []
    for f in feats:
        if f not in uniq:
            uniq.append(f)
    return uniq[:6]

def build_bullet_block(features: list) -> str:
    if not features:
        return ''
    items = ''.join(f'<li>{f}</li>' for f in features)
    return f"<ul>{items}</ul>"

def apply_title_template(original_name: str, template: str) -> str:
    """Basit başlık şablonu uygular. Placeholderlar:
    {MARKA} {MODEL} {RENK} {URUN}
    MODEL: isimde ilk boşluk veya ilk '-' öncesi blok (alfanumerik kısım)
    RENK: son büyük harfli renk kelimesi (heuristic: SIYAH, BEYAZ vb) bulunamazsa boş
    URUN: model ve renk çıkarıldıktan sonra kalan orta kısım
    """
    name = original_name.strip()
    if not template:
        return name
    import re
    # MODEL bul
    model_match = re.match(r"([A-Z0-9]+)", name)
    model = model_match.group(1) if model_match else ""
    # Renk heuristik listesi
    renk_list = ["SIYAH","BEYAZ","LACIVERT","KAHVERENGI","GRI","YESIL","MAVI","KIRMIZI","SARI","TABA","HAKI"]
    renk = ""
    tokens = name.upper().split()
    for t in reversed(tokens):
        if t in renk_list:
            renk = t
            break
    # URUN kısmını türet
    # Orijinal adı parçala, model ve renk'i çıkar
    words = name.split()
    filtered = []
    skip_model_once = False
    skip_renk_once = False
    for w in words:
        wu = w.upper()
        if not skip_model_once and model and wu.startswith(model):
            skip_model_once = True
            continue
        if not skip_renk_once and renk and wu == renk:
            skip_renk_once = True
            continue
        filtered.append(w)
    urun = " ".join(filtered).strip()
    result = template.replace('{MARKA}', 'Solederva').replace('{MODEL}', model).replace('{RENK}', renk).replace('{URUN}', urun)
    # Çift boşlukları sadeleştir
    result = re.sub(r"\s+"," ", result).strip().strip('-').strip()
    return result

def sanitize_image_url(url: str) -> str:
    if not url:
        return url
    u = url.strip().strip('"').strip("'")
    # İç boşlukları %20 ile değiştir
    u = re.sub(r"\s+", "%20", u)
    return u

def cleanse_banned_terms(text_value: str, banned_map: dict) -> str:
    if not text_value:
        return text_value
    out = text_value
    for pat, repl in banned_map.items():
        out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    return out

def convert_product(product: ET.Element, variant_mode: bool, barcode_strategy: str, barcode_prefix: str, add_bullets: bool, title_template: str, brand_override: str = "", banned_map: dict = None, sanitize_images: bool = False):
    product_code_raw = text(product.find("Product_code")) or text(product.find("Product_id"))
    product_code = normalize_product_code_prefix(product_code_raw)
    name = text(product.find("Name"))
    total_stock = text(product.find("Stock"))
    price = text(product.find("buying_price")) or text(product.find("Price"))
    currency = CURRENCY_MAP.get(text(product.find("CurrencyType")) or "", "TL")
    tax = text(product.find("Tax"))
    barcode = text(product.find("Barcode"))
    description_elem = product.find("Description")
    description = description_elem.text if description_elem is not None and description_elem.text else ""
    category_path = build_category(product)
    images = extract_images(product)
    if sanitize_images:
        for k, v in list(images.items()):
            images[k] = sanitize_image_url(v)
    # Marka: kaynaktan ne gelirse onu kullan; boşsa 'Solederva' fallback; override varsa onu uygula
    brand_src = text(product.find("Brand"))
    brand = brand_src if brand_src else "Solederva"
    if brand_override:
        brand = brand_override

    # Ağırlık: boş veya geçersizse 2 olarak ayarla
    weight_raw = text(product.find("Weight")) or text(product.find("weight"))
    def norm_weight(val: str) -> str:
        try:
            if not val:
                return "2"
            w = float(val.replace(',', '.'))
            if w <= 0:
                return "2"
            return str(int(w)) if abs(w - int(w)) < 1e-6 else str(w)
        except Exception:
            return "2"
    weight = norm_weight(weight_raw)

    # Yasaklı kelime temizlikleri (Name & Description başta uygulanmalı ki title template sonrası da temiz olsun)
    if banned_map:
        name = cleanse_banned_terms(name, banned_map)
        description = cleanse_banned_terms(description, banned_map)

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
            # VariantCode artık barkoda bağımlı değil: ProductCode + renk + beden
            renk_part = renk.replace(' ', '') or 'RENK'
            beden_part = beden.replace(' ', '') or 'BEDEN'
            vcode = f"{product_code}-{renk_part}-{beden_part}".upper()
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
            # Varyant barkodu: stratejiye göre belirle
            v_barcode = rv.get("raw_barcode", "")
            if barcode_strategy == 'synthetic':
                base_for_hash_v = f"{product_code}|{renk}|{beden}|{vcode}|{v_barcode}"
                v_barcode = generate_synthetic_barcode(base_for_hash_v, prefix=barcode_prefix)
            variants_output.append({
                "VariantCode": vcode,
                "VariantQuantity": str(qty_int),
                "VariantPrice": vprice,
                "VariantName1": "Renk" if renk else "",
                "VariantValue1": renk,
                "VariantName2": "Beden" if beden else "",
                "VariantValue2": beden,
                "Barcode": v_barcode,
            })
        quantity = str(sum(int(v.get("VariantQuantity", "0")) for v in variants_output))
    else:
        quantity = total_stock or "0"

    # Barkod stratejisi uygulanıyor
    # keep: orijinal (dokunma)
    # blank: tamamen boş (Stockmount kabul ediyorsa)
    # synthetic: deterministik benzersiz üret
    original_barcode = barcode
    if barcode_strategy == 'blank':
        barcode = ''
    elif barcode_strategy == 'synthetic':
        base_for_hash = product_code or original_barcode or name
        barcode = generate_synthetic_barcode(base_for_hash, prefix=barcode_prefix)
    else:
        # keep -> orijinal barkod; eğer boşsa ilk variant raw_barcode fallback uygula
        if (not barcode or barcode.strip() == '') and raw_variants:
            for rv in raw_variants:
                rb = rv.get('raw_barcode')
                if rb:
                    barcode = rb.strip()
                    break

    # Bullet list ekleme (isteğe bağlı)
    if add_bullets:
        features = extract_features_for_bullets(name, description)
        bullet_html = build_bullet_block(features)
        if bullet_html and bullet_html not in description:
            description = bullet_html + " " + description

    # Title template uygula
    if title_template:
        transformed_name = apply_title_template(name, title_template)
    else:
        transformed_name = name

    prod_data = {
        "ProductCode": product_code,
        "ProductName": transformed_name,
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
    "Weight": weight,
        "Images": images,
        "Variants": variants_output if has_variants else []
    }
    return prod_data


def build_stockmount_xml(products_data, omit_brand: bool = False):
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
        # Category & Description placeholder elemanları (CDATA sonradan eklenecek)
        cat_el = ET.SubElement(p_el, "Category")
        desc_el = ET.SubElement(p_el, "Description")
        # Images
        for i in range(1, 6):
            tag = f"Image{i}"
            se(tag, pdata["Images"].get(tag))
        if not omit_brand:
            se("Brand", pdata["Brand"])                    
        se("Model", pdata["Model"])                    
        se("Volume", pdata["Volume"])                  
        se("Weight", pdata.get("Weight", "2"))        
        if pdata["Variants"]:
            vars_el = ET.SubElement(p_el, "Variants")
            for v in pdata["Variants"]:
                v_el = ET.SubElement(vars_el, "Variant")
                # Standart alanlar
                for t in ["VariantCode","VariantQuantity","VariantPrice","VariantName1","VariantValue1","VariantName2","VariantValue2"]:
                    el = ET.SubElement(v_el, t)
                    if v[t]:
                        el.text = v[t]
                # Barkod alanı (Stockmount bazı şemalarda Variant > Barcode bekleyebilir)
                barkod_val = v.get("Barcode", "")
                b_el = ET.SubElement(v_el, "Barcode")
                if barkod_val:
                    b_el.text = barkod_val
        # CDATA ekleme (ElementTree default desteklemediği için string post-process)
        # Placeholder işaretleri; gerçek CDATA son aşamada eklenecek
        cat_el.text = f"__CDATA_CAT_START__{pdata['Category']}__CDATA_CAT_END__"
        desc_el.text = f"__CDATA_DESC_START__{pdata['Description']}__CDATA_DESC_END__"
    return root


def serialize_with_cdata(root: ET.Element) -> str:
    """XML'i güzel biçimli (pretty) ve Category/Description alanlarını CDATA içinde üret."""
    import re, html
    try:
        # Python 3.9+ indent fonksiyonu
        ET.indent(root, space="  ", level=0)  # type: ignore[attr-defined]
    except Exception:
        # Eski sürüm fallback: manuel indent (gerekirse eklenebilir)
        pass

    raw = ET.tostring(root, encoding="utf-8").decode("utf-8")
    # Placeholder'ları yakala ve içeriği unescape ederek CDATA ile değiştir
    def repl_placeholder(pattern_token, tag_name):
        p = re.compile(fr"<{tag_name}>(.*?)</{tag_name}>", re.DOTALL)
        def inner(m):
            content = m.group(1)
            prefix_start = f"__CDATA_{pattern_token}_START__"
            prefix_end = f"__CDATA_{pattern_token}_END__"
            if not content.startswith(prefix_start) or not content.endswith(prefix_end):
                return m.group(0)
            inner_raw = content[len(prefix_start):-len(prefix_end)]
            unescaped = html.unescape(inner_raw)
            safe = unescaped.replace(']]>', ']]]]><![CDATA[>')
            return f"<{tag_name}><![CDATA[{safe}]]></{tag_name}>"
        return p.sub(inner, raw)

    raw = repl_placeholder('CAT', 'Category')
    raw = repl_placeholder('DESC', 'Description')

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + raw + ('\n' if not raw.endswith('\n') else '')


def main():
    parser = argparse.ArgumentParser(description="Kaynak XML'i Stockmount formatına dönüştür")
    parser.add_argument("--input", required=True, help="Kaynak XML dosyası (standart.xml)")
    parser.add_argument("--output", required=True, help="Oluşacak Stockmount XML dosyası")
    parser.add_argument("--variant-mode", action="store_true", help="Varyantları yaz (varsayılan kapalı)")
    parser.add_argument("--barcode-strategy", choices=["keep","blank","synthetic"], default="keep", help="Barkod kullanımı stratejisi")
    parser.add_argument("--barcode-prefix", default="2199", help="Sentetik barkod üretirken önek (synthetic modda)")
    parser.add_argument("--add-bullets", action="store_true", help="Description başına otomatik özellik listesi ekle")
    parser.add_argument("--title-template", default="", help="Başlık şablonu (örn: {MARKA} {URUN} {RENK} - {MODEL})")
    parser.add_argument("--omit-brand", action="store_true", help="Brand etiketini tamamen yazma")
    parser.add_argument("--brand-override", default="", help="Tüm ürünlerde Brand bu değerle değişsin (örn: Markasız)")
    parser.add_argument("--sanitize-images", action="store_true", help="Image URL'lerdeki boşlukları %20 ile değiştir")
    parser.add_argument("--banned-term-replace", action="append", default=[], help="Yasaklı kelime değişimi: ORJ=YENI biçiminde. Çoklu kullanılabilir.")
    args = parser.parse_args()

    source_path = Path(args.input)
    if not source_path.is_file():
        print(f"Kaynak dosya bulunamadı: {source_path}", file=sys.stderr)
        sys.exit(1)

    tree = ET.parse(str(source_path))
    root = tree.getroot()

    products_data = []
    banned_map = {}
    for item in args.banned_term_replace:
        if '=' in item:
            src, repl = item.split('=', 1)
            src = src.strip()
            repl = repl.strip()
            if src:
                pattern = r"\b" + re.escape(src) + r"\b"
                banned_map[pattern] = repl
    for product in root.findall("Product"):
        pdata = convert_product(product, variant_mode=args.variant_mode, barcode_strategy=args.barcode_strategy, barcode_prefix=args.barcode_prefix, add_bullets=args.add_bullets, title_template=args.title_template, brand_override=args.brand_override, banned_map=banned_map if banned_map else None, sanitize_images=args.sanitize_images)
        products_data.append(pdata)

    out_root = build_stockmount_xml(products_data, omit_brand=args.omit_brand)
    xml_str = serialize_with_cdata(out_root)
    Path(args.output).write_text(xml_str, encoding="utf-8")
    print(f"Olusturuldu: {args.output} ({len(products_data)} ürün)")

if __name__ == "__main__":
    main()
