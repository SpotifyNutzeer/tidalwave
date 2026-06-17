from sqlalchemy import text

from tidalwave.models.db import User


async def test_session_can_insert_and_read(db_session):
    db_session.add(User(lastfm_username="alice", lastfm_session_key="sk"))
    await db_session.flush()
    row = (await db_session.execute(text("SELECT lastfm_username FROM users"))).scalar_one()
    assert row == "alice"
