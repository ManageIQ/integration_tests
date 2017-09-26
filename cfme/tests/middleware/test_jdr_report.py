import pytest

from datetime import datetime

from cfme.middleware.provider.hawkular import HawkularProvider
from cfme.utils import testgen
from cfme.utils.version import current_version
from jdr_report_methods import verify_report_ready
from server_methods import (
    get_eap_server,
    get_hawkular_server,
    get_domain_server,
    get_eap_container_server,
    verify_server_running)
from cfme.middleware.jdr_report import JDRReportCollection


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.9'),
]
pytest_generate_tests = testgen.generate([HawkularProvider], scope="function")


def test_hawkular_jdr(provider):
    """Tests Hawkular server's Generate JDR button.

    Steps:
        * Chooses Hawkular server.
        * Clicks on Generate JDR button.
        * Verifies that JDR report is queued.
        * Waits until JDR Report is generated.
    """
    server = get_hawkular_server(provider)
    before_test_date = datetime.utcnow()
    server.generate_jdr()
    jdr_rc = JDRReportCollection(parent=server)
    verify_report_ready(jdr_rc, date_after=before_test_date)


def test_server_jdr(provider):
    """Tests EAP7 Standalone server's Generate JDR button.

    Steps:
        * Chooses EAP7 Standalone server.
        * Clicks on Generate JDR button.
        * Verifies that JDR report is queued.
        * Waits until JDR Report is generated.
    """
    server = get_eap_server(provider)
    verify_server_running(provider, server)
    before_test_date = datetime.utcnow()
    server.generate_jdr()
    jdr_rc = JDRReportCollection(parent=server)
    verify_report_ready(jdr_rc, date_after=before_test_date)


def test_domain_server_jdr(provider):
    """Tests EAP7 Domain mode server's Generate JDR button.

    Steps:
        * Chooses Server-one server.
        * Clicks on Generate JDR button.
        * Verifies that JDR report is queued.
        * Waits until JDR Report is generated.
    """
    server = get_domain_server(provider)
    verify_server_running(provider, server)
    before_test_date = datetime.utcnow()
    server.generate_jdr()
    jdr_rc = JDRReportCollection(parent=server)
    verify_report_ready(jdr_rc, date_after=before_test_date)


def test_container_server_jdr(provider):
    """Tests Container based EAP7 server's Generate JDR button.

    Steps:
        * Chooses container based server.
        * Clicks on Generate JDR button.
        * Verifies that JDR report is queued.
        * Waits until JDR Report is generated.
    """
    server = get_eap_container_server(provider)
    verify_server_running(provider, server)
    before_test_date = datetime.utcnow()
    server.generate_jdr()
    jdr_rc = JDRReportCollection(parent=server)
    verify_report_ready(jdr_rc, date_after=before_test_date)
