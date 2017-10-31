"""rhv(tier_number): Run only tests marked with RHV tier, e.g. rhv2.

This marker is used for purposes of RHV - CFME integration.

Tests can be marked like this:

.. code-block:: python

    @pytest.mark.rhv2
    def test_something():
        assert True

Usage on CLI::

    pytest -m 'rhv1'  # Run only tier 1
    pytest -m 'rhv1 or rhv2 or rhv3'  # Run all the tiers
    pytest -m 'not rhv3'  # Run all test methods except for RHV tier 3
    pytest -m 'not rhv1 and not rhv2 and not rhv3'  # Run everything that is not marked with rhv1-3
"""


def pytest_configure(config):
    config.addinivalue_line("markers", __doc__.splitlines()[0])
