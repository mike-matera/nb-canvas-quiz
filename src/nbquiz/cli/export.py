"""
Export a test bank to canvas.
"""

from zipfile import ZipFile

from jinja2 import Environment, PackageLoader, select_autoescape

from nbquiz.testbank import bank

_template_env = Environment(
    loader=PackageLoader("nbquiz", package_path="resources/canvas"),
    autoescape=select_autoescape(),
    trim_blocks=True,
)


def add_args(parser):
    pass


def main(args):
    bank.load()
    with ZipFile("examtest.zip", "w") as zip:
        # Write the manifest
        manifest = _template_env.get_template("imsmanifest.xml")
        zip.writestr("imsmanifest.xml", manifest.render())

        # Write the assessment metadata
        assessment_meta = _template_env.get_template(
            "gf322aa7be67425e49e051ccd6a34f38c/assessment_meta.xml"
        )
        zip.writestr(
            "gf322aa7be67425e49e051ccd6a34f38c/assessment_meta.xml", assessment_meta.render()
        )

        # Write the assessment content
        assessment_content = _template_env.get_template(
            "gf322aa7be67425e49e051ccd6a34f38c/gf322aa7be67425e49e051ccd6a34f38c.xml"
        )
        zip.writestr(
            "gf322aa7be67425e49e051ccd6a34f38c/gf322aa7be67425e49e051ccd6a34f38c.xml",
            assessment_content.render(),
        )

        # Write the associated file
        assessment_content = _template_env.get_template("web_resources/Uploaded Media/final.ipynb")
        zip.writestr("web_resources/Uploaded Media/final.ipynb", assessment_content.render())
