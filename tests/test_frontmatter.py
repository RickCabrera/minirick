"""Tests de `minirick.frontmatter` — parser YAML + markdown body."""

from __future__ import annotations

import pytest

from minirick.frontmatter import FrontmatterError, dump, parse


def test_parse_basic_frontmatter() -> None:
    text = "---\ntitle: Hola\nstatus: todo\n---\n\n# Body"
    meta, body = parse(text)
    assert meta == {"title": "Hola", "status": "todo"}
    assert body == "# Body"


def test_parse_without_frontmatter_returns_original_text() -> None:
    text = "# Solo body, nada más"
    meta, body = parse(text)
    assert meta == {}
    assert body == text


def test_parse_invalid_yaml_raises() -> None:
    text = "---\ntitle: : : broken\n  - ugh\n---\nbody"
    with pytest.raises(FrontmatterError):
        parse(text)


def test_parse_preserves_unicode() -> None:
    text = "---\nname: Año\ndesc: 日本語\n---\nbody"
    meta, _ = parse(text)
    assert meta["name"] == "Año"
    assert meta["desc"] == "日本語"


def test_parse_frontmatter_must_be_mapping() -> None:
    text = "---\n- foo\n- bar\n---\nbody"
    with pytest.raises(FrontmatterError):
        parse(text)


def test_roundtrip_preserves_tools_list() -> None:
    meta = {
        "title": "Tarea",
        "tools": [
            {"type": "vscode", "path": "~/repos/x"},
            {"type": "browser", "url": "https://ejemplo.com"},
        ],
    }
    body = "# Contenido"
    serialized = dump(meta, body)
    parsed_meta, parsed_body = parse(serialized)
    assert parsed_meta == meta
    assert parsed_body.strip() == body.strip()


def test_dump_writes_unicode_raw() -> None:
    serialized = dump({"title": "Año nuevo"}, "# body")
    assert "Año nuevo" in serialized
    assert "\\u" not in serialized  # no escaping
