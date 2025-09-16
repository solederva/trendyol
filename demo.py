#!/usr/bin/env python3
"""
Demo script to showcase Shopify XML Feed Integration capabilities

This script demonstrates the main features without requiring actual Shopify credentials.
"""

import json
import sys
from pathlib import Path
from shopify_integration import XMLProductParser


def demo_xml_parsing():
    """Demonstrate XML parsing capabilities"""
    print("=== XML Parsing Demo ===")
    
    # Find an XML file to parse
    xml_files = list(Path("data").glob("*.xml"))
    if not xml_files:
        print("No XML files found in data/ directory")
        return False
    
    xml_file = xml_files[0]
    print(f"Parsing file: {xml_file}")
    
    # Parse products
    products = XMLProductParser.parse_xml_file(str(xml_file))
    
    if not products:
        print("No products found in XML file")
        return False
    
    print(f"Successfully parsed {len(products)} products")
    
    # Show details of first product
    product = products[0]
    print(f"\nFirst Product Details:")
    print(f"  Code: {product.product_code}")
    print(f"  Title: {product.title}")
    print(f"  Price: {product.price} {product.currency}")
    print(f"  Stock: {product.quantity}")
    print(f"  Images: {len(product.images)}")
    print(f"  Variants: {len(product.variants)}")
    print(f"  Category: {product.category}")
    
    if product.variants:
        print(f"\nFirst Variant:")
        variant = product.variants[0]
        print(f"  Code: {variant.get('VariantCode', 'N/A')}")
        print(f"  Price: {variant.get('VariantPrice', 'N/A')}")
        print(f"  Stock: {variant.get('VariantQuantity', 'N/A')}")
        print(f"  Color: {variant.get('VariantValue1', 'N/A')}")
        print(f"  Size: {variant.get('VariantValue2', 'N/A')}")
    
    return True


def demo_shopify_payload():
    """Demonstrate Shopify API payload generation"""
    print("\n=== Shopify Payload Demo ===")
    
    from shopify_integration import ShopifyAPI, ProductData
    
    # Create a sample product
    sample_product = ProductData(
        product_code="DEMO001",
        title="Demo Product - Test Ayakkabı",
        price=100.0,
        quantity=50,
        currency="TL",
        description="<p>This is a demo product for testing purposes.</p>",
        category="Test > Demo Products",
        images=["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
        variants=[
            {
                "VariantCode": "DEMO001-RED-40",
                "VariantPrice": "100",
                "VariantQuantity": "25",
                "VariantName1": "Renk",
                "VariantValue1": "RED",
                "VariantName2": "Beden", 
                "VariantValue2": "40"
            },
            {
                "VariantCode": "DEMO001-RED-41",
                "VariantPrice": "100",
                "VariantQuantity": "25",
                "VariantName1": "Renk",
                "VariantValue1": "RED",
                "VariantName2": "Beden",
                "VariantValue2": "41"
            }
        ],
        tags=["demo", "test", "ayakkabı"]
    )
    
    # Create mock Shopify API instance
    shopify_api = ShopifyAPI("demo-store.myshopify.com", "fake-token")
    
    # Generate payload
    payload = shopify_api._build_product_payload(sample_product)
    
    print("Generated Shopify API Payload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    
    return True


def demo_hash_calculation():
    """Demonstrate change detection via hash calculation"""
    print("\n=== Change Detection Demo ===")
    
    from shopify_integration import ShopifySync, ProductData
    
    # Create mock sync instance
    sync = ShopifySync("demo.myshopify.com", "fake-token", "demo_state.json")
    
    # Create two versions of the same product
    product_v1 = ProductData(
        product_code="TEST001",
        title="Test Product",
        price=100.0,
        quantity=50,
        currency="TL",
        description="Test description",
        category="Test",
        images=["image1.jpg"],
        variants=[
            {"VariantCode": "TEST001-40", "VariantPrice": "100", "VariantQuantity": "25"}
        ]
    )
    
    product_v2 = ProductData(
        product_code="TEST001",
        title="Test Product",
        price=120.0,  # Price changed
        quantity=45,  # Stock changed
        currency="TL",
        description="Test description",
        category="Test",
        images=["image1.jpg"],
        variants=[
            {"VariantCode": "TEST001-40", "VariantPrice": "120", "VariantQuantity": "25"}
        ]
    )
    
    hash_v1 = sync._calculate_product_hash(product_v1)
    hash_v2 = sync._calculate_product_hash(product_v2)
    
    print(f"Product V1 Hash: {hash_v1}")
    print(f"Product V2 Hash: {hash_v2}")
    print(f"Products are different: {hash_v1 != hash_v2}")
    
    return True


def demo_monitoring_config():
    """Demonstrate monitoring configuration"""
    print("\n=== Monitoring Configuration Demo ===")
    
    sample_config = {
        "xml_feed_url": "https://example.com/live-feed.xml",
        "shopify": {
            "shop_domain": "your-store.myshopify.com",
            "access_token": "your-access-token-here"
        },
        "monitor_interval_minutes": 30,
        "max_retry_attempts": 3,
        "retry_delay_seconds": 60,
        "local_xml_cache": "cached_feed.xml",
        "state_file": "sync_state.json",
        "max_sync_errors": 5
    }
    
    print("Sample Monitoring Configuration:")
    print(json.dumps(sample_config, indent=2))
    
    print("\nMonitoring Process:")
    print("1. Download XML feed from URL every 30 minutes")
    print("2. Calculate hash of feed content")
    print("3. If changed, parse products and compare with previous state")
    print("4. Update only changed products in Shopify")
    print("5. Save new state and continue monitoring")
    
    return True


def main():
    print("Shopify XML Feed Integration - Demo")
    print("=" * 50)
    
    try:
        # Run all demos
        success = True
        success &= demo_xml_parsing()
        success &= demo_shopify_payload()
        success &= demo_hash_calculation()
        success &= demo_monitoring_config()
        
        if success:
            print("\n✅ All demos completed successfully!")
            print("\nNext steps:")
            print("1. Get Shopify Admin API credentials")
            print("2. Run: python setup_shopify.py")
            print("3. Test with: python shopify_integration.py --mode initial ...")
            print("4. Start monitoring: python feed_monitor.py --mode daemon ...")
        else:
            print("\n❌ Some demos failed. Please check the output above.")
            
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()