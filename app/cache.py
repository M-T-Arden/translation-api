import redis
import hashlib
import json
from typing import Optional
from .config import get_settings

settings = get_settings()

# Redis client
redis_client = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_keepalive=True
)

def generate_cache_key(text: str, source_lang: str, target_lang: str) -> str:
    """Generate unique cache key for translation"""
    content = f"{text}:{source_lang}:{target_lang}"
    return f"trans:{hashlib.md5(content.encode()).hexdigest()}"

async def get_cached_translation(
    text: str,
    source_lang: str,
    target_lang: str
) -> Optional[str]:
    """Retrieve translation from cache"""
    try:
        cache_key = generate_cache_key(text, source_lang, target_lang)
        cached = redis_client.get(cache_key)
        
        if cached:
            redis_client.incr("stats:cache_hits")
            return cached
        
        redis_client.incr("stats:cache_misses")
        return None
    except Exception as e:
        print(f"Cache get error: {e}")
        return None

async def set_cached_translation(
    text: str,
    source_lang: str,
    target_lang: str,
    translated_text: str
) -> int:
    """
    Store translation in cache with smart expiration based on popularity
    Returns the request count for this translation
    """
    try:
        cache_key = generate_cache_key(text, source_lang, target_lang)
        count_key = f"count:{cache_key}"
        
        # Increment request count
        count = redis_client.incr(count_key)
        redis_client.expire(count_key, 604800)  # 7 days
        
        # Smart expiration based on popularity
        if count >= 100:
            expire_seconds = 604800  # 7 days - very popular
        elif count >= 20:
            expire_seconds = 86400   # 1 day - popular
        elif count >= 5:
            expire_seconds = 3600    # 1 hour - moderately popular
        else:
            expire_seconds = 1800    # 30 minutes - normal
        
        redis_client.setex(cache_key, expire_seconds, translated_text)
        return count
    except Exception as e:
        print(f"Cache set error: {e}")
        return 0

async def get_cache_stats() -> dict:
    """Get cache statistics"""
    try:
        hits = int(redis_client.get("stats:cache_hits") or 0)
        misses = int(redis_client.get("stats:cache_misses") or 0)
        total = hits + misses
        hit_rate = (hits / total * 100) if total > 0 else 0
        
        info = redis_client.info("memory")
        
        return {
            "cache_hits": hits,
            "cache_misses": misses,
            "hit_rate": f"{hit_rate:.2f}%",
            "total_requests": total,
            "memory_used": info.get("used_memory_human", "N/A"),
            "total_keys": redis_client.dbsize()
        }
    except Exception as e:
        print(f"Cache stats error: {e}")
        return {
            "cache_hits": 0,
            "cache_misses": 0,
            "hit_rate": "0%",
            "total_requests": 0,
            "memory_used": "N/A",
            "total_keys": 0
        }