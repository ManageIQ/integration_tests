import db
import pytest
import time, datetime

"""
Adds items to the database
"""
#TODO session.add_all([item1, item2, item3])
def session_manager(db_session, items):
    session = db_session
    if type(items) is list:
        for item in items:
            session.add(item)
    else:
        session.add(items)
    session.commit()

"""
Creates timestamps for items in the database
"""
def timestamp():
    ts = time.time()
    formated_ts = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S.%f")
    return formated_ts

"""
Add one management system
Infrastructure -> Management Systems
"""
@pytest.fixture # IGNORE:E1101
def db_setup_management_system(db_session, cfme_data):
    my_id = cfme_data.data["database"]["management_system"]["id"]
    my_name = cfme_data.data["database"]["management_system"]["name"]
    ts = timestamp()
    ms = db.ExtManagementSystem(id=my_id, name=my_name, hostname='10.16.120.152', ipaddress='10.16.120.152', created_on=ts, updated_on=ts, zone_id='1', type='EmsRedhat')
    session_manager(db_session, ms)

"""
Add multiple management systems
Infrastructure -> Management Systems
"""
@pytest.fixture
def db_setup_multiple_management_systems(db_session, cfme_data):
    i = 0
    count_of_management_systems = cfme_data.data["database"]["management_system"]["count"]
    my_name = cfme_data.data["database"]["management_system"]["name"]
    management_systems = []
    for i in range(0, int(count_of_management_systems)):
        ts = timestamp()
        name_of_ms = '%s_%s' % (my_name, i)
        ms = db.ExtManagementSystem(name=name_of_ms, emstype='test_emstype', hostname='10.16.120.152', ipaddress='10.16.120.152', created_on=ts, updated_on=ts, zone_id='1', type='EmsRedhat')
        management_systems.append(ms)
    session_manager(db_session, management_systems)

"""
Add one cluster
Infrastructure -> Cluster
"""
@pytest.fixture
def db_setup_cluster(db_session, cfme_data):
    my_id = cfme_data.data["database"]["cluster"]["id"]
    my_ems_id = cfme_data.data["database"]["cluster"]["management_system_id"]
    my_name = cfme_data.data["database"]["cluster"]["name"]
    ts = timestamp()
    cluster = db.EmCluster(id=my_id, ems_id=my_ems_id, name=my_name, created_on=ts, updated_on=ts, uid_ems='domain-c159')
    session_manager(db_session, cluster)

"""
Add multiple clusters
Infrastructure -> Clusters
"""
@pytest.fixture
def db_setup_multiple_clusters(db_session, cfme_data):
    i = 0
    count_of_clusters = cfme_data.data["database"]["cluster"]["count"]
    my_name = cfme_data.data["database"]["cluster"]["name"]
    clusters = []
    for i in range(0, count_of_clusters):
        ts = timestamp()
        name_of_cluster = '%s_%s' % (my_name, i)
        cluster = db.EmCluster(name=name_of_cluster, created_on=ts, updated_on=ts, uid_ems='domain-c159')
        clusters.append(cluster)
    session_manager(db_session, clusters)

"""
Add one datastore
Infrastructure -> Datastores
"""
@pytest.fixture
def db_setup_datastore(db_session, cfme_data):
    my_id = cfme_data.data["database"]["datastore"]["id"]
    my_name = cfme_data.data["database"]["datastore"]["name"]
    ts = timestamp()
    datastore = db.Storage(id=my_id, name=my_name, store_type='NFS', total_space='924491710464', free_space='820338753536', created_on=ts, updated_on=ts, multiplehostaccess='1', location='somewhere', master='FALSE')
    session_manager(db_session, datastore)

"""
Add multiple datastores
Infrastructure -> Datastores
"""
@pytest.fixture
def db_setup_multiple_datastores(db_session, cfme_data):
    i = 0
    count_of_datastores = cfme_data.data["database"]["datastore"]["count"]
    my_name = cfme_data.data["database"]["datastore"]["name"]
    datastores = []
    for i in range(0, count_of_datastores):
        ts = timestamp()
        name_of_datastore = '%s_%s' % (my_name, i)
        datastore = db.Storage(name=name_of_datastore, store_type='NFS', total_space='924491710464', free_space='820338753536', created_on=ts, updated_on=ts, multiplehostaccess='1', location='somewhere', master='FALSE')
        datastores.append(datastore)
    session_manager(db_session, datastores)

