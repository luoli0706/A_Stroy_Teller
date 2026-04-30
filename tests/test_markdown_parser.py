"""统一 Markdown 解析器测试。"""

import pytest
from app.markdown_utils import parse_markdown_header


class TestParseMarkdownHeader:
    def test_standard_front_matter(self):
        text = (
            "---\n"
            "story_id: my_story\n"
            "role_id: TestRole\n"
            "run_id: 42\n"
            "---\n"
            "## Story Content\n"
            "Once upon a time...\n"
        )
        meta = parse_markdown_header(text)
        assert meta["story_id"] == "my_story"
        assert meta["role_id"] == "TestRole"
        assert meta["run_id"] == "42"

    def test_no_delimiters(self):
        text = (
            "Topic: space exploration\n"
            "Style: sci-fi\n"
            "Some prose here...\n"
        )
        meta = parse_markdown_header(text)
        assert meta["topic"] == "space exploration"
        assert meta["style"] == "sci-fi"

    def test_empty_text(self):
        assert parse_markdown_header("") == {}

    def test_no_headers(self):
        text = "Just a plain paragraph.\nAnother line.\n"
        assert parse_markdown_header(text) == {}

    def test_key_normalization(self):
        text = (
            "---\n"
            "Story Id: uppercase\n"
            "Character Name: John Doe\n"
            "---\n"
        )
        meta = parse_markdown_header(text)
        assert "story_id" in meta
        assert meta["story_id"] == "uppercase"
        assert "character_name" in meta
        assert meta["character_name"] == "John Doe"

    def test_front_matter_terminates(self):
        text = (
            "---\n"
            "key: value\n"
            "---\n"
            "not_a_key: not_parsed\n"
        )
        meta = parse_markdown_header(text)
        assert "key" in meta
        assert "not_a_key" not in meta

    def test_extra_colons_in_value(self):
        text = "url: https://example.com:8080/path\n"
        meta = parse_markdown_header(text)
        assert meta["url"] == "https://example.com:8080/path"
