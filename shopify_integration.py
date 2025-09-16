#!/usr/bin/env python3
"""
Shopify Store Integration for XML Product Feed Management

This module provides functionality to:
1. Upload products from XML feed to Shopify store
2. Monitor XML feed for changes (price, stock)
3. Update Shopify products incrementally
4. Track synchronization state
"""

import argparse
import json
import logging
import os
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import hashlib
import requests
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ProductData:
    """Product data structure for Shopify"""
    product_code: str
    title: str
    price: float
    quantity: int
    currency: str
    description: str
    category: str
    images: List[str]
    variants: List[Dict]
    barcode: str = ""
    vendor: str = "solederva"
    product_type: str = ""
    tags: List[str] = None


@dataclass
class SyncState:
    """Track synchronization state"""
    last_sync: str
    product_hashes: Dict[str, str]
    shopify_product_ids: Dict[str, str]  # product_code -> shopify_id mapping


class ShopifyAPI:
    """Shopify Admin API wrapper"""
    
    def __init__(self, shop_domain: str, access_token: str):
        self.shop_domain = shop_domain
        self.access_token = access_token
        self.base_url = f"https://{shop_domain}/admin/api/2023-10/products"
        self.headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        }
    
    def create_product(self, product_data: ProductData) -> Optional[str]:
        """Create a new product in Shopify"""
        try:
            payload = self._build_product_payload(product_data)
            response = requests.post(self.base_url + ".json", 
                                   headers=self.headers, 
                                   json=payload)
            
            if response.status_code == 201:
                result = response.json()
                product_id = str(result['product']['id'])
                logger.info(f"Created product: {product_data.product_code} (ID: {product_id})")
                return product_id
            else:
                logger.error(f"Failed to create product {product_data.product_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating product {product_data.product_code}: {e}")
            return None
    
    def update_product(self, product_id: str, product_data: ProductData) -> bool:
        """Update existing product in Shopify"""
        try:
            payload = self._build_product_payload(product_data, update=True)
            response = requests.put(f"{self.base_url}/{product_id}.json",
                                  headers=self.headers,
                                  json=payload)
            
            if response.status_code == 200:
                logger.info(f"Updated product: {product_data.product_code} (ID: {product_id})")
                return True
            else:
                logger.error(f"Failed to update product {product_data.product_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating product {product_data.product_code}: {e}")
            return False
    
    def get_product(self, product_id: str) -> Optional[Dict]:
        """Get product details from Shopify"""
        try:
            response = requests.get(f"{self.base_url}/{product_id}.json",
                                  headers=self.headers)
            
            if response.status_code == 200:
                return response.json()['product']
            else:
                logger.warning(f"Product {product_id} not found: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting product {product_id}: {e}")
            return None
    
    def _build_product_payload(self, product_data: ProductData, update: bool = False) -> Dict:
        """Build Shopify API payload from product data"""
        # Convert price from TL to appropriate format
        price_value = str(product_data.price)
        
        # Build images array
        images = []
        for img_url in product_data.images:
            if img_url and img_url.strip():
                images.append({"src": img_url.strip()})
        
        # Build variants
        variants = []
        if product_data.variants:
            for variant in product_data.variants:
                variant_data = {
                    "sku": variant.get("VariantCode", ""),
                    "price": variant.get("VariantPrice", price_value),
                    "inventory_quantity": int(variant.get("VariantQuantity", 0)),
                    "inventory_management": "shopify",
                    "option1": variant.get("VariantValue1", ""),
                    "option2": variant.get("VariantValue2", ""),
                    "barcode": variant.get("VariantCode", "")
                }
                variants.append(variant_data)
        else:
            # Single variant product
            variants.append({
                "sku": product_data.product_code,
                "price": price_value,
                "inventory_quantity": product_data.quantity,
                "inventory_management": "shopify",
                "barcode": product_data.barcode
            })
        
        # Build options for variants
        options = []
        if product_data.variants and len(product_data.variants) > 0:
            first_variant = product_data.variants[0]
            if first_variant.get("VariantName1"):
                options.append({
                    "name": first_variant.get("VariantName1", "Option1"),
                    "values": list(set(v.get("VariantValue1", "") for v in product_data.variants if v.get("VariantValue1")))
                })
            if first_variant.get("VariantName2"):
                options.append({
                    "name": first_variant.get("VariantName2", "Option2"), 
                    "values": list(set(v.get("VariantValue2", "") for v in product_data.variants if v.get("VariantValue2")))
                })
        
        product_payload = {
            "title": product_data.title,
            "body_html": product_data.description,
            "vendor": product_data.vendor,
            "product_type": product_data.product_type or product_data.category,
            "tags": ",".join(product_data.tags or []),
            "variants": variants,
            "images": images[:10],  # Shopify limit
            "options": options
        }
        
        return {"product": product_payload}


