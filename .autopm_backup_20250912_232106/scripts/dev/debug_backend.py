#!/usr/bin/env python3
"""Debug script to understand the backend error"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from backend.api_keys import APIKeysManager

# Test API keys manager
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "speecher")

api_keys_manager = APIKeysManager(MONGODB_URI, MONGODB_DB)

# Get AWS API keys
api_keys = api_keys_manager.get_api_keys("aws")
print(f"API Keys object: {api_keys}")
print(f"Type: {type(api_keys)}")

if api_keys:
    print(f"Keys field: {api_keys.get('keys')}")
    keys = api_keys.get("keys", {})
    print(f"Keys dict: {keys}")
    print(f"Has access_key_id: {bool(keys.get('access_key_id'))}")
    print(f"Has secret_access_key: {bool(keys.get('secret_access_key'))}")
    print(f"Has s3_bucket_name: {bool(keys.get('s3_bucket_name'))}")
    print(f"S3 bucket value: {keys.get('s3_bucket_name')}")
else:
    print("No API keys found for AWS")