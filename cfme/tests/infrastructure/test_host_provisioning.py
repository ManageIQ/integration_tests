import pytest

from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.pxe import get_pxe_server_from_config
from cfme.infrastructure.pxe import get_template_from_config
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.config_data import cfme_data
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.meta(server_roles="+automate +notifier"),
    pytest.mark.usefixtures('uses_infra_providers'),
]


def pytest_generate_tests(metafunc):
    # Filter out providers without host provisioning data defined
    argnames, argvalues, idlist = testgen.providers_by_class(
        metafunc, [InfraProvider], required_fields=[
            ['host_provisioning', 'pxe_server'],
            ['host_provisioning', 'pxe_image'],
            ['host_provisioning', 'pxe_image_type'],
            ['host_provisioning', 'pxe_kickstart'],
            ['host_provisioning', 'datacenter'],
            ['host_provisioning', 'cluster'],
            ['host_provisioning', 'datastores'],
            ['host_provisioning', 'hostname'],
            ['host_provisioning', 'root_password'],
            ['host_provisioning', 'ip_addr'],
            ['host_provisioning', 'subnet_mask'],
            ['host_provisioning', 'gateway'],
            ['host_provisioning', 'dns'],
        ])
    pargnames, pargvalues, pidlist = testgen.pxe_servers(metafunc)
    pxe_server_names = [pval[0] for pval in pargvalues]

    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(list(zip(argnames, argvalue_tuple)))
        try:
            prov_data = args['provider'].data['host_provisioning']
        except KeyError:
            # No host provisioning data available
            continue

        holder = metafunc.config.pluginmanager.get_plugin('appliance-holder')
        stream = prov_data.get('runs_on_stream', '')
        if not holder.held_appliance.version.is_in_series(str(stream)):
            continue

        pxe_server_name = prov_data.get('pxe_server', '')
        if pxe_server_name not in pxe_server_names:
            continue

        pxe_cust_template = prov_data.get('pxe_kickstart', '')
        if pxe_cust_template not in list(cfme_data.get('customization_templates', {}).keys()):
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope='module')
def pxe_server(appliance, provider):
    provisioning_data = provider.data['provisioning']
    pxe_server_name = provisioning_data['pxe_server']
    return get_pxe_server_from_config(pxe_server_name, appliance=appliance)


@pytest.fixture(scope='module')
def pxe_cust_template(appliance, provider):
    provisioning_data = provider.data['provisioning']
    pxe_cust_template = provisioning_data['pxe_kickstart']
    return get_template_from_config(pxe_cust_template, appliance=appliance)


@pytest.fixture(scope="module")
def setup_pxe_servers_host_prov(pxe_server, pxe_cust_template, host_provisioning):
    if not pxe_server.exists:
        pxe_server.create()
        pxe_server.set_pxe_image_type(host_provisioning['pxe_image'],
                                      host_provisioning['pxe_image_type'])
    if not pxe_cust_template.exists:
        pxe_cust_template.create()


