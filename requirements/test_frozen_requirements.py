try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path
import pytest

HERE = Path(__file__).resolve().parent


def reqs(file):
    with file.open() as fp:
        return dict(x.strip().split("==") for x in fp if "==" in x)


@pytest.mark.parametrize("pyver", ["py2", "py3"])
def test_match_files(pyver):
    frozen = reqs(HERE.joinpath("frozen.{pyver}.txt".format(pyver=pyver)))
    frozen_doc = reqs(HERE.joinpath("frozen_docs.{pyver}.txt".format(pyver=pyver)))
    expected_frozen_doc = {k: v for k, v in frozen.items() if k in frozen_doc}
    assert expected_frozen_doc == frozen_doc
