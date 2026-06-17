from tidalwave.models.db import Base, Listen, User


def test_tables_registered():
    names = set(Base.metadata.tables)
    assert names == {"users", "listens", "sync_state", "shares"}


def test_listen_dedup_constraint_present():
    cols = {c.name for c in Listen.__table__.columns}
    assert {"user_id", "artist", "track_title", "played_at"} <= cols
    uniques = [c for c in Listen.__table__.constraints if c.__class__.__name__ == "UniqueConstraint"]
    assert any(
        {col.name for col in u.columns} == {"user_id", "artist", "track_title", "played_at"}
        for u in uniques
    )


def test_user_username_unique():
    assert User.__table__.columns["lastfm_username"].unique is True
