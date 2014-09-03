#import pytest
#from utils import db
#from utils import providers
#from utils import conf
#import time
#from cfme.configure.configuration import candu

#pytestmark = [
#    pytest.mark.fixtureconf(server_roles="+ems_metrics_coordinator +ems_metrics_collector"
#                            " +ems_metrics_processor"),
#    pytest.mark.usefixtures('server_roles', 'setup_providers')
#]


#@pytest.fixture(scope="module")
#def setup_providers():
#    providers.setup_cloud_providers()
#    providers.setup_infrastructure_providers()
#    # also enable collection for the region
#    candu.enable_all()


#@pytest.mark.parametrize("provider", providers.list_all_providers())
#def test_metrics_collection(provider):
#    '''check the db is gathering collection data for the given provider'''
#
#    metrics_tbl = db.cfmedb['metrics']
#    mgmt_systems_tbl = db.cfmedb['ext_management_systems']
#
#    # the id for the provider we're testing
#    mgmt_system_id = db.cfmedb.session.query(mgmt_systems_tbl).filter(
#        mgmt_systems_tbl.name == conf.cfme_data['management_systems'][provider]['name']
#    ).first().id
#
#    start_time = time.time()
#    metric_count = 0
#    timeout = 900.0  # 15 min
#    while time.time() < start_time + timeout:
#        last_metric_count = metric_count
#        print "name: %s, id: %s, metrics: %s" % (provider,
#                                                 mgmt_system_id, metric_count)
#        # count all the metrics for the provider we're testing
#        metric_count = db.cfmedb.session.query(metrics_tbl).filter(
#            metrics_tbl.parent_ems_id == mgmt_system_id
#        ).count()
#
#        # collection is working if increasing
#        if metric_count > last_metric_count and last_metric_count > 0:
#            return
#        else:
#            time.sleep(15)
#
#    if time.time() > start_time + timeout:
#        raise Exception("Timed out waiting for metrics to be collected")
