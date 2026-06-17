import pytest

from tidalwave.auth.session import SessionCodec


def test_roundtrip_encodes_and_decodes_user_id():
    codec = SessionCodec(secret="s3cr3t")
    token = codec.encode(42)
    assert codec.decode(token) == 42


def test_tampered_token_rejected():
    codec = SessionCodec(secret="s3cr3t")
    assert codec.decode("garbage.value.here") is None


def test_token_signed_with_other_secret_rejected():
    token = SessionCodec(secret="A").encode(1)
    assert SessionCodec(secret="B").decode(token) is None