"""
Add one virtual machine
Services -> Virtual Machines
"""
@pytest.fixture
def db_setup_virtual_machine(db_session, cfme_data):
    my_cluster_id = cfme_data.data["database"]["virtual_machine"]["cluster_id"]
    my_ems_id = cfme_data.data["database"]["virtual_machine"]["management_system_id"]
    my_host_id = cfme_data.data["database"]["virtual_machine"]["host_id"]
    my_storage_id = cfme_data.data["database"]["virtual_machine"]["storage_id"]
    my_id = cfme_data.data["database"]["virtual_machine"]["id"]
    my_name = cfme_data.data["database"]["virtual_machine"]["name"]
    my_location = "somewhere/%s.vmx" % my_name
    ts = timestamp()
    vm = db.Vm(id=my_id, host_id=my_host_id, ems_id=my_ems_id, ems_cluster_id=my_cluster_id, storage_id=my_storage_id, vendor='redhat', name=my_name, location=my_location, created_on=ts, updated_on=ts, tools_status='toolsNotRunning', standby_action='checkpoint', power_state='on', state_changed_on=ts, previous_state='unknown', connection_state='connected', memory_reserve='0', memory_reserve_expand='FALSE', memory_limit='-1', memory_shares='40960', memory_shares_level='normal', cpu_reserve='0', cpu_reserve_expand='FALSE', cpu_limit='-1', cpu_shares='2000', cpu_shares_level='normal', template='FALSE', vdi='FALSE', linked_clone='FALSE', fault_tolerance='FALSE', type='VmRedhat')
    session_manager(db_session, vm)

"""
Add multiple virtual machines
Services -> Virtual Machines
"""
#TODO add ids and such
@pytest.fixture
def db_setup_multiple_virtual_machines(db_session, cfme_data):
    i = 0
    #count_of_virtual_machines = 3
    count_of_virtual_machines = cfme_data.data["database"]["virtual_machine"]["count"]
    virtual_machines = []
    my_name = cfme_data.data["database"]["virtual_machine"]["name"]
    for i in range (0, count_of_virtual_machines):
        ts = timestamp()
        name_of_virtual_machine =  '%s_%s' % (my_name, i)
        my_location = "somewhere/%s.vmx" % name_of_virtual_machine
        virtual_machine = db.Vm(vendor='vmware', name=name_of_virtual_machine, location=my_location, created_on=ts, updated_on=ts, tools_status='toolsNotRunning', standby_action='checkpoint', power_state='unknown', state_changed_on=ts, previous_state='unknown', connection_state='connected', memory_reserve='0', memory_reserve_expand='FALSE', memory_limit='-1', memory_shares='40960', memory_shares_level='normal', cpu_reserve='0', cpu_reserve_expand='FALSE', cpu_limit='-1', cpu_shares='2000', cpu_shares_level='normal', template='FALSE', vdi='FALSE', linked_clone='FALSE', fault_tolerance='FALSE', type='VmVmware')
        virtual_machines.append(virtual_machine)
    session_manager(db_session, virtual_machines)

#TODO red hat template fixture

"""
Add one template
Services -> Virtual Machines
"""
@pytest.fixture
def db_setup_template(db_session, cfme_data):
    ts = timestamp()
    my_name = cfme_data.data["database"]["template"]["name"]
    my_id = cfme_data.data["database"]["template"]["id"]
    my_ems_id = cfme_data.data["database"]["template"]["management_system_id"]
    my_location = 'somewhere/%s.vmtx' % my_name
    template = db.Vm(id=my_id, ems_id=my_ems_id, vendor='vmware', name=my_name, location=my_location, created_on=ts, updated_on=ts, tools_status='toolsNotRunning', standby_action='checkpoint', power_state='never', state_changed_on=ts, previous_state='unknown', connection_state='connected', memory_reserve='0', memory_reserve_expand='FALSE', memory_limit='-1', memory_shares='40960', memory_shares_level='normal', cpu_reserve='0', cpu_reserve_expand='FALSE', cpu_limit='-1', cpu_shares='2000', cpu_shares_level='normal', template='TRUE', vdi='FALSE', linked_clone='FALSE', fault_tolerance='FALSE', type='TemplateVmware')
    session_manager(db_session, template)

