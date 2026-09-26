from services.writer import Writer


def test_write_json_adds_final_newline(tmp_path):
    output = tmp_path / "output.json"

    Writer.write_json({"name": "räksmörgås"}, output)

    assert output.read_text(encoding="utf-8") == ('{\n    "name": "räksmörgås"\n}\n')


def test_format_md_removes_trailing_whitespace_and_blank_lines(tmp_path):
    output = tmp_path / "output.md"

    Writer.write_md(Writer.format_md("# Heading   \n\nContent   \n\n\n"), output)

    assert output.read_text(encoding="utf-8") == "# Heading\n\nContent\n"


def test_format_md_handles_layout_and_is_idempotent(tmp_path):
    output = tmp_path / "output.md"
    markdown = "Before\n# Heading\nContent\n"

    formatted = Writer.format_md(markdown)
    Writer.write_md(formatted, output)

    assert output.read_text(encoding="utf-8") == "Before\n\n# Heading\n\nContent\n"
    assert Writer.format_md(formatted) == formatted
