from __future__ import annotations

import re

DEFAULT_PATTERNS: dict[str, str] = {
    "私钥": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "AWS 访问密钥": r"\bAKIA[0-9A-Z]{16}\b",
    "GitHub 令牌": r"\bgh[pousr]_[A-Za-z0-9]{30,}\b",
    "Slack 令牌": r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b",
    "JWT": r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
    # 键名可带前后缀（SECRET_KEY、DB_PASSWORD、access_token）。值只认可见 ASCII（冒号后面的中文说明不算；
    # 不能写成排除 \u0080-\uffff，忽略大小写时 ſ、K 会折叠成 s、k，把普通字母也排除掉）：带引号；
    # 或不带引号时含数字、或够长且不含点，并且不是函数调用（hash_password(raw)）、属性访问（request.headers）
    "密钥赋值": r"(?i)(?<![A-Za-z0-9])\w*?(?:api[_-]?key|secret|token|passwd|password|pwd)\w*['\"]?\s*[:=]\s*"
                r"(?:['\"][!#-&(-~]{8,}['\"]|(?:(?=[!#-&(-~]*\d)[!#-&*+\--:<-~]{8,}"
                r"|[!#-&*+\-/-:<-~]{16,})(?=[\s,;)]|[^\x00-\x7f]|$))",
    "中文密码": r"密码\s*[:：=]\s*[!-~]{6,}",
}


def find_secrets(text: str, extra: list[str] | None = None) -> list[str]:
    """返回命中描述，如“密钥赋值（第 12 个字符起）”；没有命中返回空列表。"""
    patterns = dict(DEFAULT_PATTERNS)
    for index, pattern in enumerate(extra or []):
        patterns[f"自定义规则 {index + 1}"] = pattern
    hits = []
    for name, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            hits.append(f"{name}（第 {match.start() + 1} 个字符起）")
    return hits
