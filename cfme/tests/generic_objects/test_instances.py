# -*- coding: utf-8 -*-

import fauxfactory
import pytest


from cfme import test_requirements
from cfme.base.login import BaseLoggedInPage
from cfme.services.myservice import MyService
from cfme.rest.gen_data import categories as _categories, tags as _tags
from cfme.utils.appliance import ViaREST, ViaUI
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.rest import assert_response
from cfme.utils.update import update


pytestmark = [
    test_requirements.generic_objects,
    pytest.mark.uncollectif(lambda appliance: appliance.version < "5.9",
                            reason="5.8 appliance doesn't support generic objects")
]


@pytest.fixture
def definition(appliance):
    with appliance.context.use(ViaREST):
        definition = appliance.collections.generic_object_definitions.create(
            name='rest_generic_class{}'.format(fauxfactory.gen_alphanumeric()),
            description='Generic Object Definition',
            attributes={'addr01': 'string'},
            associations={'services': 'Service'},
            methods=['add_vm', 'remove_vm']
        )
        yield definition
        if definition.exists:
            definition.delete()


@pytest.fixture
def service(appliance):
    service_name = 'rest_service_{}'.format(fauxfactory.gen_alphanumeric())
    rest_service = appliance.rest_api.collections.services.action.create(
        name=service_name,
        display=True
    )
    rest_service = rest_service[0]
    yield rest_service
    rest_service.action.delete()


@pytest.fixture
def g_object(definition, service, appliance):
    myservice = MyService(appliance, name=service.name)
    with appliance.context.use(ViaREST):
        instance = appliance.collections.generic_objects.create(
            name='rest_generic_instance{}'.format(fauxfactory.gen_alphanumeric()),
            definition=definition,
            attributes={'addr01': 'Test Address'},
            associations={'services': [myservice]}
        )
        yield instance
        if instance.exists:
            instance.delete()


@pytest.fixture
def add_generic_object_to_service(appliance, service, g_object):
    with appliance.context.use(ViaREST):
        service.action.add_resource(
            resource=appliance.rest_api.collections.generic_objects.find_by(
                name=g_object.name)[0]._ref_repr()
        )
        assert_response(appliance)

@pytest.fixture(scope="module")
def categories(request, appliance):
    return _categories(request, appliance.rest_api, 3)


@pytest.fixture(scope="module")
def tags(request, appliance, categories):
    return _tags(request, appliance.rest_api, categories)


@pytest.mark.sauce
@pytest.mark.parametrize('context', [ViaREST])
def test_generic_objects_crud(appliance, context, request):
    with appliance.context.use(context):
        definition = appliance.collections.generic_object_definitions.create(
            name='rest_generic_class{}'.format(fauxfactory.gen_alphanumeric()),
            description='Generic Object Definition',
            attributes={'addr01': 'string'},
            associations={'services': 'Service'}
        )
        assert definition.exists
        request.addfinalizer(definition.delete)

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
        assert instance.exists
        request.addfinalizer(instance.delete)

        with update(instance):
            instance.attributes = {'addr01': 'Changed'}
            instance.associations = {'services': myservices}
        rest_instance = appliance.rest_api.collections.generic_objects.get(name=instance.name)
        rest_data = appliance.rest_api.get('{}?associations=services'.format(rest_instance.href))
        assert len(rest_data['services']) == 2
        assert rest_data['property_attributes']['addr01'] == 'Changed'

        instance.delete()
        assert not instance.exists


@pytest.mark.parametrize('context', [ViaUI])
def test_generic_objects_crud_ui(appliance, context, request):
    """
        CRUD test for generic object via UI

        Metadata:
            test_flag: ui
    """
    with appliance.context.use(context):
        definition = appliance.collections.generic_object_definitions.create(
            name="rest_generic_class{}".format(fauxfactory.gen_alphanumeric()),
            description="Generic Object Definition",
            attributes={"addr01": "String"},
            associations={"services": "Service"},
            methods=["hello_world"])

        with appliance.context.use(ViaREST):
            instance = appliance.collections.generic_objects.create(
                name='rest_generic_instance{}'.format(fauxfactory.gen_alphanumeric()),
                definition=definition,
                attributes={'addr01': 'Test Address'}
            )
            request.addfinalizer(instance.delete)
        view = navigate_to(instance, 'Details')
        assert view.is_displayed


