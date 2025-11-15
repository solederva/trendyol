#!/usr/bin/env python3
import os
import sys
import logging
import concurrent.futures as futures
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import requests
from PIL import Image, ImageFilter
from rembg import remove
import xml.etree.ElementTree as ET


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

ROOT = Path(__file__).resolve().parents[1]
FEED_PATH = ROOT / 'data' / 'chekich21_synthetic_bullets_titled_nobrand.xml'
OUT_DIR = ROOT / 'data' / 'processed_images'
OUT_DIR.mkdir(parents=True, exist_ok=True)


def normalize_url(url: str) -> str:
    # XML'de &amp; olabilir, düzelt
    return url.replace('&amp;', '&')


def download_image(url: str) -> Image.Image:
    url = normalize_url(url)
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=60)
    resp.raise_for_status()
    img = Image.open(BytesIO(resp.content)).convert('RGBA')
    return img


def compose_on_white(product_rgba: Image.Image) -> Image.Image:
    # Beyaz arka plan + yumuşak gölge ile merkezde konumlandır
    w, h = product_rgba.size
    canvas = Image.new('RGB', (w, h), (255, 255, 255))

    # Gölge: alpha mask üzerinden gauss blur
    try:
        alpha = product_rgba.split()[3]
    except Exception:
        alpha = None

    if alpha is not None:
        shadow = Image.new('RGBA', product_rgba.size, (0, 0, 0, 0))
        shadow_layer = Image.new('RGBA', product_rgba.size, (0, 0, 0, 120))
        shadow.paste(shadow_layer, (0, 0), mask=alpha)
        shadow = shadow.filter(ImageFilter.GaussianBlur(18))
        # Hafif aşağı-ofset gölge
        canvas_rgba = canvas.convert('RGBA')
        canvas_rgba.alpha_composite(shadow, dest=(8, 14))
        canvas = canvas_rgba.convert('RGB')

    # Ürünü yerleştir (merkez)
    product_rgb = product_rgba.convert('RGB')
    x = (canvas.width - product_rgb.width) // 2
    y = (canvas.height - product_rgb.height) // 2
    canvas.paste(product_rgb, (x, y))
    return canvas


def process_single(product_code: str, index: int, url: str) -> tuple[Path, bool]:
    """
    Tek bir görseli indir, arka planı rembg ile kaldır ve beyaz arka planda kaydet.
    Döndür: (çıktı yolu, başarı)
    """
    out_path = OUT_DIR / f"{product_code}_img{index}.jpg"
    try:
        img = download_image(url)
        # rembg remove
        cutout_bytes = remove(BytesIO(img.tobytes()))  # not used; better to use PIL input
    except Exception:
        cutout_bytes = None

    try:
        # rembg remove - PIL friendly path
        from rembg import remove as rembg_remove
        out_rgba = rembg_remove(img)
    except Exception as e:
        logging.error(f"rembg hata: {e} - {product_code} img{index}")
        return (out_path, False)

    # Beyaz kompozit
    composed = compose_on_white(out_rgba)
    composed.save(out_path, quality=95)
    return (out_path, True)


def iter_products(feed_path: Path):
    tree = ET.parse(feed_path)
    root = tree.getroot()
    for p in root.findall('Product'):
        code_el = p.find('ProductCode')
        if code_el is None or not (code_el.text or '').strip():
            continue
        code = code_el.text.strip()
        images = []
        for i in range(1, 6):
            tag = f'Image{i}'
            el = p.find(tag)
            if el is not None and el.text:
                images.append((i, el.text.strip()))
        if images:
            yield code, images


def main(max_products: int | None = None, max_workers: int = 6):
    if not FEED_PATH.exists():
        logging.error(f"Feed bulunamadı: {FEED_PATH}")
        sys.exit(1)

    to_process = []
    for code, images in iter_products(FEED_PATH):
        for idx, url in images:
            out_path = OUT_DIR / f"{code}_img{idx}.jpg"
            if not out_path.exists():
                to_process.append((code, idx, url))
        if max_products is not None and len(to_process) >= max_products * 5:
            break

    if not to_process:
        logging.info("İşlenecek yeni görsel yok. Çıkılıyor.")
        return 0

    logging.info(f"Toplam işlenecek görsel: {len(to_process)}")

    ok = 0
    with futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(process_single, code, idx, url) for code, idx, url in to_process]
        for f in futures.as_completed(futs):
            out_path, success = f.result()
            if success:
                ok += 1
                logging.info(f"✓ {out_path.relative_to(ROOT)}")
            else:
                logging.warning(f"✗ Hata: {out_path.relative_to(ROOT)}")

    logging.info(f"Tamamlandı. Başarılı: {ok}/{len(to_process)}")
    return 0 if ok > 0 else 1


if __name__ == '__main__':
    # Opsiyonel argümanlar: max_products, max_workers
    mp = int(os.environ.get('MAX_PRODUCTS', '0')) or None
    mw = int(os.environ.get('MAX_WORKERS', '6'))
    sys.exit(main(max_products=mp, max_workers=mw))
