from pathlib import Path

import cssutils
import minify_html
from docutils.core import publish_string
from docutils.writers import _html_base
from docutils.writers.html5_polyglot import Writer
from myst_parser.docutils_ import Parser
from pygments.formatters import get_formatter_by_name


class MyTranslator(_html_base.HTMLTranslator):
    def __init__(self, document):
        super().__init__(document)
        fmter = get_formatter_by_name("html")
        styledefs = fmter.get_style_defs("")
        css = cssutils.parseString(styledefs)
        self.pygments = {
            r.selectorText[1:]: r.style.cssText
            for r in css.cssRules
            if isinstance(r, cssutils.css.CSSStyleRule)
        }

    def visit_literal(self, node):
        self.body.append(self.starttag(node, "code", "", CLASS=""))

    def depart_literal(self, node):
        self.body.append("</code>")

    def visit_inline(self, node):
        cl = node.get("classes")[0]
        style = self.pygments.get(cl, "")
        self.body.append(f"""<span style="{style}">""")

    def depart_inline(self, node):
        self.body.append("""</span>""")

    def visit_table(self, node):
        atts = {"classes": self.settings.table_style.replace(",", " ").split()}
        if "align" in node:
            atts["classes"].append("align-%s" % node["align"])
        if "width" in node:
            atts["style"] = "width: %s;" % node["width"]

        # atts["style"] = atts.get("style", "") + "border: 10px;"
        atts["border"] = "1px"

        tag = self.starttag(node, "table", **atts)
        self.body.append(tag)

    def depart_table(self, node):
        self.body.append("</table>\n")
        self.report_messages(node)


class MyWriter(_html_base.Writer):
    supported = Writer.supported + ("canvas",)
    default_template = Path("template.txt")

    def __init__(self):
        super().__init__()
        self.translator_class = MyTranslator


def md_to_canvas_html(source):
    """
    Convert Markdown into HTML that's suitable for Canvas LMS
    """

    output = publish_string(
        source=source,
        writer=MyWriter(),
        settings_overrides={
            "template": Path(__file__).parent / "canvas_html_template.txt",
            "myst_enable_extensions": ["deflist", "colon_fence"],
            "embed_stylesheet": False,
        },
        parser=Parser(),
    )

    return minify_html.minify(
        code=output.decode("utf-8"),
    )
