import time

from cacheai import CacheAI


def test_cache_hit_and_miss():
    cache = CacheAI(backend="memory", adaptive_ttl=False, default_ttl=60)
    calls = []

    @cache.intelligent()
    def get_value(x):
        calls.append(x)
        return {"value": x * 2}

    assert get_value(5) == {"value": 10}
    assert get_value(5) == {"value": 10}
    assert calls == [5]  # second call served from cache, function not re-executed

    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate"] == 0.5


def test_different_args_are_different_cache_entries():
    cache = CacheAI(backend="memory", adaptive_ttl=False, default_ttl=60)

    @cache.intelligent()
    def get_value(x):
        return x * 2

    assert get_value(1) == 2
    assert get_value(2) == 4
    assert cache.stats()["misses"] == 2


def test_invalidate_forces_recompute():
    cache = CacheAI(backend="memory", adaptive_ttl=False, default_ttl=60)
    calls = []

    @cache.intelligent()
    def get_value(x):
        calls.append(x)
        return x

    get_value(1)
    get_value.invalidate(1)
    get_value(1)
    assert calls == [1, 1]


def test_expired_entry_is_recomputed():
    cache = CacheAI(backend="memory", adaptive_ttl=False, default_ttl=1)
    calls = []

    @cache.intelligent()
    def get_value(x):
        calls.append(x)
        return x

    get_value(1)
    time.sleep(1.2)
    get_value(1)
    assert calls == [1, 1]


def test_adaptive_ttl_grows_for_frequently_accessed_key():
    cache = CacheAI(backend="memory", adaptive_ttl=True, default_ttl=60, min_ttl=5, max_ttl=1800)

    @cache.intelligent()
    def get_value(x):
        return x

    get_value(1)
    fingerprint = cache._fingerprint(get_value.__wrapped__, (1,), {})
    now = time.time()
    cache._history[fingerprint].clear()
    cache._history[fingerprint].extend([now + i * 2 for i in range(10)])  # accessed every ~2s

    ttl = cache._adaptive_ttl(fingerprint)
    assert ttl > cache.default_ttl


def test_adaptive_ttl_shrinks_for_rarely_accessed_key():
    cache = CacheAI(backend="memory", adaptive_ttl=True, default_ttl=60, min_ttl=5, max_ttl=1800)

    @cache.intelligent()
    def get_value(x):
        return x

    get_value(1)
    fingerprint = cache._fingerprint(get_value.__wrapped__, (1,), {})
    now = time.time()
    cache._history[fingerprint].clear()
    cache._history[fingerprint].extend([now, now + 7200])  # accessed ~2h apart

    ttl = cache._adaptive_ttl(fingerprint)
    assert ttl < cache.default_ttl
