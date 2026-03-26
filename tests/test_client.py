from dokploy_ctl.client import load_config, make_client


def test_load_config_success(config_dir):
    url, token = load_config(config_dir)
    assert url == "https://dokploy.example.com"
    assert token == "test-token-123"


def test_load_config_strips_trailing_slash(config_dir):
    (config_dir / "url").write_text("https://example.com/  \n")
    url, _ = load_config(config_dir)
    assert url == "https://example.com"


def test_load_config_missing_files(empty_config_dir):
    import pytest

    with pytest.raises(SystemExit):
        load_config(empty_config_dir)


def test_load_config_rejects_invalid_url(tmp_path):
    import pytest

    (tmp_path / "url").write_text("not-a-url\n")
    (tmp_path / "token").write_text("tok123\n")
    with pytest.raises(SystemExit):
        load_config(tmp_path)


def test_load_config_rejects_empty_token(tmp_path):
    import pytest

    (tmp_path / "url").write_text("https://example.com\n")
    (tmp_path / "token").write_text("  \n")
    with pytest.raises(SystemExit):
        load_config(tmp_path)


def test_make_client_sets_headers():
    client = make_client("https://example.com", "tok123")
    assert client.headers["x-api-key"] == "tok123"
    assert "json" in client.headers["content-type"]


def test_make_client_respects_insecure_env(monkeypatch):
    monkeypatch.setenv("DOKPLOY_INSECURE", "1")
    client = make_client("https://example.com", "tok123")
    # Client should be created without error when DOKPLOY_INSECURE=1
    assert client.headers["x-api-key"] == "tok123"


def test_make_client_default_verify(monkeypatch):
    monkeypatch.delenv("DOKPLOY_INSECURE", raising=False)
    client = make_client("https://example.com", "tok123")
    assert client.headers["x-api-key"] == "tok123"
