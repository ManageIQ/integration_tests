import pytest
from wrapanapi.utils.random import random_name

from cfme.utils.log_validator import LogValidator
from cfme.utils.update import update


def test_auth_attributes_of_nuage_ae_class(appliance):
    """
        Ensure Nuage AE Class contains auth attributes in AE Schema
    """
    expected_fields = ['nuage_password', 'nuage_username', 'nuage_enterprise', 'nuage_url',
                       'nuage_api_version']
    manageiq_domain = appliance.collections.domains.instantiate(name='ManageIQ')
    system_namespace = manageiq_domain.namespaces.instantiate(name='System')
    event_namespace = system_namespace.namespaces.instantiate(name='Event')
    ems_event_namespace = event_namespace.namespaces.instantiate(name='EmsEvent')
    nuage_class = ems_event_namespace.classes.instantiate(name='Nuage')
    schema_fields = nuage_class.schema.schema_field_names

    assert all(expected in schema_fields for expected in expected_fields)


@pytest.mark.parametrize(
    'copy_ae_instance_to_new_domain',
    ['ManageIQ/System/Event/EmsEvent/Nuage/nuage_enterprise_create'],
    indirect=True)
@pytest.mark.parametrize('ansible_repository', ['nuage'], indirect=True)
def test_embedded_ansible_executed_with_data_upon_event(request,
                                                        ansible_repository,
                                                        copy_ae_instance_to_new_domain,
                                                        networks_provider):
    """
    Test that Nuage events trigger Embedded Ansible automation and that playbook has access to
    authentication attributes and event data.

    Specifically, we copy AE Instance 'ManageIQ/System/Event/EmsEvent/Nuage/nuage_enterprise_create'
    from default domain into our own domain and customize it's 'meth5' attribute to invoke
    Embedded Ansible playbook which prints authentication attributes and event data into evm.log.
    This test then triggers a 'nuage_enterprise_create' event and waits for appropriate line
    to appear in evm.log.

    Prerequisites:
    Following content needs to be present in cfme_data.yaml in order to fetch correct
    Ansible repository:

    ansible_links:
      playbook_repositories:
        embedded_ansible: https://github.com/xlab-si/integration-tests-nuage-automation.git
    """
    ae_instance = copy_ae_instance_to_new_domain
    ae_class = ae_instance.klass
    ae_method = ae_class.methods.create(
        name='printout',
        location='playbook',
        repository=ansible_repository.name,
        playbook='printout.yaml',
        machine_credential='CFME Default Credential',
        logging_output='Always')

    username = random_name()
    with update(ae_instance):
        ae_instance.fields = {
            'nuage_username': {'value': username},
            'nuage_enterprise': {'value': 'csp'},
            'nuage_url': {'value': 'https://nuage:8443'},
            'nuage_api_version': {'value': 'v5_0'},
            'meth5': {'value': ae_method.name}
        }

    enterprise = networks_provider.mgmt.create_enterprise()
    request.addfinalizer(lambda: networks_provider.mgmt.delete_enterprise(enterprise))
    evm_tail = LogValidator(
        '/var/www/miq/vmdb/log/evm.log',
        matched_patterns=[
            r'.*I confirm that username is {} and event is raised for {}.*'.format(username,
                                                                                   enterprise.id)
        ]
    )
    evm_tail.start_monitoring()
    # search logs and wait for validation
    assert evm_tail.validate(wait="300s")
