import subprocess

from setuptools import setup
from setuptools.command.sdist import sdist


class BuildProtos(sdist):
    """
    Build the gRPC source files and the dots binaries. They get included in the
    source distribution because it's a nightmare to compile all of the gRPC C++
    dependencies during the bdist_wheel step.
    """

    def run(self):
        subprocess.run("make protos", shell=True, check=True)
        super().run()


setup(
    cmdclass={
        "sdist": BuildProtos,
    },
)
