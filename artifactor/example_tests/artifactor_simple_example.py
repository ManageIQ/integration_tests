import pytest

from cfme.utils.log import logger as log


def test_pass():
    log.info("pass")


@pytest.mark.skip(reason="example")
def test_skip():
    pass


def test_skip_imp():
    log.info("skip")
    pytest.skip("example")


def test_fail():
    log.info("fail")
    raise ValueError()
