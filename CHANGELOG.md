# Changelog

## v0.1.0 (unreleased)

**Core**
- `@cache.intelligent()` decorator with memory and Redis backends.
- Adaptive TTL heuristic based on recent access frequency (not ML --
  see README for why, and for the benchmark showing when it actually helps).
- `cache.invalidate(func, *args)` for manual eviction.
- `cache.stats()` for hits/misses/hit-rate.

**Invalidation**
- Tag-based invalidation: `@cache.intelligent(tags=[...])` +
  `cache.invalidate_tag(...)`. Safe across processes on the Redis backend
  (tag membership is stored in Redis, not per-process memory).
- `cacheai.ext.sqlalchemy.watch_sqlalchemy()`: automatic tag invalidation
  when a watched SQLAlchemy `Session` commits a write to a matching table.
  Scoped to that ORM session -- raw SQL or other services aren't detected.

**Validation**
- 14 tests (core, Redis, tags, SQLAlchemy integration, and a full FastAPI
  example) run in CI on Python 3.9-3.12 with a real Redis service container.
- `benchmark.py`: a real (wall-clock, not mocked) benchmark comparing no
  cache / static TTL / adaptive TTL, with the honest result documented in
  the README -- adaptive wins when the static TTL is conservative, ties
  when it's already generous.
- `examples/fastapi_app.py`: a small runnable service demonstrating the
  full loop (cache a read, write through SQLAlchemy, watch it
  auto-invalidate) end to end.

**Not here yet**
- PyPI release
- A learned model in place of the heuristic
- Go/Node SDKs, a stats dashboard
- General (non-SQLAlchemy) automatic invalidation