"""
Add multiple templates
Services -> Virtual Machines
"""
#TODO id
@pytest.fixture
def db_setup_multiple_templates(db_session, cfme_data):
    i = 0
    count_of_templates = cfme_data.data["database"]["template"]["count"]
    my_name = cfme_data.data["database"]["template"]["name"]
    templates = []
    for i in range (0, count_of_templates):
        ts = timestamp()
        name_of_template = '%s_%s' % (my_name, i)
        my_location = 'somewhere/%s.vmtx' % name_of_template
        template = db.Vm(vendor='vmware', name=name_of_template, location=my_location, created_on=ts, updated_on=ts, tools_status='toolsNotRunning', standby_action='checkpoint', power_state='never', state_changed_on=ts, previous_state='unknown', connection_state='connected', memory_reserve='0', memory_reserve_expand='FALSE', memory_limit='-1', memory_shares='40960', memory_shares_level='normal', cpu_reserve='0', cpu_reserve_expand='FALSE', cpu_limit='-1', cpu_shares='2000', cpu_shares_level='normal', template='TRUE', vdi='FALSE', linked_clone='FALSE', fault_tolerance='FALSE', type='TemplateVmware')
        templates.append(template)
    session_manager(db_session, templates)

"""
Add one host
Infrastructure -> Hosts
"""
@pytest.fixture
def db_setup_host(db_session, cfme_data):
    ts = timestamp()
    my_id = cfme_data.data["database"]["host"]["id"]
    my_ems_id = cfme_data.data["database"]["host"]["management_system_id"]
    my_cluster_id = cfme_data.data["database"]["host"]["cluster_id"]
    my_name = cfme_data.data["database"]["host"]["name"]
    host = db.Host(id=my_id, ems_id=my_ems_id, ems_cluster_id=my_cluster_id, name=my_name, hostname='10.16.120.152', ipaddress='10.16.120.152', vmm_vendor='redhat', vmm_product='rhel', created_on=ts, updated_on=ts, power_state='on', smart='1', connection_state='connected', type='HostRedhat')
    session_manager(db_session, host)

"""
Add multiple hosts
Infrastructure -> Hosts
"""
#TODO
@pytest.fixture
def db_setup_multiple_hosts(db_session, cfme_data):
    pass

"""
Add hardware data for provisioning from templates
Services -> Virtual Machines, Lifecycle -> Provision VMs
"""
@pytest.fixture
def db_setup_hardware(db_session, cfme_data):
    my_id = cfme_data.data["database"]["hardware"]["id"]
    my_template_id = cfme_data.data["database"]["hardware"]["template_id"]
    hw = db.Hardware(id=my_id, guest_os='other_linux', numvcpus='1', vm_or_template_id=my_template_id, memory_cpu='512')
    session_manager(db_session, hw)

@pytest.fixture
def db_setup_metrics(db_session, cfme_data):
    my_id = cfme_data.data["database"]["metrics"]["id"]
    vm_id = cfme_data.data["database"]["metrics"]["vm_id"]
    vm_name= cfme_data.data["database"]["metrics"]["vm_name"]
    ts = timestamp()
    metrics = db.Metric(id=my_id, resource_id=vm_id, resource_name=vm_name, resource_type='VmOrTemplate', cpu_usagemhz_rate_average='700', net_usage_rate_average='800', disk_usage_rate_average='300', derived_memory_used='900', cpu_ready_delta_summation='372579.208333333', cpu_used_delta_summation='2143234.66666667', timestamp=ts, capture_interval_name='realtime')
    session_manager(db_session, metrics)

