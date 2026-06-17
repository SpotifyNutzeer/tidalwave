from tidalwave.lastfm.signing import sign


def test_sign_concatenates_sorted_params_plus_secret():
    # params {b:2, a:1}, secret "S" -> md5("a1b2S")
    import hashlib

    expected = hashlib.md5("a1b2S".encode("utf-8")).hexdigest()
    assert sign({"b": "2", "a": "1"}, secret="S") == expected


def test_sign_excludes_format_and_callback():
    import hashlib

    expected = hashlib.md5("a1S".encode("utf-8")).hexdigest()
    assert sign({"a": "1", "format": "json", "callback": "x"}, secret="S") == expected
