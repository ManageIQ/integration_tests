from cfme.utils.wait import wait_for


named_lambda = lambda: False


def normal_everyday_func():
    return False


def test_wait_for_anonymous_lambda():
    wait_for(lambda: False, num_sec=.1)


def test_wait_for_named_lambda():
    wait_for(named_lambda, num_sec=.1)


def test_wait_for_normal_everyday_func():
    wait_for(normal_everyday_func, num_sec=.1)