@pytest.fixture
def db_setup_metrics_rollup(db_session, cfme_data):
    my_id = cfme_data.data["database"]["rollups"]["id"]
    vm_id = cfme_data.data["database"]["rollups"]["vm_id"]
    vm_name= cfme_data.data["database"]["rollups"]["vm_name"]
    date_year = cfme_data.data["database"]["rollups"]["date_year"]
    date_month = cfme_data.data["database"]["rollups"]["date_month"]
    date_day = cfme_data.data["database"]["rollups"]["date_day"]
    temp_date = datetime.date(date_year, date_month, date_day) + datetime.timedelta(hours=8)
    my_date = temp_date.strftime("%Y-%m-%d %H:%M:%S.%f")
    rollup = db.MetricRollup(id=my_id, resource_id=vm_id, resource_name=vm_name, resource_type='VmOrTemplate', cpu_usagemhz_rate_average='200', net_usage_rate_average='500', disk_usage_rate_average='70', derived_memory_used='100', cpu_ready_delta_summation='372579.208333333', cpu_used_delta_summation='2143234.66666667', timestamp=my_date, capture_interval_name='hourly')
    session_manager(db_session, rollup)

"""
Create link between datastore and VM
"""
@pytest.fixture
def db_link_datastore_to_vm(db_session, cfme_data):
    my_vm_id = cfme_data.data["database"]["links"]["link_datastore_vm"]["vm_id"]
    my_datastore_id = cfme_data.data["database"]["links"]["link_datastore_vm"]["datastore_id"]
    conn = db.engine.connect()
    command = "INSERT INTO storages_vms_and_templates VALUES ('%s', '%s');" % (my_datastore_id, my_vm_id)
    result = conn.execute(command)

"""
Create link between datastore and host
"""
@pytest.fixture
def db_link_datastore_to_host(db_session, cfme_data):
    my_datastore_id = cfme_data.data["database"]["links"]["link_datastore_host"]["datastore_id"]
    my_host_id = cfme_data.data["database"]["links"]["link_datastore_host"]["host_id"]
    conn = db.engine.connect()
    command = "INSERT INTO hosts_storages VALUES ('%s', '%s');" % (my_datastore_id, my_host_id)
    result = conn.execute(command)

"""
All in one for tests/test_infrastructure_clusters.py
"""
@pytest.fixture(scope="function")
def db_setup_for_test_infrastructure_clusters(db_session, cfme_data, request):
    #if db_session.query(db.EmCluster).count() == 0:
    db_setup_cluster(db_session, cfme_data)
    db_setup_management_system(db_session, cfme_data)
    db_setup_host(db_session, cfme_data)
    db_setup_datastore(db_session, cfme_data)
    db_setup_virtual_machine(db_session, cfme_data)
    db_link_datastore_to_vm(db_session, cfme_data)
    db_link_datastore_to_host(db_session, cfme_data)

    #clean up after myself
    def fin():
        session = db_session
        #delete vm
        vm_id = cfme_data.data["database"]["virtual_machine"]["id"]
        session.query(db.Vm).filter(db.Vm.id==vm_id).delete()
        #delete management system
        ms_id = cfme_data.data["database"]["management_system"]["id"]
        session.query(db.ExtManagementSystem).filter(db.ExtManagementSystem.id==ms_id).delete()
        #delete cluster
        cluster_id = cfme_data.data["database"]["cluster"]["id"]
        session.query(db.EmCluster).filter(db.EmCluster.id==cluster_id).delete()
        #delete datastore
        datastore_id = cfme_data.data["database"]["datastore"]["id"]
        session.query(db.Storage).filter(db.Storage.id==datastore_id).delete()
        #delete host
        host_id = cfme_data.data["database"]["host"]["id"]
        session.query(db.Host).filter(db.Host.id==host_id).delete()
        #delete link between datastore and vm
        conn = db.engine.connect()
        command = "DELETE FROM storages_vms_and_templates WHERE storage_id='%s';" % datastore_id
        conn.execute(command)
        #delete link between datastore and host
        conn = db.engine.connect()
        command = "DELETE FROM hosts_storages WHERE storage_id='%s';" % datastore_id
        conn.execute(command)
        session.commit()

    request.addfinalizer(fin)

"""
All in one for tests/test_utilization.py
"""
@pytest.fixture(scope="function")
def db_setup_for_test_utilization(db_session, cfme_data, request):
    db_setup_for_test_infrastructure_clusters(db_session, cfme_data, request)

