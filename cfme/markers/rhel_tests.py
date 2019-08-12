# register the rhel_testing marker
# for use on tests that deal directly with the OS that MIQ/CFME is running in


def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        'rhel_testing: mark tests that deal with the base OS directly'
    )