@pytest.fixture
def create_button_group(appliance, definition):

    def _create_button_group():
        with appliance.context.use(ViaUI):
            group_name = 'button_group_{}'.format(fauxfactory.gen_alphanumeric())
            view = appliance.browser.create_view(BaseLoggedInPage)
            definition.add_button_group(
                name=group_name,
                description='Group_button_description',
                image='fa-user'
            )
            view.flash.assert_no_error()
            return group_name
    return _create_button_group


@pytest.fixture
def create_button(appliance, create_button_group, definition):

    def _create_button(button_group):
        with appliance.context.use(ViaUI):
            group_name = create_button_group() if button_group else None
            button_name = 'button_{}'.format(fauxfactory.gen_alphanumeric())
            definition.add_button(
                name=button_name,
                description='Button_description',
                image='fa-home',
                request=fauxfactory.gen_alphanumeric(),
                button_group=group_name)
            view = appliance.browser.create_view(BaseLoggedInPage)
            view.flash.assert_no_error()
        return {group_name: button_name}
    return _create_button


@pytest.mark.parametrize('button_group', [True, False],
                         ids=['button_group_with_button', 'single_button'])
@pytest.mark.parametrize('context', [ViaUI])
def test_generic_objects_with_buttons_ui(appliance, request, button_group, create_button,
                                         context, service):
    """
        Tests buttons ui visibility assigned to generic object

        Metadata:
            test_flag: ui
    """
    myservice = MyService(appliance, name=service.name)
    button = create_button(button_group)
    group = list(button.keys())[0]
    with appliance.context.use(ViaREST):
        instance = appliance.collections.generic_objects.create(
            name='rest_generic_instance{}'.format(fauxfactory.gen_alphanumeric()),
            definition=definition,
            attributes={'addr01': 'Test Address'},
            associations={'services': [myservice]}
        )
        request.addfinalizer(instance.delete)
        service.action.add_resource(
            resource=appliance.rest_api.collections.generic_objects.find_by(
                name=instance.name)[0]._ref_repr()
        )
        assert_response(appliance)
    with appliance.context.use(context):
        view = navigate_to(myservice, 'GenericObjectInstance', instance_name=instance.name)
        if button_group:
            assert view.toolbar.group(group).custom_button.has_item(button[group])
        else:
            assert view.toolbar.button(button[group]).custom_button.is_displayed


@pytest.mark.parametrize('tag_place', [True, False], ids=['details', 'collection'])
@pytest.mark.parametrize('context', [ViaUI])
def test_generic_objects_tag_ui(appliance, context, g_object, tag_place):
    """Tests assigning and unassigning tags using UI.

        Metadata:
            test_flag: ui
        """
    with appliance.context.use(context):
        assigned_tag = g_object.add_tag(details=tag_place)
        # TODO uncomment when tags aria added to details
        # tag_available = instance.get_tags()
        # assert any(tag.category.display_name == assigned_tag.category.display_name and
        #            tag.display_name == assigned_tag.display_name
        #            for tag in tag_available), 'Assigned tag was not found on the details page'
        g_object.remove_tag(assigned_tag, details=tag_place)
        # TODO uncomment when tags aria added to details
        # assert not(tag.category.display_name == assigned_tag.category.display_name and
        #            tag.display_name == assigned_tag.display_name
        #            for tag in tag_available), 'Assigned tag was not removed from the details page'


@pytest.mark.parametrize('context', [ViaREST])
def test_generic_objects_tag(appliance, context, g_object, tags):
    """Tests assigning and unassigning tags using REST.

    Metadata:
        test_flag: rest
    """
    tag = tags[0]
    with appliance.context.use(context):
        g_object.add_tag(tag)
        tag_available = g_object.get_tags()
        assert tag.id in [t.id for t in tag_available], 'Assigned tag was not found'
        g_object.remove_tag(tag)
        tag_available = g_object.get_tags()
        assert tag.id not in [t.id for t in tag_available]
