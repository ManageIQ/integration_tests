# -*- coding: utf-8 -*-
# pylint: disable=W0621
import pytest
from unittestzero import Assert
from utils.wait import wait_for, TimedOutError
import time

pytestmark = [
    pytest.mark.nondestructive,
    pytest.mark.skip_selenium,
]


class Incrementor():
    value = 0

    def i_sleep_a_lot(self):
        time.sleep(3)
        self.value += 1
        return self.value


def test_simple_wait():
    incman = Incrementor()
    ec, tc = wait_for(incman.i_sleep_a_lot,
                      fail_condition=0)
    print "Function output %s in time %s " % (ec, tc)
    Assert.less(tc, 4, "Should take less than 4 seconds")


def test_lambda_wait():
    incman = Incrementor()
    ec, tc = wait_for(lambda self: self.i_sleep_a_lot() > 2,
                      [incman])
    print "Function output %s in time %s " % (ec, tc)
    Assert.less(tc, 12, "Should take less than 12 seconds")


def test_lambda_long_wait():
    incman = Incrementor()
    Assert.raises(TimedOutError,
                  wait_for,
                  lambda self: self.i_sleep_a_lot() > 10,
                  [incman],
                  num_sec=10,
                  message="waiting for sleepy head")
