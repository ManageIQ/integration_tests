import pytest

from fixtures.soft_assert import SoftAssertionError, _soft_assert_cm


# If we wanted to be super cool, we could use pytester and run a pytest session
# inside pytest to make sure the call-phase hook works. Instead of that...
# xfail! If this "xpasses", the call hook is broken. :(
@pytest.mark.xfail
def test_soft_assert_call_fails(soft_assert):
    soft_assert(None, "This test should xfail due to a SoftAssertionError")


def test_soft_assert_call_passes(soft_assert):
    soft_assert(True, "This test should pass")


def test_soft_assert(soft_assert):
    with pytest.raises(AssertionError) as exc:
        # Run the soft assert context manager by itself to make sure it's
        # working right
        with _soft_assert_cm():
            soft_assert(None)
            soft_assert(False, 'Value is False')
            soft_assert(True, 'Value is True')

    # the AssertionError is related to soft assertions
    assert isinstance(exc.value, SoftAssertionError)

    # the number of failed assertions is what we expect
    assert len(exc.value.failed_assertions) == 2

    exc_message = str(exc.value)
    # showing code context instead of the message where appropriate
    assert 'soft_assert(None)' in exc_message

    # showing the message when it's passed in
    assert 'Value is False' in exc_message

    # assertions that pass aren't reported
    assert 'Value is True' not in exc_message

    # assertions are cleared if soft_assert is used twice in a test
    with _soft_assert_cm():
        # if assertions aren't cleared, this will erroneously raise AssertionError
        pass
