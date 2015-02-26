import pytest
from utils import db
from utils import providers
from utils import testgen
from utils import conf
import time
from cfme.configure.configuration import candu

pytestmark = [
    pytest.mark.meta(
        server_roles="+ems_metrics_coordinator +ems_metrics_collector +ems_metrics_processor")
]

pytest_generate_tests = testgen.generate(testgen.provider_by_type, None)


@pytest.yield_fixture(scope="module")
def enable_candu():
    try:
        candu.enable_all()
        yield
    finally:
        candu.disable_all()


# blow away all providers when done - collecting metrics for all of them is
# too much
@pytest.fixture
def handle_provider(provider_key):
    providers.clear_providers()
    providers.setup_provider(provider_key)


def test_metrics_collection(handle_provider, provider_key, provider_crud, enable_candu):
    """check the db is gathering collection data for the given provider

    Metadata:
        test_flag: metrics_collection
    """
    metrics_tbl = db.cfmedb()['metrics']
    mgmt_systems_tbl = db.cfmedb()['ext_management_systems']

    # the id for the provider we're testing
    mgmt_system_id = db.cfmedb().session.query(mgmt_systems_tbl).filter(
        mgmt_systems_tbl.name == conf.cfme_data.get('management_systems', {})[provider_key]['name']
    ).first().id

    start_time = time.time()
    metric_count = 0
    timeout = 900.0  # 15 min
    while time.time() < start_time + timeout:
        last_metric_count = metric_count
        print "name: %s, id: %s, metrics: %s" % (provider_key,
                                                mgmt_system_id, metric_count)
        # count all the metrics for the provider we're testing
        metric_count = db.cfmedb().session.query(metrics_tbl).filter(
            metrics_tbl.parent_ems_id == mgmt_system_id
        ).count()

        # collection is working if increasing
        if metric_count > last_metric_count and last_metric_count > 0:
            return
        else:
            time.sleep(15)

    if time.time() > start_time + timeout:
        raise Exception("Timed out waiting for metrics to be collected")
