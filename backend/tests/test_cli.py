from tidalwave import cli


def test_cli_exposes_poll_and_backfill_entrypoints():
    assert callable(cli.poll)
    assert callable(cli.backfill)