class XMLProductParser:
    """Parse XML feed and extract product data"""
    
    @staticmethod
    def parse_xml_file(xml_path: str) -> List[ProductData]:
        """Parse XML file and return list of ProductData objects"""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            products = []
            
            for product_elem in root.findall("Product"):
                product_data = XMLProductParser._parse_product_element(product_elem)
                if product_data:
                    products.append(product_data)
            
            logger.info(f"Parsed {len(products)} products from {xml_path}")
            return products
            
        except Exception as e:
            logger.error(f"Error parsing XML file {xml_path}: {e}")
            return []
    
    @staticmethod
    def _parse_product_element(elem: ET.Element) -> Optional[ProductData]:
        """Parse single product element"""
        try:
            def get_text(tag: str) -> str:
                child = elem.find(tag)
                return child.text.strip() if child is not None and child.text else ""
            
            # Basic product info
            product_code = get_text("ProductCode")
            title = get_text("ProductName")
            price_str = get_text("Price")
            quantity_str = get_text("Quantity")
            currency = get_text("Currency") or "TL"
            description = get_text("Description")
            category = get_text("Category")
            barcode = get_text("Barcode")
            
            if not product_code or not title:
                logger.warning("Skipping product with missing code or title")
                return None
            
            # Parse price and quantity
            try:
                price = float(price_str) if price_str else 0.0
                quantity = int(quantity_str) if quantity_str else 0
            except ValueError:
                logger.warning(f"Invalid price/quantity for product {product_code}")
                price, quantity = 0.0, 0
            
            # Parse images
            images = []
            for i in range(1, 6):
                img_url = get_text(f"Image{i}")
                if img_url:
                    images.append(img_url)
            
            # Parse variants
            variants = []
            variants_elem = elem.find("Variants")
            if variants_elem is not None:
                for variant_elem in variants_elem.findall("Variant"):
                    variant_data = {}
                    for field in ["VariantCode", "VariantQuantity", "VariantPrice", 
                                "VariantName1", "VariantValue1", "VariantName2", "VariantValue2"]:
                        variant_child = variant_elem.find(field)
                        variant_data[field] = variant_child.text.strip() if variant_child is not None and variant_child.text else ""
                    variants.append(variant_data)
            
            # Generate tags from category
            tags = []
            if category:
                tags = [tag.strip() for tag in category.replace(" > ", ",").split(",") if tag.strip()]
            
            return ProductData(
                product_code=product_code,
                title=title,
                price=price,
                quantity=quantity,
                currency=currency,
                description=description,
                category=category,
                images=images,
                variants=variants,
                barcode=barcode,
                tags=tags
            )
            
        except Exception as e:
            logger.error(f"Error parsing product element: {e}")
            return None


