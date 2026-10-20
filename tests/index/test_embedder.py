import urllib.error

import pytest

from pmem.index.embedder import _NoRedirect, embed_url, make_embedder


def test_only_loopback_and_official_openai_are_allowed(monkeypatch):
    monkeypatch.delenv("PMEM_EMBED_ALLOW_REMOTE", raising=False)
    assert embed_url("http://127.0.0.1:11434")[1] == "local"
    assert embed_url("http://localhost:11434/")[1] == "local"
    assert embed_url("http://[::1]:11434")[1] == "local"
    assert embed_url("https://api.openai.com/v1")[1] == "official"
    assert embed_url("https://evil.example/v1") is None
    assert embed_url("http://api.openai.com/v1") is None
    assert embed_url("http://169.254.169.254/") is None
    assert embed_url("http://localhost.evil.com") is None
    assert embed_url("file:///etc/passwd") is None
    assert embed_url("http://user:pw@127.0.0.1") is None


def test_remote_url_is_refused_and_does_not_read_ambient_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-ambient")
    monkeypatch.delenv("PMEM_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PMEM_EMBED_ALLOW_REMOTE", raising=False)
    embedder, problem = make_embedder({"backend": "openai", "base_url": "https://evil.example/v1", "model": "m"})
    assert embedder is None
    assert "PMEM_EMBED_ALLOW_REMOTE" in problem
    assert "sk-ambient" not in problem


def test_official_endpoint_can_use_ambient_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-ambient")
    monkeypatch.delenv("PMEM_OPENAI_API_KEY", raising=False)
    embedder, problem = make_embedder({"backend": "openai", "base_url": "https://api.openai.com/v1", "model": "m"})
    assert problem is None
    assert embedder._api_key == "sk-ambient"


def test_explicit_remote_uses_only_the_pmem_key(monkeypatch):
    monkeypatch.setenv("PMEM_EMBED_ALLOW_REMOTE", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-ambient")
    monkeypatch.setenv("PMEM_OPENAI_API_KEY", "sk-pmem")
    embedder, problem = make_embedder({"backend": "openai", "base_url": "https://embed.example/v1", "model": "m"})
    assert problem is None
    assert embedder._api_key == "sk-pmem"
    assert embedder.base_url == "https://embed.example/v1"


def test_local_openai_does_not_send_the_ambient_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-ambient")
    monkeypatch.setenv("PMEM_OPENAI_API_KEY", "sk-pmem")
    embedder, problem = make_embedder({"backend": "openai", "base_url": "http://127.0.0.1:8080/v1", "model": "m"})
    assert problem is None
    assert embedder._api_key == "sk-pmem"


def test_ollama_defaults_to_localhost(monkeypatch):
    monkeypatch.delenv("PMEM_EMBED_ALLOW_REMOTE", raising=False)
    embedder, problem = make_embedder({"backend": "ollama", "model": "bge-m3"})
    assert problem is None
    assert embedder.base_url == "http://localhost:11434"


def test_embed_request_refuses_redirect():
    with pytest.raises(urllib.error.HTTPError):
        _NoRedirect().redirect_request(None, None, 302, "found", {}, "https://evil.example")
