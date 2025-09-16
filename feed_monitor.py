#!/usr/bin/env python3
"""
XML Feed Monitor Daemon

Monitors a live XML feed URL for changes and automatically updates Shopify store.
Supports:
- Periodic monitoring with configurable intervals
- Price and stock change detection
- Error handling and retry logic
- Logging and status reporting
"""

import argparse
import json
import logging
import os
import signal
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import hashlib

from shopify_integration import ShopifySync, XMLProductParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('feed_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FeedMonitor:
    """XML Feed monitoring daemon"""
    
    def __init__(self, config_file: str):
        self.config = self._load_config(config_file)
        self.running = False
        self.last_feed_hash = ""
        self.last_successful_sync = None
        self.sync_error_count = 0
        
        # Initialize Shopify sync
        self.shopify_sync = ShopifySync(
            self.config['shopify']['shop_domain'],
            self.config['shopify']['access_token'],
            self.config.get('state_file', 'sync_state.json')
        )
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _load_config(self, config_file: str) -> dict:
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Validate required fields
            required_fields = [
                'xml_feed_url',
                'shopify.shop_domain',
                'shopify.access_token'
            ]
            
            for field in required_fields:
                keys = field.split('.')
                current = config
                for key in keys:
                    if key not in current:
                        raise ValueError(f"Missing required config field: {field}")
                    current = current[key]
            
            # Set defaults
            config.setdefault('monitor_interval_minutes', 30)
            config.setdefault('max_retry_attempts', 3)
            config.setdefault('retry_delay_seconds', 60)
            config.setdefault('local_xml_cache', 'cached_feed.xml')
            config.setdefault('state_file', 'sync_state.json')
            config.setdefault('max_sync_errors', 5)
            
            return config
            
        except Exception as e:
            logger.error(f"Error loading config file {config_file}: {e}")
            sys.exit(1)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def _download_feed(self, url: str, output_path: str) -> bool:
        """Download XML feed from URL"""
        try:
            logger.info(f"Downloading feed from {url}")
            
            # Add user agent and timeout
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (compatible; FeedMonitor/1.0)')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status == 200:
                    with open(output_path, 'wb') as f:
                        f.write(response.read())
                    logger.info(f"Feed downloaded successfully to {output_path}")
                    return True
                else:
                    logger.error(f"HTTP error downloading feed: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error downloading feed: {e}")
            return False
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of file content"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.md5(content).hexdigest()
        except Exception as e:
            logger.error(f"Error calculating file hash: {e}")
            return ""
    
    def _has_feed_changed(self, xml_path: str) -> bool:
        """Check if feed content has changed since last check"""
        current_hash = self._calculate_file_hash(xml_path)
        if current_hash != self.last_feed_hash:
            logger.info("Feed content has changed")
            self.last_feed_hash = current_hash
            return True
        else:
            logger.debug("Feed content unchanged")
            return False
    
    def _sync_with_shopify(self, xml_path: str) -> bool:
        """Synchronize XML feed with Shopify store"""
        try:
            # Check if this is the first run (no state file exists)
            state_file = Path(self.config['state_file'])
            is_initial_sync = not state_file.exists() or os.path.getsize(state_file) == 0
            
            if is_initial_sync:
                logger.info("Performing initial full sync with Shopify")
                success, fail = self.shopify_sync.initial_upload(xml_path)
                if fail == 0:
                    logger.info(f"Initial sync completed successfully: {success} products uploaded")
                    self.sync_error_count = 0
                    self.last_successful_sync = datetime.now()
                    return True
                else:
                    logger.warning(f"Initial sync completed with errors: {success} success, {fail} failed")
                    self.sync_error_count += 1
                    return False
            else:
                logger.info("Performing incremental sync with Shopify")
                updated, new, unchanged = self.shopify_sync.incremental_update(xml_path)
                logger.info(f"Incremental sync completed: {updated} updated, {new} new, {unchanged} unchanged")
                self.sync_error_count = 0
                self.last_successful_sync = datetime.now()
                return True
                
        except Exception as e:
            logger.error(f"Error during Shopify sync: {e}")
            self.sync_error_count += 1
            return False
    
    def _should_stop_monitoring(self) -> bool:
        """Check if monitoring should be stopped due to too many errors"""
        max_errors = self.config.get('max_sync_errors', 5)
        if self.sync_error_count >= max_errors:
            logger.error(f"Too many sync errors ({self.sync_error_count}), stopping monitor")
            return True
        return False
    
    def _get_status_report(self) -> dict:
        """Generate status report"""
        return {
            "status": "running" if self.running else "stopped",
            "last_successful_sync": self.last_successful_sync.isoformat() if self.last_successful_sync else None,
            "sync_error_count": self.sync_error_count,
            "last_feed_hash": self.last_feed_hash,
            "config": {
                "monitor_interval_minutes": self.config['monitor_interval_minutes'],
                "xml_feed_url": self.config['xml_feed_url'],
                "shop_domain": self.config['shopify']['shop_domain']
            }
        }
    
    def run_once(self) -> bool:
        """Run one monitoring cycle"""
        xml_cache_path = self.config['local_xml_cache']
        
        # Download feed
        if not self._download_feed(self.config['xml_feed_url'], xml_cache_path):
            logger.error("Failed to download feed, skipping this cycle")
            return False
        
        # Check if feed changed
        if not self._has_feed_changed(xml_cache_path):
            logger.debug("No changes detected, skipping sync")
            return True
        
        # Sync with Shopify
        return self._sync_with_shopify(xml_cache_path)
    
    def run_daemon(self):
        """Run monitoring daemon"""
        logger.info("Starting XML feed monitor daemon")
        logger.info(f"Monitoring URL: {self.config['xml_feed_url']}")
        logger.info(f"Check interval: {self.config['monitor_interval_minutes']} minutes")
        logger.info(f"Shopify store: {self.config['shopify']['shop_domain']}")
        
        self.running = True
        next_check_time = datetime.now()
        
        while self.running:
            try:
                current_time = datetime.now()
                
                if current_time >= next_check_time:
                    logger.info("Starting monitoring cycle")
                    
                    success = self.run_once()
                    if not success and self._should_stop_monitoring():
                        break
                    
                    # Schedule next check
                    interval = timedelta(minutes=self.config['monitor_interval_minutes'])
                    next_check_time = current_time + interval
                    logger.info(f"Next check scheduled for: {next_check_time}")
                
                # Sleep for a short interval to avoid busy waiting
                time.sleep(min(30, self.config['monitor_interval_minutes'] * 60 // 4))
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in monitoring loop: {e}")
                time.sleep(60)  # Wait before retrying
        
        self.running = False
        logger.info("Monitor daemon stopped")
    
    def status(self):
        """Print current status"""
        report = self._get_status_report()
        print(json.dumps(report, indent=2))


def create_sample_config():
    """Create a sample configuration file"""
    config = {
        "xml_feed_url": "https://example.com/feed.xml",
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
    
    with open("monitor_config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print("Sample configuration created: monitor_config.json")
    print("Please edit this file with your actual settings before running the monitor.")


def main():
    parser = argparse.ArgumentParser(description="XML Feed Monitor for Shopify Integration")
    parser.add_argument("--config", required=True, help="Configuration file path")
    parser.add_argument("--mode", choices=["daemon", "once", "status", "create-config"], 
                       default="daemon", help="Run mode")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                       default="INFO", help="Logging level")
    
    args = parser.parse_args()
    
    # Configure logging level
    logger.setLevel(getattr(logging, args.log_level))
    
    if args.mode == "create-config":
        create_sample_config()
        return
    
    if not Path(args.config).exists():
        logger.error(f"Configuration file not found: {args.config}")
        logger.info("Use --mode create-config to create a sample configuration file")
        sys.exit(1)
    
    monitor = FeedMonitor(args.config)
    
    try:
        if args.mode == "daemon":
            monitor.run_daemon()
        elif args.mode == "once":
            success = monitor.run_once()
            print(f"Monitoring cycle completed: {'success' if success else 'failed'}")
        elif args.mode == "status":
            monitor.status()
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()