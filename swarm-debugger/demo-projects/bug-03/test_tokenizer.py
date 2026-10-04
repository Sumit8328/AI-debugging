import pytest
from tokenizer import extract_tags


def test_hashtag_extraction():
    assert extract_tags("Deploying #swarm to production") == ["swarm"]


def test_bracket_tag_extraction():
    assert extract_tags("Analyzing bug in [module_kernel]") == ["module_kernel"]


def test_multiple_mixed_tags():
    tags = extract_tags("Check [auth_v2] and #security")
    assert "auth_v2" in tags
    assert "security" in tags


def test_multiple_bracket_tags():
    # Greedy regex causes all bracketed items to merge into a single invalid string
    assert extract_tags("[first] and [second]") == ["first", "second"]
