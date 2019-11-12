import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.explorer.namespace import NamespaceAddView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update

pytestmark = [test_requirements.automate]


@pytest.fixture(
    scope="module",
    params=["plain", "nested_existing"])
def parent_namespace(request, domain):
    if request.param == 'plain':
        return domain
    else:
        return domain.namespaces.create(
            name=fauxfactory.gen_alpha(),
            description=fauxfactory.gen_alpha()
        )


@pytest.mark.sauce
@pytest.mark.tier(1)
def test_namespace_crud(parent_namespace):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: critical
        initialEstimate: 1/16h
        tags: automate
    """
    ns = parent_namespace.namespaces.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha())
    assert ns.exists
    updated_description = "editdescription{}".format(fauxfactory.gen_alpha())
    with update(ns):
        ns.description = updated_description
    assert ns.exists
    ns.delete(cancel=True)
    assert ns.exists
    ns.delete()
    assert not ns.exists


@pytest.mark.tier(1)
def test_namespace_delete_from_table(parent_namespace):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/30h
        tags: automate
    """
    generated = []
    for _ in range(3):
        namespace = parent_namespace.namespaces.create(
            name=fauxfactory.gen_alpha(),
            description=fauxfactory.gen_alpha())
        generated.append(namespace)

    parent_namespace.namespaces.delete(*generated)
    for namespace in generated:
        assert not namespace.exists


@pytest.mark.tier(2)
def test_duplicate_namespace_disallowed(parent_namespace):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseposneg: negative
        initialEstimate: 1/16h
        tags: automate
    """
    ns = parent_namespace.namespaces.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha())
    with pytest.raises(Exception, match="Name has already been taken"):
        parent_namespace.namespaces.create(
            name=ns.name,
            description=ns.description)


@pytest.mark.tier(2)
def test_wrong_namespace_name(request, domain):
    """To test whether namespace is creating with wrong name or not.
       wrong_namespace: 'Dummy Namespace' (This is invalid name of Namespace because there is space
       in the name)

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/60h
        tags: automate
        testSteps:
            1. Navigate to Automation> Automate> Explorer
            2. Try to create namespace with name `Dummy Namespace` (I put space which is invalid)
        expectedResults:
            1.
            2. Should give proper flash message

    Bugzilla:
        1650071
    """
    wrong_namespace = 'Dummy Namespace'
    namespace = domain.namespaces
    with pytest.raises(AssertionError):
        namespace.create(name=wrong_namespace)
    view = namespace.create_view(NamespaceAddView)
    view.flash.assert_message('Name may contain only alphanumeric and _ . - $ characters')
    wrong_namespace = namespace.instantiate(name=wrong_namespace)
    request.addfinalizer(wrong_namespace.delete_if_exists)
    assert not wrong_namespace.exists


@pytest.mark.tier(1)
@pytest.mark.ignore_stream("5.10")
def test_remove_openshift_deployment_in_automate(appliance):
    """This test case will test successful removal of OpenShift "Deployment" from Automate domain -
    ManageIQ.

    Polarion:
        assignee: ghubale
        initialEstimate: 1/20h
        caseimportance: high
        caseposneg: negative
        testtype: functional
        startsin: 5.11
        casecomponent: Automate

    Bugzilla:
        1672937
    """
    view = navigate_to(appliance.collections.domains, 'All')
    assert not view.datastore.tree.has_path('Datastore', 'ManageIQ (Locked)', 'Deployment')
