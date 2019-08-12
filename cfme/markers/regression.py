# register the regression marker
# for use on tests that dare written for regressions


def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        'regression: mark tests written for regressions'
    )
