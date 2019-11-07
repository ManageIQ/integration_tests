"""
serial: Marker for marking test modules as "serial" tests. Serial is in quotes because this is not
        meant to guarantee that tests will run in a specific order but instead meant to make sure
        that all the tests in the test module will be sent to a single slave.

        The parallelizer is designed to divy up tests to slaves according to their parametrization.
        So tests with similar parameters end up going to the same slave. The problem this marker
        seeks to address is when the same fixture is evaluated on multiple slaves. When the auth
        tests were changed to use a temp appliance, this resulted in a new temp appliance being
        pulled for each slave that the tests were sent to. This created an unnecessary load on
        sprout and resulted in test errors due to not receiving an appliance.

        IMPORTANT: The serial marker SHOULD NOT be used on provider parametrized test cases, this
        will result in lengthy test runs due to having to constantly setup and tear down providers.
"""


def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        'serial: Mark a test case to run serially (all parameters on a single appliance)'
    )
