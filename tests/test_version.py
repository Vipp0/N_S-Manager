import re

from gilda_app.version import __version__


def test_version_is_major_minor_with_optional_patch():
    assert re.fullmatch(r"\d+\.\d+(\.\d+)?", __version__)
