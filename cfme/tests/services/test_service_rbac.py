import fauxfactory
import pytest

from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.services.service_catalogs import ServiceCatalogs

pytestmark = [
    pytest.mark.usefixtures('uses_infra_providers', 'setup_provider'),
    pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE, scope="module")
]


# todo: turn all below methods into fixtures with teardown steps
def new_role(appliance, product_features):
    collection = appliance.collections.roles
    return collection.create(name=fauxfactory.gen_alphanumeric(start="role_"),
                             vm_restriction=None, product_features=product_features)


def new_group(appliance, role):
    collection = appliance.collections.groups
    return collection.create(description=fauxfactory.gen_alphanumeric(start="group_"),
                             role=role, tenant="My Company")


def new_user(appliance, group, credential):
    collection = appliance.collections.users
    return collection.create(name=fauxfactory.gen_alphanumeric(start="user_"),
                             credential=credential,
                             email='xyz@redhat.com',
                             groups=group,
                             cost_center='Workload',
                             value_assign='Database')


@pytest.yield_fixture(scope='module')
def role_user_group(appliance, new_credential):
    role = new_role(appliance=appliance, product_features=[(['Everything'], False),
                            (['Everything', 'Access Rules for all Virtual Machines'], True)])
    group = new_group(appliance=appliance, role=role.name)
    user = new_user(appliance=appliance, group=group, credential=new_credential)
    yield role, user
    if user.exists:
        user.delete(cancel=False)

    if group.exists:
        group.delete(cancel=False)

    if role.exists:
        role.delete(cancel=False)


def test_service_rbac_no_permission(appliance, role_user_group):
    """ Test service rbac without user permission

    Polarion:
        assignee: apagac
        initialEstimate: 1/4h
        casecomponent: Services
    """
    role, user = role_user_group
    error_message = ("The user's role is not authorized for any access, "
                     "please contact the administrator!")
    with pytest.raises(Exception, match=error_message):
        with user:
            appliance.server.login(user)


def test_service_rbac_catalog(appliance, role_user_group, catalog):
    """ Test service rbac with catalog

    Polarion:
        assignee: apagac
        initialEstimate: 1/4h
        casecomponent: Services
    """
    role, user = role_user_group
    product_features = [(['Everything'], True), (['Everything'], False)]
    product_features.extend([(['Everything', 'Services', 'Catalogs Explorer', k], True)
                             for k in ['Catalogs']])
    role.update({'product_features': product_features})
    with user:
        appliance.server.login(user)
        assert catalog.exists


def test_service_rbac_service_catalog(appliance, role_user_group, catalog, catalog_item):
    """ Test service rbac with service catalog

    Polarion:
        assignee: apagac
        initialEstimate: 1/4h
        casecomponent: Services
    """
    role, user = role_user_group
    product_features = [
        (['Everything'], True), (['Everything'], False),
        (['Everything', 'Services', 'Requests'], True),
        (['Everything', 'Automation', 'Automate', 'Customization'], True)
    ]
    product_features.extend([(['Everything', 'Services', 'Catalogs Explorer', k], True)
                             for k in ['Catalog Items', 'Service Catalogs', 'Catalogs']])
    role.update({'product_features': product_features})
    # Without below line, service_order only works here via admin, not via user
    # TODO: Remove below line when this behavior gets fixed
    with user:
        appliance.server.login(user)
        service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
        service_catalogs.order()
        service_request = appliance.collections.requests.instantiate(catalog_item.name,
                                                                     partial_check=True)
        service_request.wait_for_request()
        assert service_request.is_succeeded()


def test_service_rbac_catalog_item(request, appliance, role_user_group, catalog_item):
    """ Test service rbac with catalog item

    Polarion:
        assignee: apagac
        initialEstimate: 1/4h
        casecomponent: Services
    """
    role, user = role_user_group
    product_features = [(['Everything'], True), (['Everything'], False)]
    product_features.extend([(['Everything', 'Services', 'Catalogs Explorer', k], True)
                             for k in ['Catalog Items']])
    role.update({'product_features': product_features})
    with user:
        appliance.server.login(user)
        assert catalog_item.exists


def test_service_rbac_orchestration(appliance, role_user_group):
    """ Test service rbac with orchestration

    Polarion:
        assignee: apagac
        initialEstimate: 1/4h
        casecomponent: Services
    """
    role, user = role_user_group
    product_features = [(['Everything'], True), (['Everything'], False)]
    product_features.extend([(['Everything', 'Services', 'Catalogs Explorer', k], True)
                             for k in ['Orchestration Templates']])
    role.update({'product_features': product_features})
    with user:
        appliance.server.login(user)
        collection = appliance.collections.orchestration_templates
        template = collection.create(
            template_name=fauxfactory.gen_alphanumeric(start="temp_"),
            template_type='Amazon CloudFormation',
            template_group='CloudFormation Templates',
            description='template description',
            content=fauxfactory.gen_numeric_string())
        assert template.exists
        template.delete()


def test_service_rbac_request(appliance, role_user_group, catalog_item):
    """ Test service rbac with only request module permissions

    Polarion:
        assignee: apagac
        initialEstimate: 1/4h
        casecomponent: Services
    """
    role, user = role_user_group
    product_features = [
        (['Everything'], True), (['Everything'], False),
        (['Everything', 'Services', 'Requests', ], True),
        (['Everything', 'Automation', 'Automate', 'Customization'], True)
    ]
    product_features.extend([(['Everything', 'Services', 'Catalogs Explorer', k], True)
                             for k in ['Catalog Items', 'Service Catalogs', 'Catalogs']])
    role.update({'product_features': product_features})
    with user:
        # Without below line, service_order only works here via admin, not via user
        # TODO: Remove below line when this behavior gets fixed
        appliance.server.login(user)
        service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
        service_catalogs.order()
        cells = {'Description': catalog_item.name}
        order_request = appliance.collections.requests.instantiate(cells=cells, partial_check=True)
        order_request.wait_for_request(method='ui')
        assert order_request.is_succeeded(method='ui')
