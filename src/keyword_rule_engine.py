"""
关键词判断引擎：单组 OR 逻辑，命中任意关键词即推荐。
支持正则 (/pattern/) 和排除词 (-keyword 或 -/pattern/)。
"""
import re
from typing import Any, Dict, List, Optional, Tuple


_ASCII_TOKEN_KEYWORD_PATTERN = re.compile(r"^[a-z0-9 ]+$")
_ASCII_TOKEN_BOUNDARY = r"[a-z0-9]"


def normalize_text(value: str) -> str:
    return " ".join((value or "").lower().split())


def _collect_text_fragments(value: Any, bucket: List[str]) -> None:
    if value is None:
        return
    if isinstance(value, str):
        text = value.strip()
        if text:
            bucket.append(text)
        return
    if isinstance(value, (int, float, bool)):
        bucket.append(str(value))
        return
    if isinstance(value, dict):
        for item in value.values():
            _collect_text_fragments(item, bucket)
        return
    if isinstance(value, list):
        for item in value:
            _collect_text_fragments(item, bucket)


def build_search_text(record: Dict[str, Any]) -> str:
    fragments: List[str] = []
    product_info = record.get("商品信息", {})
    seller_info = record.get("卖家信息", {})

    _collect_text_fragments(product_info.get("商品标题"), fragments)
    _collect_text_fragments(product_info, fragments)
    _collect_text_fragments(seller_info, fragments)

    return normalize_text(" ".join(fragments))


class _Keyword:
    __slots__ = ("raw", "is_regex", "is_exclude", "pattern", "_literal")

    def __init__(self, raw: str):
        self.raw = raw
        self.is_regex = False
        self.is_exclude = False
        self.pattern: Optional[re.Pattern] = None
        self._literal: str = ""
        self._compile(raw.strip())

    def _compile(self, s: str) -> None:
        if s.startswith("-"):
            self.is_exclude = True
            s = s[1:].strip()

        if s.startswith("/") and s.endswith("/") and len(s) >= 2:
            inner = s[1:-1]
            if inner:
                try:
                    self.pattern = re.compile(inner, re.IGNORECASE)
                    self.is_regex = True
                    return
                except re.error:
                    pass  # fall through to literal matching

        self._literal = normalize_text(s)

    def matches(self, normalized_text: str) -> bool:
        if self.is_regex:
            return self.pattern.search(normalized_text) is not None
        if _uses_ascii_token_match(self._literal):
            pattern = rf"(?<!{_ASCII_TOKEN_BOUNDARY}){re.escape(self._literal)}(?!{_ASCII_TOKEN_BOUNDARY})"
            return re.search(pattern, normalized_text) is not None
        return self._literal in normalized_text


def _uses_ascii_token_match(keyword: str) -> bool:
    return bool(keyword) and _ASCII_TOKEN_KEYWORD_PATTERN.fullmatch(keyword) is not None


def _parse_keyword(raw: str) -> Optional[_Keyword]:
    kw = _Keyword(raw)
    has_literal = bool(kw._literal)
    has_regex = kw.is_regex
    if not has_literal and not has_regex:
        return None
    return kw


def _normalize_keywords(values: List[str]) -> List[_Keyword]:
    seen = set()
    result: List[_Keyword] = []
    for raw in values:
        text = str(raw).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        kw = _parse_keyword(text)
        if kw is not None:
            result.append(kw)
    return result


def evaluate_keyword_rules(keywords: List[str], search_text: str) -> Dict[str, Any]:
    normalized_text = normalize_text(search_text)
    parsed = _normalize_keywords(keywords)

    if not normalized_text:
        return {
            "analysis_source": "keyword",
            "is_recommended": False,
            "reason": "可匹配文本为空，关键词规则无法执行。",
            "matched_keywords": [],
            "excluded_by": [],
            "keyword_hit_count": 0,
        }

    if not parsed:
        return {
            "analysis_source": "keyword",
            "is_recommended": False,
            "reason": "未配置关键词规则。",
            "matched_keywords": [],
            "excluded_by": [],
            "keyword_hit_count": 0,
        }

    exclude_keywords = [kw for kw in parsed if kw.is_exclude]
    include_keywords = [kw for kw in parsed if not kw.is_exclude]

    # 排除规则优先：命中任意排除词则直接拒绝
    excluded_by = [kw.raw for kw in exclude_keywords if kw.matches(normalized_text)]
    if excluded_by:
        return {
            "analysis_source": "keyword",
            "is_recommended": False,
            "reason": f"命中排除词：{', '.join(excluded_by)}",
            "matched_keywords": [],
            "excluded_by": excluded_by,
            "keyword_hit_count": 0,
        }

    matched_keywords = [kw.raw for kw in include_keywords if kw.matches(normalized_text)]
    hit_count = len(matched_keywords)
    is_recommended = hit_count > 0

    if is_recommended:
        reason = f"命中 {hit_count} 个关键词：{', '.join(matched_keywords)}"
    else:
        reason = "未命中任何关键词。"

    return {
        "analysis_source": "keyword",
        "is_recommended": is_recommended,
        "reason": reason,
        "matched_keywords": matched_keywords,
        "excluded_by": [],
        "keyword_hit_count": hit_count,
    }
