import json
import os
import time
from utils import log

CACHE_DIR = '.cache'

def _get_cache_path(key):
    # Sanitize key to be safe filename
    safe_key = "".join([c if c.isalnum() or c in ('-', '_') else '_' for c in key])
    return os.path.join(CACHE_DIR, f"{safe_key}.json")

def cache_get(key, ttl_seconds=300):
    """
    Get cached value if exists and not expired.
    Returns None if missing or expired.
    """
    try:
        path = _get_cache_path(key)
        if not os.path.exists(path):
            return None
        
        stat = os.stat(path)
        age = time.time() - stat.st_mtime
        
        if age > ttl_seconds:
            # os.remove(path) # Optional: Cleanup expired? Or let write overwrite it.
            return None  # Expired
        
        with open(path, 'r') as f:
            return json.load(f)
            
    except Exception as e:
        log("WARN", f"Cache Read Error ({key}): {e}")
        return None

def cache_set(key, value):
    """
    Store value in cache.
    """
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        path = _get_cache_path(key)
        
        # Atomic Write pattern (write to temp then rename) prevents partial reads
        # But for this scale, direct write is acceptable if simple.
        # We will do direct write for simplicity as per user request.
        with open(path, 'w') as f:
            json.dump(value, f)
            
    except Exception as e:
        log("WARN", f"Cache Write Error ({key}): {e}")

def clear_cache(key=None):
    """Clear specific key or entire cache."""
    try:
        if key:
            path = _get_cache_path(key)
            if os.path.exists(path):
                os.remove(path)
        else:
            if os.path.exists(CACHE_DIR):
                for f in os.listdir(CACHE_DIR):
                    if f.endswith(".json"):
                        os.remove(os.path.join(CACHE_DIR, f))
    except Exception as e:
        log("ERROR", f"Cache Clear Error: {e}")
