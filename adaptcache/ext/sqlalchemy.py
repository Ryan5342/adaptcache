"""Optional SQLAlchemy integration: automatically invalidate tagged cache
entries when a table they depend on is written to.

This is scoped and honest about its limits: it hooks SQLAlchemy's ORM
session events, so it only sees writes made through that Session class.
Raw SQL run outside the ORM (or from another service) is not detected.
General, DB-agnostic auto-invalidation is still on the roadmap, not here.

Usage:
    from adaptcache import AdaptCache
    from adaptcache.ext.sqlalchemy import watch_sqlalchemy

    cache = AdaptCache(backend="redis", redis_url="redis://localhost:6379")
    watch_sqlalchemy(cache, Session)  # Session = your sessionmaker(...) class

    @cache.intelligent(tags=["users"])
    def get_user(user_id):
        ...

Any commit that inserts/updates/deletes a row whose model has
`__tablename__ == "users"` invalidates every cache entry tagged "users".
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..core import AdaptCache

_INFO_KEY = "_adaptcache_touched_tables"


def watch_sqlalchemy(cache: "AdaptCache", session_class: Any) -> None:
    """Attach event listeners to `session_class` (a sessionmaker(...) class,
    or scoped_session) that call `cache.invalidate_tag(table_name)` for
    every table touched by a committed transaction.
    """
    try:
        from sqlalchemy import event
    except ImportError as exc:
        raise ImportError(
            "watch_sqlalchemy requires SQLAlchemy. Install with: pip install adaptcache[sqlalchemy]"
        ) from exc

    @event.listens_for(session_class, "after_flush")
    def _collect_touched_tables(session: Any, flush_context: Any) -> None:
        # session.new/dirty/deleted are only reliably populated up to this
        # point in the commit lifecycle -- by after_commit they're cleared.
        touched = session.info.setdefault(_INFO_KEY, set())
        for obj in list(session.new) + list(session.dirty) + list(session.deleted):
            table_name = getattr(obj, "__tablename__", None)
            if table_name:
                touched.add(table_name)

    @event.listens_for(session_class, "after_commit")
    def _invalidate_touched_tables(session: Any) -> None:
        touched = session.info.pop(_INFO_KEY, None)
        if touched:
            for table_name in touched:
                cache.invalidate_tag(table_name)

    @event.listens_for(session_class, "after_rollback")
    def _discard_touched_tables(session: Any) -> None:
        # A rolled-back transaction never happened -- don't invalidate,
        # and don't leak this session's bookkeeping into its next transaction.
        session.info.pop(_INFO_KEY, None)
