import pytest
from wrapanapi.utils.random import random_name


def instantiate_namespace(domain_name, namespace_levels):
    namespace = domain_name
    for namespace_name in namespace_levels:
        namespace = namespace.namespaces.instantiate(namespace_name)
    return namespace


def copy_ae_instance(appliance, instance_fqdn, domain_name):
    """
    Copy AE Instance into a domain. We split 'instance_fqdn' which is a full string path to existing
    AE instance. Then based on the values we get from split, proper classes are instantiated.
    AE Instance is copied to provided domain name, then instantiated and returned under new domain.
    Example:
    if 'instance_fqdn' is 'ManageIQ/System/Event/EmsEvent/Nuage/nuage_enterprise_create' we get the
    following values:
    source = ['ManageIQ', 'System', 'Event', 'EmsEvent', 'Nuage', 'nuage_enterprise_create']
    'ManageIQ' as source_domain
    'nuage_enterprise_create' as source AE instance
    'Nuage' as source AE class
    the remaining strings left after 'pop' calls are the AE namespaces which are instantiated
    through 'instantiate_namespace' function
    AE instance is then copied to a new domain. We also instantiate all the destination classes so
    we get proper parent-child structure.

    Args:
        appliance (Appliance): Instance of :class:`Appliance`
        instance_fqdn (string): Full path to the existing AE Instance that we want to copy e.g.
                                   'ManageIQ/System/Event/EmsEvent/Nuage/nuage_enterprise_create'
        domain_name (string): name of existing AE Domain where we want to copy to e.g. 'TestDomain'

    Returns:
        Instance: The new AE Instance object under new domain
    """
    source = instance_fqdn.split('/')
    source_domain_name = source.pop(0)
    source_instance_name = source.pop(-1)
    source_class_name = source.pop(-1)
    source_domain = appliance.collections.domains.instantiate(source_domain_name)

    source_namespace = instantiate_namespace(source_domain, source)
    source_class = source_namespace.classes.instantiate(source_class_name)
    source_instance = source_class.instances.instantiate(source_instance_name)

    source_instance.copy_to(domain_name)

    destination_domain = appliance.collections.domains.instantiate(domain_name)
    destination_namespace = instantiate_namespace(destination_domain, source)
    destination_class = destination_namespace.classes.instantiate(source_class_name)
    # Instantiate instance under new domain
    return destination_class.instances.instantiate(source_instance_name)


@pytest.fixture
def custom_ae_domain(request, appliance):
    """
    Create a new AE Domain.

    By default, a random name is generated for the Domain, but you can specify it explicitly with
    @pytest.mark.parametrize decorator on your test function.

    Example:
    @pytest.mark.parametrize('domain', ['TestDomain'], indirect=True)
    def test_my_automation(domain):
      ...
    """
    domains_collection = appliance.collections.domains
    domain = domains_collection.create(
        name=getattr(request, 'param', random_name()),
        enabled=True)
    yield domain
    domain.delete()


@pytest.fixture
def copy_ae_instance_to_new_domain(request, appliance, custom_ae_domain):
    """
    Copy AE Instance to a newly created AE Domain.

    This fixture requires at least Instance fqdn parameter, while newly created domain name
    can also be customized:

    @pytest.mark.parametrize(
      'copy_ae_instance_to_new_domain',
      ['ManageIQ/System/Event/EmsEvent/Nuage/nuage_enterprise_create'],
      indirect=True
    )
    @pytest.mark.parametrize(
      'custom_ae_domain',
      ['CustomDomainName'],
      indirect=True
    )
    def test_my_automation(copy_ae_instance_to_domain):
      ...

    :return: newly created AE Instance
    """
    return copy_ae_instance(appliance, request.param, custom_ae_domain.name)
