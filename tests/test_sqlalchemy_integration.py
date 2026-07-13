import pytest

sqlalchemy = pytest.importorskip("sqlalchemy")

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from cacheai import CacheAI
from cacheai.ext.sqlalchemy import watch_sqlalchemy

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)


def _make_session_class():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_commit_invalidates_tagged_cache_entry():
    Session = _make_session_class()
    cache = CacheAI(backend="memory", adaptive_ttl=False, default_ttl=300)
    watch_sqlalchemy(cache, Session)
    calls = []

    @cache.intelligent(tags=["users"])
    def get_all_user_names():
        calls.append(1)
        session = Session()
        try:
            return [u.name for u in session.query(User).all()]
        finally:
            session.close()

    assert get_all_user_names() == []
    assert get_all_user_names() == []
    assert calls == [1]  # second call was a cache hit

    session = Session()
    session.add(User(name="Ana"))
    session.commit()
    session.close()

    assert get_all_user_names() == ["Ana"]
    assert calls == [1, 1]  # the commit invalidated the "users" tag


def test_rollback_does_not_invalidate():
    Session = _make_session_class()
    cache = CacheAI(backend="memory", adaptive_ttl=False, default_ttl=300)
    watch_sqlalchemy(cache, Session)
    calls = []

    @cache.intelligent(tags=["users"])
    def get_all_user_names():
        calls.append(1)
        session = Session()
        try:
            return [u.name for u in session.query(User).all()]
        finally:
            session.close()

    get_all_user_names()

    session = Session()
    session.add(User(name="Bob"))
    session.rollback()
    session.close()

    get_all_user_names()
    assert calls == [1]  # still cached: nothing was actually committed
