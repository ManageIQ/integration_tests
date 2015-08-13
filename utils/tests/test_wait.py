# -*- coding: utf-8 -*-
# pylint: disable=W0621
import pytest
import time
from functools import partial
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
        wait_for(lambda self: self.i_sleep_a_lot() > 10, [incman],
                 num_sec=1, message="lambda_long_wait")


def test_partial():
    incman = Incrementor()
    func = partial(lambda: incman.i_sleep_a_lot() > 10)
    with pytest.raises(TimedOutError):
        wait_for(func,
                 num_sec=2, delay=1)


def test_callable_fail_condition():
    incman = Incrementor()
    with pytest.raises(TimedOutError):
        wait_for(
            incman.i_sleep_a_lot,
            fail_condition=lambda value: value <= 10, num_sec=2, delay=1)


def test_wait_decorator():
    incman = Incrementor()

    @pytest.wait_for(fail_condition=0, delay=.05)
    def a_test():
        incman.i_sleep_a_lot()
    print "Function output %s in time %s " % (a_test.out, a_test.duration)
    assert a_test.duration < 1, "Should take less than 1 seconds"


def test_wait_decorator_noparams():
    incman = Incrementor()

    @pytest.wait_for
    def a_test():
        return incman.i_sleep_a_lot() != 0
    print "Function output %s in time %s " % (a_test.out, a_test.duration)
    assert a_test.duration < 1, "Should take less than 1 seconds"


def test_nonnumeric_numsec_timedelta_via_string():
    incman = Incrementor()
    func = partial(lambda: incman.i_sleep_a_lot() > 10)
    with pytest.raises(TimedOutError):
        wait_for(func,
                 timeout="2s", delay=1)
