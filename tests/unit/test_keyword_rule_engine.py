from src.keyword_rule_engine import build_search_text, evaluate_keyword_rules


def _sample_record():
    return {
        "商品信息": {
            "商品标题": "Sony A7M4 全画幅相机",
            "当前售价": "10000",
            "商品标签": ["验货宝", "包邮"],
        },
        "卖家信息": {
            "卖家昵称": "摄影器材店",
            "卖家个性签名": "可验机，支持同城面交",
        },
    }


def test_build_search_text_only_includes_product_fields():
    text = build_search_text(_sample_record())
    assert "sony a7m4" in text
    assert "验货宝" in text
    # 卖家信息不应出现在搜索文本中
    assert "摄影器材店" not in text
    assert "支持同城面交" not in text


def test_keyword_rules_or_match_any_keyword():
    text = build_search_text(_sample_record())
    result = evaluate_keyword_rules(["a7m4", "佳能"], text)
    assert result["is_recommended"] is True
    assert result["analysis_source"] == "keyword"
    assert result["keyword_hit_count"] == 1
    assert result["matched_keywords"] == ["a7m4"]


def test_keyword_rules_count_multiple_hits():
    text = build_search_text(_sample_record())
    result = evaluate_keyword_rules(["a7m4", "验货宝", "包邮"], text)
    assert result["is_recommended"] is True
    assert result["keyword_hit_count"] == 3


def test_keyword_rules_case_insensitive_contains():
    text = build_search_text(_sample_record())
    result = evaluate_keyword_rules(["SONY", "A7M4"], text)
    assert result["is_recommended"] is True
    assert result["keyword_hit_count"] == 2


def test_keyword_rules_no_match():
    text = build_search_text(_sample_record())
    result = evaluate_keyword_rules(["佳能", "单反"], text)
    assert result["is_recommended"] is False
    assert result["keyword_hit_count"] == 0


def test_keyword_rules_do_not_partially_match_alphanumeric_prefixes():
    result = evaluate_keyword_rules(["q1"], "富士 q1r5 旗舰相机")
    assert result["is_recommended"] is False
    assert result["keyword_hit_count"] == 0


def test_keyword_rules_still_match_full_alphanumeric_token():
    result = evaluate_keyword_rules(["q1r5"], "富士 q1r5 旗舰相机")
    assert result["is_recommended"] is True
    assert result["keyword_hit_count"] == 1


# --- Regex support ---


def test_regex_keyword_matches():
    result = evaluate_keyword_rules(["/Sony.*相机/"], build_search_text(_sample_record()))
    assert result["is_recommended"] is True
    assert result["matched_keywords"] == ["/Sony.*相机/"]


def test_regex_keyword_case_insensitive():
    result = evaluate_keyword_rules(["/sony.*相机/"], "SONY A7M4 全画幅相机")
    assert result["is_recommended"] is True


def test_regex_keyword_no_match():
    result = evaluate_keyword_rules(["/佳能|尼康/"], build_search_text(_sample_record()))
    assert result["is_recommended"] is False


def test_regex_keyword_alternation():
    result = evaluate_keyword_rules(["/sony|a7m4/"], build_search_text(_sample_record()))
    assert result["is_recommended"] is True
    assert result["keyword_hit_count"] == 1


# --- Negative / exclude keywords ---


def test_exclude_keyword_blocks_match():
    text = build_search_text(_sample_record())
    result = evaluate_keyword_rules(["a7m4", "-包邮"], text)
    assert result["is_recommended"] is False
    assert "-包邮" in result["excluded_by"]
    assert result["matched_keywords"] == []


def test_exclude_keyword_without_positive_match():
    text = build_search_text(_sample_record())
    result = evaluate_keyword_rules(["-佳能"], text)
    assert result["is_recommended"] is False
    assert result["excluded_by"] == []


def test_exclude_regex():
    result = evaluate_keyword_rules(["a7m4", "-/包邮|面交/"], build_search_text(_sample_record()))
    assert result["is_recommended"] is False
    assert "excluded_by" in result


def test_exclude_has_priority_over_include():
    result = evaluate_keyword_rules(["a7m4", "-a7m4"], build_search_text(_sample_record()))
    assert result["is_recommended"] is False
    assert result["excluded_by"] == ["-a7m4"]


# --- Mixed regex + exclude + literal ---


def test_mixed_literal_regex_exclude():
    """鹿乃场景：命中关键词但排除特定词"""
    result = evaluate_keyword_rules(
        ["鹿乃", "-鹿乃子", "-原神", "-保真"],
        "鹿乃 手办 保真 付邮送",
    )
    assert result["is_recommended"] is False
    assert "-保真" in result["excluded_by"]


def test_mixed_literal_regex_exclude_pass():
    """鹿乃场景：命中关键词且没有命中排除词"""
    result = evaluate_keyword_rules(
        ["鹿乃", "-鹿乃子", "-原神", "-保真"],
        "鹿乃 蓝牙耳机 全新未拆封",
    )
    assert result["is_recommended"] is True
    assert result["matched_keywords"] == ["鹿乃"]


def test_exclude_has_priority_multiple():
    result = evaluate_keyword_rules(
        ["鹿乃", "/手办|一番赏/", "-原神", "-保真", "-/付邮|送礼/"],
        "鹿乃 手办 保真 包邮",
    )
    assert result["is_recommended"] is False
    assert "-保真" in result["excluded_by"]
