"""
Convert markdown to Canvas friendly HTML.

Canvas does not allow for <style> tags inside of content boxes
and obviously no JS. The default Docutils HTML relies heavily on
classed <span> and <div> tags to produce a wide range of visual styles
that are not possible in Canvas.

TODO: Docutils inserts <aside> tags when there are errors. Mute them.
"""

from importlib.resources import files

import cssutils
import minify_html
from docutils.core import publish_string
from docutils.writers import _html_base
from docutils.writers.html5_polyglot import Writer
from myst_parser.docutils_ import Parser
from pygments.formatters import get_formatter_by_name

MYST_EXTENSIONS = [
    "replacements",
    "dollarmath",
    "amsmath",
    "substitution",
    "colon_fence",
    "deflist",
    "fieldlist",
    "attrs_inline",
    "attrs_block",
    "html_image",
]


class CanvasHTMLTranslator(_html_base.HTMLTranslator):
    """
    Vistor to produce the very simple HTML that Canvas needs.
    """

    def __init__(self, document):
        super().__init__(document)
        self._pia = False
        fmter = get_formatter_by_name("html")
        styledefs = fmter.get_style_defs("")
        css = cssutils.parseString(styledefs)
        self.pygments = {
            r.selectorText[1:]: r.style.cssText
            for r in css.cssRules
            if isinstance(r, cssutils.css.CSSStyleRule)
        }

    def visit_literal(self, node):
        style = ""
        if "pia" in node["classes"] and "invisible" in node["classes"]:
            style = "display:inline-block; overflow:hidden; width: 1px; height: 1px"
        self.body.append(
            self.starttag(node, "code", suffix="", style=style, CLASS="")
        )

    def depart_literal(self, node):
        if "pia" in node["classes"] and "invisible" not in node["classes"]:
            self.body.append(
                """<span style="display:inline-block; overflow:hidden; width: 1px; height: 1px">_</span>"""
            )
        self.body.append("</code>")

    def visit_inline(self, node):
        if "pia" in node["classes"]:
            style = "display:inline-block; overflow:hidden; width: 1px; height: 1px"
        else:
            try:
                cl = node.get("classes")[0]
                style = self.pygments.get(cl, "")
            except (IndexError, KeyError):
                style = ""
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


class CanvasHTMLWriter(_html_base.Writer):
    supported = Writer.supported + ("canvas",)

    def apply_template(self):
        """Do not assume template is a file."""
        subs = self.interpolation_dict()
        return self.document.settings.template % subs

    def __init__(self):
        super().__init__()
        self.translator_class = CanvasHTMLTranslator


def md_to_canvas_html(source):
    """
    Convert Markdown into HTML that's suitable for Canvas LMS
    """

    output = publish_string(
        source=source,
        writer=CanvasHTMLWriter(),
        settings_overrides={
            "template": files("nbquiz.resources")
            .joinpath("canvas_html_template.txt")
            .read_text(),
            "myst_enable_extensions": MYST_EXTENSIONS,
            "embed_stylesheet": False,
            "stylesheet_dirs": [],
        },
        parser=Parser(),
    )

    return minify_html.minify(
        code=output.decode("utf-8"),
    )
