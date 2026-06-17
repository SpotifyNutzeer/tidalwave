import pytest
from sqlalchemy import func, select

from tidalwave.auth.registration import RegistrationDenied
from tidalwave.auth.service import upsert_user_from_session
from tidalwave.models.db import User


async def test_first_user_becomes_admin(db_session):
    user = await upsert_user_from_session(
        db_session, "alice", "sk1", mode="open", allowlist=[]
    )
    assert user.is_admin is True
    assert user.lastfm_session_key == "sk1"


async def test_existing_user_is_logged_in_and_key_refreshed(db_session):
    first = await upsert_user_from_session(db_session, "alice", "sk1", mode="open", allowlist=[])
    again = await upsert_user_from_session(db_session, "alice", "sk2", mode="open", allowlist=[])
    assert again.id == first.id
    assert again.lastfm_session_key == "sk2"
    assert again.disconnected is False
    count = (await db_session.execute(select(func.count()).select_from(User))).scalar_one()
    assert count == 1


async def test_second_user_not_admin(db_session):
    await upsert_user_from_session(db_session, "alice", "sk1", mode="open", allowlist=[])
    bob = await upsert_user_from_session(db_session, "bob", "sk2", mode="open", allowlist=[])
    assert bob.is_admin is False


async def test_new_user_denied_when_not_on_allowlist(db_session):
    with pytest.raises(RegistrationDenied):
        await upsert_user_from_session(
            db_session, "mallory", "sk", mode="allowlist", allowlist=["alice"]
        )
