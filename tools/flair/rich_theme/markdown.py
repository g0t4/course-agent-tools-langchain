from rich.console import Console
from rich.theme import Theme
from rich.markdown import Markdown

md_theme = Theme({
    # headings (clear hierarchy)
    "markdown.h1": "bold #e06c75",  # red-ish, strong anchor
    "markdown.h2": "bold #61afef",  # blue
    "markdown.h3": "bold #98c379",  # green
    "markdown.h4": "bold #c678dd",  # purple
    "markdown.h5": "bold #56b6c2",  # cyan
    "markdown.h6": "bold #abb2bf",  # muted

    # text emphasis
    "markdown.strong": "bold #ffffff",
    "markdown.emphasis": "italic #d19a66",

    # inline + blocks
    "markdown.code": "bold #e5c07b",  # inline code pops
    "markdown.block_code": "#abb2bf on #2c313c",  # subtle bg

    # structure
    "markdown.list": "#61afef",
    "markdown.item": "#abb2bf",
    "markdown.block_quote": "italic #5c6370",

    # links
    "markdown.link": "underline #61afef",
})

if __name__ == "__main__":
    console = Console(theme=md_theme)

    md = """
# Header 1
## Header 2

- item one
- item two

> this is a quote

Some **bold**, *italic*, and `inline code`
"""

    console.rule("GENERAL")

    console.print(Markdown(md))

    console.rule("TABLE")

    table_md = """
Here are the tools available to the web-researcher subagent, with their arguments:

| Tool | Arguments |
|---|---|
| **write_todos** | `todos` (array: `{content, status}`) |
| **ls** | `path` (absolute directory path) |
| **read_file** | `file_path`, `offset` (default 0), `limit` (default 100) |
| **write_file** | `file_path`, `content` |
| **edit_file** | `file_path`, `old_string`, `new_string`, `replace_all` (default false) |
| **glob** | `pattern`, `path` (default "/") |
| **grep** | `pattern`, `path`, `glob`, `output_mode` (default: files_with_matches) |
| **fetch** | `url`, `max_length` (default 5000), `start_index` (default 0), `raw` (default false) |

In total, **8 tools** — filesystem (6), web fetching (1), and task management (1).
"""

    console.print(Markdown(table_md))

