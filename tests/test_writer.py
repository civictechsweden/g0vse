from services.writer import Writer


def test_write_json_adds_final_newline(tmp_path):
    output = tmp_path / "output.json"

    Writer.write_json({"name": "räksmörgås"}, output)

    assert output.read_text(encoding="utf-8") == ('{\n    "name": "räksmörgås"\n}\n')


def test_write_md_normalizes_trailing_whitespace_and_blank_lines(tmp_path):
    output = tmp_path / "output.md"

    Writer.write_md("# Heading  \n\nContent  \n\n\n", output)

    assert output.read_text(encoding="utf-8") == "# Heading\n\nContent\n"


def test_normalize_md_matches_write_md_output(tmp_path):
    output = tmp_path / "output.md"
    markdown = "# Heading  \n\nContent  \n\n\n"

    Writer.write_md(markdown, output)

    assert output.read_text(encoding="utf-8") == Writer.normalize_md(markdown)
