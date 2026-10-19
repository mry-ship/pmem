import pytest

from pmem.core.secrets import find_secrets


@pytest.mark.parametrize("text", [
    "SECRET_KEY='django-insecure-abc'",
    "DB_PASSWORD=abc12345",
    "access_token: ghx12345678",
    'client_secret="a1b2c3d4e5"',
    "aws_secret_access_key=wJalrXUtnFEMI1K7MDENG",
    "password: P@ssw0rd!x",
    "api_key = sk_live_abcdefghijklmnop 才能访问",
    '{"token": "abcdefgh12"}',
    "密码：Abc12345",
    "password=abc12345才能登录",
])
def test_secrets_are_found(text):
    assert find_secrets(text)


@pytest.mark.parametrize("text", [
    "token = getToken()",
    "password = hash_password(raw)",
    "密码：必须包含大小写字母和数字",
    "token = request.headers",
    "max_tokens = 4096",
    "password == other",
    "secret = settings.SECRET_KEY_FROM_ENVIRONMENT",
    'JSON 的 "token": 也漏；又把这些正常的中文说明当成了密钥',
    'token: "这是一段很长的中文说明文字"',
])
def test_code_and_rules_about_secrets_are_not_flagged(text):
    assert find_secrets(text) == []
