# register the non_destructive marker
# for use on tests that are non-destructive to the appliance, and can be run concurrently


def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        'non_destructive: mark tests that are non-destructive to the appliance'
    )
