import fauxfactory
import pytest

import cfme.rest.gen_data as rest_gen_data
from cfme import test_requirements
from cfme.generic_objects.instance.ui import MyServiceGenericObjectInstanceView
from cfme.services.myservice import MyService
from cfme.services.myservice.ui import MyServicesView
from cfme.tests.automate.custom_button import TextInputDialogView
from cfme.utils.appliance import ViaREST
from cfme.utils.appliance import ViaUI
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.update import update
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for


pytestmark = [test_requirements.generic_objects]


@pytest.fixture(scope="module")
def categories(request, appliance):
    return rest_gen_data.categories(request, appliance, 3)


@pytest.fixture(scope="module")
def tags(request, appliance, categories):
    return rest_gen_data.tags(request, appliance, categories)


@pytest.fixture
def button_with_dialog(appliance, generic_object, dialog):
    generic_definition = generic_object.definition
    with appliance.context.use(ViaUI):
        button = generic_definition.collections.generic_object_buttons.create(
            name=fauxfactory.gen_alpha(),
            description=fauxfactory.gen_alpha(),
            request="call_instance",
            image="ff ff-network-interface",
            dialog=dialog.label
        )

        yield button

        button.delete_if_exists()


@pytest.mark.sauce
@pytest.mark.parametrize('context', [ViaREST, ViaUI])
def test_generic_objects_crud(appliance, context, request):
    """
    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        tags: 5.9
        casecomponent: GenericObjects
    """
    with appliance.context.use(context):
        definition = appliance.collections.generic_object_definitions.create(
            name='rest_generic_class{}'.format(fauxfactory.gen_alphanumeric()),
            description='Generic Object Definition',
            attributes={'addr01': 'string'},
            associations={'services': 'Service'}
        )
        assert definition.exists
        request.addfinalizer(definition.delete)

    with appliance.context.use(ViaREST):
        myservices = []
        for _ in range(2):
            service_name = 'rest_service_{}'.format(fauxfactory.gen_alphanumeric())
            rest_service = appliance.rest_api.collections.services.action.create(
                name=service_name,
                display=True
            )
            rest_service = rest_service[0]
            request.addfinalizer(rest_service.action.delete)
            myservices.append(MyService(appliance, name=service_name))
        instance = appliance.collections.generic_objects.create(
            name='rest_generic_instance{}'.format(fauxfactory.gen_alphanumeric()),
            definition=definition,
            attributes={'addr01': 'Test Address'},
            associations={'services': [myservices[0]]}
        )
        request.addfinalizer(instance.delete)
    with appliance.context.use(context):
        if context.name == 'UI':
            # we need to refresh definition page to update instance count,
            # as navigation to instance details happens via this page
            appliance.browser.widgetastic.refresh()
        assert instance.exists

    with appliance.context.use(ViaREST):
        with update(instance):
            instance.attributes = {'addr01': 'Changed'}
            instance.associations = {'services': myservices}
        rest_instance = appliance.rest_api.collections.generic_objects.get(name=instance.name)
        rest_data = appliance.rest_api.get('{}?associations=services'.format(rest_instance.href))
        assert len(rest_data['services']) == 2
        assert rest_data['property_attributes']['addr01'] == 'Changed'
        instance.delete()

    with appliance.context.use(context):
        assert not instance.exists


@test_requirements.tag
@pytest.mark.parametrize('tag_place', [True, False], ids=['details', 'collection'])
def test_generic_objects_tag_ui(appliance, generic_object, tag_place):
    """Tests assigning and unassigning tags using UI.

        Metadata:
            test_flag: ui

    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: GenericObjects
    """
    with appliance.context.use(ViaUI):
        assigned_tag = generic_object.add_tag(details=tag_place)
        # TODO uncomment when tags aria added to details
        # tag_available = instance.get_tags()
        # assert any(tag.category.display_name == assigned_tag.category.display_name and
        #            tag.display_name == assigned_tag.display_name
        #            for tag in tag_available), 'Assigned tag was not found on the details page'
        generic_object.remove_tag(assigned_tag, details=tag_place)
        # TODO uncomment when tags aria added to details
        # assert not(tag.category.display_name == assigned_tag.category.display_name and
        #            tag.display_name == assigned_tag.display_name
        #            for tag in tag_available), 'Assigned tag was not removed from the details page'


@test_requirements.rest
def test_generic_objects_tag_rest(appliance, generic_object, tags):
    """Tests assigning and unassigning tags using REST.

    Metadata:
        test_flag: rest

    Polarion:
        initialEstimate: 1/4h
        assignee: pvala
        casecomponent: Tagging
        caseimportance: high
    """
    tag = tags[0]
    with appliance.context.use(ViaREST):
        generic_object.add_tag(tag)
        tag_available = generic_object.get_tags()
        assert tag.id in [t.id for t in tag_available], 'Assigned tag was not found'
        generic_object.remove_tag(tag)
        tag_available = generic_object.get_tags()
        assert tag.id not in [t.id for t in tag_available]


@test_requirements.customer_stories
@pytest.mark.meta(automates=[1729341, 1743266])
def test_generic_object_with_service_button(appliance, generic_object, button_with_dialog):
    """
    Bugzilla:
        1729341
        1743266

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/6h
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: GenericObjects
    """
    # add generic object to service
    myservice = MyService(appliance, name=generic_object.associations.get("services")[0].name)
    with appliance.context.use(ViaREST):
        myservice.add_resource_generic_object(generic_object)
    # now navigate to the details of the generic_object
    view = navigate_to(generic_object, "MyServiceDetails")
    view.toolbar.button(button_with_dialog.name).custom_button.click()
    view = generic_object.create_view(TextInputDialogView, wait=10)
    view.service_name.fill("Custom Button Execute")
    wait_for(lambda: not view.submit.disabled, timeout="10s")
    view.submit.click()

    # now for the actual test, make sure after hitting submit we're on the correct page
    try:
        generic_object.create_view(MyServiceGenericObjectInstanceView, wait=10)
    except TimedOutError:
        pytest.fail("Could not wait for service's generic object view to displayed.")


@pytest.mark.ignore_stream("5.10")
@pytest.mark.meta(blockers=[BZ(1741050)], coverage=[1741050])
def test_generic_object_on_service_breadcrumb(appliance, generic_object):
    """
    Bugzilla:
        1741050

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/6h
        casecomponent: GenericObjects
        testSteps:
            1. Generate a service viewable under My Services
            2. Create Generic Object Class & Instance
            3. Assign the generic object instance to the service
            4. Navigate to the service
            5. Click on the generic object instances
            6. Check the breadcrumb link
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6. Breadcrumb should work properly
    """
    # add generic object to service
    myservice = MyService(appliance, name=generic_object.associations.get("services")[0].name)
    with appliance.context.use(ViaREST):
        myservice.add_resource_generic_object(generic_object)
    # now navigate to the details of the generic_object
    with appliance.context.use(ViaUI):
        view = navigate_to(generic_object, "MyServiceDetails")
        view.breadcrumb.click_location("Active Services")
        assert not view.is_displayed
        view = myservice.create_view(MyServicesView)
        assert view.is_displayed
