"""Marker definitions for upgrade testing"""
from cfme.fixtures.pytest_store import store


# Add Marker
def pytest_configure(config):
    config.addinivalue_line("markers", "post_upgrade: Mark test for post upgrade testing")


# Filtering options
def pytest_addoption(parser):
    group = parser.getgroup("cfme")
    group.addoption(
        "--upgrade-appliance",
        dest="upgrade_appliance",
        action="store_true",
        default=False,
        help="Upgrade an appliance before tests are run.",
    )
    group.addoption(
        "--upgrade-to",
        dest="upgrade_to",
        action="store",
        default="5.11.z",
        help="Supported versions 5.9.z, 5.10.z, 5.11.z (.z means latest and default is 5.11.z)",
    )


def pytest_sessionstart(session):
    if store.parallelizer_role == "master":
        return
    if not session.config.getoption("upgrade_appliance"):
        return
    upgrade_to = session.config.getoption("upgrade_to")
    appliance = store.current_appliance
    store.write_line(
        f"Initiating appliance upgrade from '{appliance.version.vstring}' to '{upgrade_to}'"
    )
    appliance.upgrade(upgrade_to=upgrade_to, reboot=True)
    store.write_line("Appliance upgrade finished...")