"""
All in one for tests/test_infrastructure_datastores.py
"""
@pytest.fixture(scope="function")
def db_setup_for_test_infrastructure_datastores(db_session, cfme_data, request):
    #if db_session.query(db.Vm).count() == 0:
    db_setup_virtual_machine(db_session, cfme_data)
    db_setup_datastore(db_session, cfme_data)
    db_setup_host(db_session, cfme_data)
    db_link_datastore_to_host(db_session, cfme_data)
    db_link_datastore_to_vm(db_session, cfme_data)

    #cleanup
    def fin():
        session = db_session
        vm_id = cfme_data.data["database"]["virtual_machine"]["id"]
        session.query(db.Vm).filter(db.Vm.id==vm_id).delete()
        datastore_id = cfme_data.data["database"]["datastore"]["id"]
        session.query(db.Storage).filter(db.Storage.id==datastore_id).delete()
        host_id = cfme_data.data["database"]["host"]["id"]
        session.query(db.Host).filter(db.Host.id==host_id).delete()
        conn = db.engine.connect()
        command = "DELETE FROM hosts_storages WHERE storage_id='%s';" % datastore_id
        conn.execute(command)
        conn = db.engine.connect()
        command = "DELETE FROM storages_vms_and_templates WHERE storage_id='%s';" % datastore_id
        conn.execute(command)
        session.commit()

    request.addfinalizer(fin)

"""
All in one for tests/test_paginator.py
"""
@pytest.fixture
def db_setup_for_test_paginator(db_session, cfme_data, request):
    #if db_session.query(db.Vm).count() == 0:
    db_setup_virtual_machine(db_session, cfme_data)

    #cleanup
    def fin():
        session = db_session
        vm_id = cfme_data.data["database"]["virtual_machine"]["id"]
        session.query(db.Vm).filter(db.Vm.id==vm_id).delete()
        session.commit()

    request.addfinalizer(fin)

"""
All in one for tests/test_power_button.py
"""
@pytest.fixture
def db_setup_for_test_power_button(db_session, cfme_data, request):
    #if db_session.query(db.Vm).count() == 0:
    db_setup_template(db_session, cfme_data)
    db_setup_management_system(db_session, cfme_data)
    db_setup_hardware(db_session, cfme_data)

    #cleanup
    def fin():
        session = db_session
        template_id = cfme_data.data["database"]["template"]["id"]
        session.query(db.Vm).filter(db.Vm.id==template_id).delete()
        ms_id = cfme_data.data["database"]["template"]["management_system_id"]
        session.query(db.ExtManagementSystem).filter(db.ExtManagementSystem.id==ms_id).delete()
        hw_id = cfme_data.data["database"]["hardware"]["id"]
        session.query(db.Hardware).filter(db.Hardware.id==hw_id).delete()
        session.commit()

    request.addfinalizer(fin)

"""
All in one for tests/test_configuration_settings_region.py
"""
@pytest.fixture
def db_setup_for_test_configuration_settings_region(db_session, cfme_data, request):
    #if db_session.query(db.EmCluster).count() == 0:
    db_setup_cluster(db_session, cfme_data)
    #if db_session.query(db.Storage).count() == 0:
    db_setup_datastore(db_session, cfme_data)

    #cleanup
    def fin():
        session = db_session
        cluster_id = cfme_data.data["database"]["cluster"]["id"]
        session.query(db.EmCluster).filter(db.EmCluster.id==cluster_id).delete()
        datastore_id = cfme_data.data["database"]["datastore"]["id"]
        session.query(db.Storage).filter(db.Storage.id==datastore_id).delete()
        session.commit()

    request.addfinalizer(fin)

"""
All in one for tests/test_utilization.py
"""
@pytest.fixture
def db_setup_for_utilization_data(db_session, cfme_data, request):
    #if db_session.query(db.Metric).count() == 0:
    db_setup_metrics(db_session, cfme_data)
    db_setup_metrics_rollup(db_session, cfme_data)

    #cleanup
    def fin():
        session = db_session
        metric_id = cfme_data.data["database"]["metrics"]["id"]
        session.query(db.Metric).filter(db.Metric.id==metric_id).delete()
        rollup_id = cfme_data.data["database"]["rollups"]["id"]
        session.query(db.MetricRollup).filter(db.MetricRollup.id==rollup_id).delete()
        session.commit()

    request.addfinalizer(fin)
