# -*- coding: utf-8 -*-

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.base.login import BaseLoggedInPage
from cfme.utils.appliance import ViaREST, ViaUI
from cfme.utils.update import update
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ

pytestmark = [test_requirements.generic_objects]


@pytest.mark.sauce
@pytest.mark.parametrize('context', [ViaREST, ViaUI])
def test_generic_object_definition_crud(appliance, context, soft_assert):
    """
    Polarion:
        assignee: dmisharo
        initialEstimate: 1/30h
        tags: 5.9
    """
    with appliance.context.use(context):
        definition = appliance.collections.generic_object_definitions.create(
            name="{}_generic_class{}".format(context.name.lower(), fauxfactory.gen_alphanumeric()),
            description="Generic Object Definition",
            attributes={"addr01": "string"},
            associations={"services": "Service"},
            methods=["hello_world"])
        if context.name == 'UI':
            view = appliance.browser.create_view(BaseLoggedInPage)
            view.flash.assert_success_message(
                'Generic Object Class "{}" has been successfully added.'.format(definition.name))
        assert definition.exists

        with update(definition):
            definition.name = '{}_updated'.format(definition.name)
            definition.attributes = {"new_address": "string"}
        if context.name == 'UI':
            view.flash.assert_success_message(
                'Generic Object Class "{}" has been successfully saved.'.format(definition.name))
            view = navigate_to(definition, 'Details')
            soft_assert(view.summary('Attributes (2)').get_text_of('new_address'))
            soft_assert(view.summary('Attributes (2)').get_text_of('addr01'))
            soft_assert(view.summary('Associations (1)').get_text_of('services'))
        else:
            rest_definition = appliance.rest_api.collections.generic_object_definitions.get(
                name=definition.name)
            soft_assert("new_address" in rest_definition.properties['attributes'])
            soft_assert("addr01" not in rest_definition.properties['attributes'])

        definition.delete()
        if context.name == 'UI' and not BZ(bug_id=1644658, forced_streams=["5.10"]).blocks:
            view.flash.assert_success_message(
                'Generic Object Class:"{}" was successfully deleted'.format(definition.name))
        assert not definition.exists


@pytest.mark.manual
@pytest.mark.tier(3)
def test_generic_objects_class_accordion_should_display_when_locale_is_french():
    """ Generic objects class accordion should display when locale is french

    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/6h
        startsin: 5.10
        tags: service

    Bugzilla:
        1594480
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_generic_objects_class_crud():
    """

    Polarion:
        assignee: nansari
        casecomponent: WebUI
        testtype: functional
        initialEstimate: 1/16h
        startsin: 5.9
        tags: service
        testSteps:
            1.Create Generic Objects Class
            2.Add button group
            3.Go to Generic Objects Class details page
            4.Delete the Generic Objects Class

    Bugzilla:
        1650137
    """
    pass
