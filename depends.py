from typing import Annotated

import bleach_allowlist
import fastapi
import fastapi.security
import fastapi.templating
import markdown_it
import nh3
from fastapi.responses import HTMLResponse
from markupsafe import escape
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.lexers.special import TextLexer
from pygments.util import ClassNotFound

app = fastapi.FastAPI()

templates = fastapi.templating.Jinja2Templates(directory="templates")

formatter = HtmlFormatter(cssclass="highlight")


def highlight_code(code: str, lang: str, attrs: str) -> str:
    if not lang:
        return f"<pre><code>{escape(code)}</code></pre>"

    try:
        lexer = get_lexer_by_name(lang)
    except ClassNotFound:
        lexer = TextLexer()

    return highlight(code, lexer, formatter)


md_cleaner = nh3.Cleaner(
    tags=set(bleach_allowlist.markdown_tags) | {"div", "pre", "span", "code"},
    attributes={
        **{k: set(v) for k, v in bleach_allowlist.markdown_attrs.items()},
        "div": {"class"},
        "span": {"class"},
        "code": {"class"},
        "pre": {"class"},
    },
)
md_maker = markdown_it.MarkdownIt(
    "commonmark",
    {
        "html": False,
        "linkify": True,
        "typographer": True,
        "highlight": highlight_code,
    },
)


def render_markdown_sync(markdown_text: str) -> str:
    html = md_maker.render(markdown_text)
    return md_cleaner.clean(html)


@app.get("/markdown/styles.css")
async def markdown_styles():
    css = formatter.get_style_defs(".highlight")
    return HTMLResponse(css, media_type="text/css")


@app.post("/markdown/render", response_class=fastapi.responses.HTMLResponse)
async def render_markdown(
    markdown_text: Annotated[
        str,
        fastapi.Body(
            description="The markdown text to render as HTML",
            media_type="text/markdown",
        ),
    ],
) -> str:
    html = render_markdown_sync(markdown_text)
    return html


text = """# Hello, World!
This is an example of markdown text.

## This is a list
- Item 1
- Item 2

```python
def hello():
    print("Hello, World!")
```
"""


def mandate_api_key(
    key: Annotated[
        str,
        fastapi.Security(
            fastapi.security.APIKeyHeader(name="X-API-Key", auto_error=False)
        ),
    ],
) -> str:
    if key == "secret":
        return key

    raise fastapi.HTTPException(status_code=401, detail="Unauthorized")


@app.get("/markdown/example", response_class=fastapi.responses.HTMLResponse)
async def example_markdown(request: fastapi.Request) -> str:
    html = render_markdown_sync(text)
    return templates.TemplateResponse(
        "markdown.html", {"request": request, "content": html}
    )


@app.get("/protected", response_class=fastapi.responses.PlainTextResponse)
async def protected_route(api_key: Annotated[str, fastapi.Depends(mandate_api_key)]):
    return f"Access granted with API key: {api_key}"


@app.exception_handler(404)
def not_found_handler(request: fastapi.Request, exc: fastapi.HTTPException):
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
