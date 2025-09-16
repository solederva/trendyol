#!/bin/bash
"""
Shopify XML Feed Integration Setup Script

This script helps you set up the Shopify integration for your XML product feed.
"""

import json
import sys
from pathlib import Path


def create_config():
    """Interactive configuration setup"""
    print("=== Shopify XML Feed Integration Setup ===\n")
    
    # Shopify store configuration
    print("1. Shopify Store Configuration:")
    shop_domain = input("Enter your Shopify store domain (e.g., mystore.myshopify.com): ").strip()
    access_token = input("Enter your Shopify Admin API access token: ").strip()
    
    if not shop_domain or not access_token:
        print("Error: Shop domain and access token are required!")
        return False
    
    # XML feed configuration
    print("\n2. XML Feed Configuration:")
    xml_feed_url = input("Enter your live XML feed URL: ").strip()
    
    if not xml_feed_url:
        print("Error: XML feed URL is required!")
        return False
    
    # Monitoring configuration
    print("\n3. Monitoring Configuration:")
    try:
        interval = int(input("Enter monitoring interval in minutes (default: 30): ") or "30")
    except ValueError:
        interval = 30
    
    # Create configuration
    config = {
        "xml_feed_url": xml_feed_url,
        "shopify": {
            "shop_domain": shop_domain,
            "access_token": access_token
        },
        "monitor_interval_minutes": interval,
        "max_retry_attempts": 3,
        "retry_delay_seconds": 60,
        "local_xml_cache": "cached_feed.xml",
        "state_file": "sync_state.json",
        "max_sync_errors": 5
    }
    
    # Save configuration
    config_file = "shopify_config.json"
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"\nConfiguration saved to: {config_file}")
    return True


def main():
    print(__doc__)
    
    if not create_config():
        sys.exit(1)
    
    print("\n=== Setup Complete ===")
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Test the connection: python feed_monitor.py --config shopify_config.json --mode once")
    print("3. Start monitoring: python feed_monitor.py --config shopify_config.json --mode daemon")
    print("\nFor initial product upload, run:")
    print("python shopify_integration.py --shop-domain <domain> --access-token <token> --xml-feed <path> --mode initial")


if __name__ == "__main__":
    main()