@pytest.mark.usefixtures('setup_pxe_servers_host_prov')
def test_host_provisioning(appliance, setup_provider, cfme_data, host_provisioning, provider,
                           smtp_test, request):
    """Tests host provisioning

    Metadata:
        test_flag: host_provision

    Bugs:
        1203775
        1232427

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: Provisioning
    """

    # Add host before provisioning
    test_host = appliance.collections.hosts.create_from_config('esx')

    # Populate provisioning_data before submitting host provisioning form
    (pxe_server,
     pxe_image,
     pxe_image_type,
     pxe_kickstart,
     datacenter,
     cluster,
     datastores,
     prov_host_name,
     root_password,
     ip_addr,
     subnet_mask,
     gateway,
     dns) = tuple(map(host_provisioning.get,
            ('pxe_server',
             'pxe_image',
             'pxe_image_type',
             'pxe_kickstart',
             'datacenter',
             'cluster',
             'datastores',
             'hostname',
             'root_password',
             'ip_addr',
             'subnet_mask',
             'gateway',
             'dns')))

    def cleanup_host():
        try:
            logger.info('Cleaning up host %s on provider %s', prov_host_name, provider.key)
            mgmt_system = provider.mgmt
            host_list = mgmt_system.list_host()
            if host_provisioning['ip_addr'] in host_list:
                wait_for(mgmt_system.is_host_connected, [host_provisioning['ip_addr']])
                mgmt_system.remove_host_from_cluster(host_provisioning['ip_addr'])

            ipmi = test_host.get_ipmi()
            ipmi.power_off()

            # During host provisioning,the host name gets changed from what's specified at creation
            # time.If host provisioning succeeds,the original name is reverted to,otherwise the
            # changed names are retained upon failure
            renamed_host_name1 = "{} ({})".format('IPMI', host_provisioning['ipmi_address'])
            renamed_host_name2 = "{} ({})".format('VMware ESXi', host_provisioning['ip_addr'])

            host_collection = appliance.collections.hosts
            host_list_ui = host_collection.all(provider=provider)
            if host_provisioning['hostname'] in host_list_ui:
                test_host.delete(cancel=False)
                test_host.wait_for_delete()
            elif renamed_host_name1 in [h.name for h in host_list_ui]:
                host_renamed_obj1 = host_collection.instantiate(name=renamed_host_name1,
                                                                provider=provider)
                host_renamed_obj1.delete(cancel=False)
                host_renamed_obj1.wait_for_delete()
            elif renamed_host_name2 in [h.name for h in host_list_ui]:
                host_renamed_obj2 = host_collection.instantiate(name=renamed_host_name2,
                                                                provider=provider)
                host_renamed_obj2.delete(cancel=False)
                host_renamed_obj2.wait_for_delete()
        except Exception:
            # The mgmt_sys classes raise Exception :\
            logger.exception('Failed to clean up host %s on provider %s',
                             prov_host_name,
                             provider.key)

    request.addfinalizer(cleanup_host)

    view = navigate_to(test_host, 'Provision')

    note = ('Provisioning host {} on provider {}'.format(prov_host_name, provider.key))
    provisioning_data = {
        'request': {
            'email': 'template_provisioner@example.com',
            'first_name': 'Template',
            'last_name': 'Provisioner',
            'notes': note
        },
        'catalog': {'pxe_server': pxe_server,
                    'pxe_image': {'name': [pxe_image]}
                    },
        'environment': {'provider_name': provider.name,
                        'datastore_name': {'name': datastores},
                        'cluster': "{} / {}".format(datacenter, cluster),
                        'host_name': prov_host_name
                        },
        'customize': {'root_password': root_password,
                      'ip_address': ip_addr,
                      'subnet_mask': subnet_mask,
                      'gateway': gateway,
                      'dns_servers': dns,
                      'custom_template': {'name': [pxe_kickstart]},
                      },
    }

    view.form.fill_with(provisioning_data, on_change=view.form.submit_button)
    view.flash.assert_success_message(
        "Host Request was Submitted, you will be notified when your Hosts are ready"
    )

    request_description = 'PXE install on [{}] from image [{}]'.format(prov_host_name, pxe_image)
    host_request = appliance.collections.requests.instantiate(request_description)
    host_request.wait_for_request(method='ui')
    assert host_request.row.last_message.text == 'Host Provisioned Successfully'
    assert host_request.row.status.text != 'Error'

    # Navigate to host details page and verify Provider and cluster names
    view = navigate_to(test_host, 'Details')
    assert view.entities.summary('Relationships').get_text_of('Infrastructure Provider') ==\
        provider.name, 'Provider name does not match'

    assert view.entities.summary('Relationships').get_text_of('Cluster') ==\
        host_provisioning['cluster'], 'Cluster does not match'

    # Navigate to host datastore page and verify that the requested datastore has been assigned
    # to the host
    requested_ds = host_provisioning['datastores']
    datastores = test_host.get_datastores()
    assert set(requested_ds).issubset(datastores), 'Datastores are missing some members'

    # Wait for e-mails to appear
    def verify():
        return len(
            smtp_test.get_emails(
                subject_like="Your host provisioning request has Completed - Host:%%".format(
                    prov_host_name))
        ) > 0

    wait_for(verify, message="email receive check", delay=5)