class ShopifySync:
    """Main synchronization controller"""
    
    def __init__(self, shop_domain: str, access_token: str, state_file: str = "sync_state.json"):
        self.shopify = ShopifyAPI(shop_domain, access_token)
        self.state_file = Path(state_file)
        self.sync_state = self._load_sync_state()
    
    def _load_sync_state(self) -> SyncState:
        """Load synchronization state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                return SyncState(
                    last_sync=data.get("last_sync", ""),
                    product_hashes=data.get("product_hashes", {}),
                    shopify_product_ids=data.get("shopify_product_ids", {})
                )
            except Exception as e:
                logger.warning(f"Could not load sync state: {e}")
        
        return SyncState(
            last_sync="",
            product_hashes={},
            shopify_product_ids={}
        )
    
    def _save_sync_state(self):
        """Save synchronization state to file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(asdict(self.sync_state), f, indent=2)
        except Exception as e:
            logger.error(f"Could not save sync state: {e}")
    
    def _calculate_product_hash(self, product: ProductData) -> str:
        """Calculate hash of product data for change detection"""
        # Include only fields that matter for updates (price, quantity, variants)
        hash_data = {
            "price": product.price,
            "quantity": product.quantity,
            "variants": []
        }
        
        for variant in product.variants:
            hash_data["variants"].append({
                "code": variant.get("VariantCode", ""),
                "price": variant.get("VariantPrice", ""),
                "quantity": variant.get("VariantQuantity", "")
            })
        
        hash_str = json.dumps(hash_data, sort_keys=True)
        return hashlib.md5(hash_str.encode()).hexdigest()
    
    def initial_upload(self, xml_path: str) -> Tuple[int, int]:
        """Upload all products from XML to Shopify (initial setup)"""
        logger.info(f"Starting initial upload from {xml_path}")
        
        products = XMLProductParser.parse_xml_file(xml_path)
        success_count = 0
        fail_count = 0
        
        for product in products:
            # Skip if already uploaded
            if product.product_code in self.sync_state.shopify_product_ids:
                logger.info(f"Product {product.product_code} already exists, skipping")
                continue
            
            product_id = self.shopify.create_product(product)
            if product_id:
                self.sync_state.shopify_product_ids[product.product_code] = product_id
                self.sync_state.product_hashes[product.product_code] = self._calculate_product_hash(product)
                success_count += 1
            else:
                fail_count += 1
            
            # Rate limiting
            time.sleep(0.5)
        
        self.sync_state.last_sync = datetime.now().isoformat()
        self._save_sync_state()
        
        logger.info(f"Initial upload completed: {success_count} success, {fail_count} failed")
        return success_count, fail_count
    
    def incremental_update(self, xml_path: str) -> Tuple[int, int, int]:
        """Update changed products (price/stock monitoring)"""
        logger.info(f"Starting incremental update from {xml_path}")
        
        products = XMLProductParser.parse_xml_file(xml_path)
        updated_count = 0
        new_count = 0
        unchanged_count = 0
        
        for product in products:
            current_hash = self._calculate_product_hash(product)
            previous_hash = self.sync_state.product_hashes.get(product.product_code, "")
            
            if product.product_code not in self.sync_state.shopify_product_ids:
                # New product
                product_id = self.shopify.create_product(product)
                if product_id:
                    self.sync_state.shopify_product_ids[product.product_code] = product_id
                    self.sync_state.product_hashes[product.product_code] = current_hash
                    new_count += 1
                    logger.info(f"Added new product: {product.product_code}")
            
            elif current_hash != previous_hash:
                # Product changed - update
                product_id = self.sync_state.shopify_product_ids[product.product_code]
                if self.shopify.update_product(product_id, product):
                    self.sync_state.product_hashes[product.product_code] = current_hash
                    updated_count += 1
                    logger.info(f"Updated product: {product.product_code}")
            
            else:
                # No changes
                unchanged_count += 1
            
            # Rate limiting
            time.sleep(0.5)
        
        self.sync_state.last_sync = datetime.now().isoformat()
        self._save_sync_state()
        
        logger.info(f"Incremental update completed: {updated_count} updated, {new_count} new, {unchanged_count} unchanged")
        return updated_count, new_count, unchanged_count


def main():
    parser = argparse.ArgumentParser(description="Shopify Store XML Feed Integration")
    parser.add_argument("--shop-domain", required=True, help="Shopify shop domain (e.g., mystore.myshopify.com)")
    parser.add_argument("--access-token", required=True, help="Shopify Admin API access token")
    parser.add_argument("--xml-feed", required=True, help="Path to XML product feed")
    parser.add_argument("--mode", choices=["initial", "update"], default="update", 
                       help="Sync mode: initial (full upload) or update (incremental)")
    parser.add_argument("--state-file", default="sync_state.json", help="State file path")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                       default="INFO", help="Logging level")
    
    args = parser.parse_args()
    
    # Configure logging level
    logger.setLevel(getattr(logging, args.log_level))
    
    # Validate XML file exists
    if not Path(args.xml_feed).exists():
        logger.error(f"XML feed file not found: {args.xml_feed}")
        sys.exit(1)
    
    # Initialize synchronizer
    sync = ShopifySync(args.shop_domain, args.access_token, args.state_file)
    
    try:
        if args.mode == "initial":
            success, fail = sync.initial_upload(args.xml_feed)
            print(f"Initial upload: {success} successful, {fail} failed")
        else:
            updated, new, unchanged = sync.incremental_update(args.xml_feed)
            print(f"Incremental update: {updated} updated, {new} new, {unchanged} unchanged")
    
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()