# -*- coding: utf-8 -*-
# pylint: disable=W0621
import pytest
import time
from utils.wait import wait_for, TimedOutError

pytestmark = [
    pytest.mark.nondestructive,
    pytest.mark.skip_selenium,
]


class Incrementor():
    value = 0

    def i_sleep_a_lot(self):
        time.sleep(.1)
        self.value += 1
        return self.value


def test_simple_wait():
    incman = Incrementor()
    ec, tc = wait_for(incman.i_sleep_a_lot,
                      fail_condition=0,
                      delay=.05)
    print "Function output %s in time %s " % (ec, tc)
    assert tc < 1, "Should take less than 1 seconds"


def test_lambda_wait():
    incman = Incrementor()
    ec, tc = wait_for(lambda self: self.i_sleep_a_lot() > 10,
                      [incman],
                      delay=.05)
    print "Function output %s in time %s " % (ec, tc)
    assert tc < 2, "Should take less than 2 seconds"


def test_lambda_long_wait():
    incman = Incrementor()
    with pytest.raises(TimedOutError):
        wait_for(lambda self: self.i_sleep_a_lot() > 10, [incman], num_sec=1, message="this fails")
