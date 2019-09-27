from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic_patternfly import CandidateNotFound

from cfme.exceptions import ItemNotFound
from cfme.generic_objects.definition import GenericObjectDefinition
from cfme.generic_objects.definition import GenericObjectDefinitionCollection
from cfme.generic_objects.definition.definition_views import GenericObjectDefinitionAddView
from cfme.generic_objects.definition.definition_views import GenericObjectDefinitionAllView
from cfme.generic_objects.definition.definition_views import GenericObjectDefinitionDetailsView
from cfme.generic_objects.definition.definition_views import GenericObjectDefinitionEditView
from cfme.generic_objects.instance.ui import GenericObjectInstanceAllView
from cfme.utils.appliance import MiqImplementationContext
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.appliance.implementations.ui import ViaUI


# collection methods
@MiqImplementationContext.external_for(GenericObjectDefinitionCollection.create, ViaUI)
def create(self, name, description, attributes=None, associations=None, methods=None,
           custom_image_file_path=None, cancel=False):
    """
    Create new generic object definition
    Args:
        name: generic object definition name
        description: generic object definition description
        attributes:  generic object definition attributes ex. {'address': 'string'}
        associations:  generic object definition associations ex. {'services': 'Service'}
        methods: generic object definition methods ex. ['method1', 'method2']
        custom_image_file_path: generic object definition custom image file path
        cancel: by default will not be canceled, pass True to make successful cancel

    Returns:
        GenericObjectDefinition entity

    """
    view = navigate_to(self, 'Add')
    view.fill({
        'name': name,
        'description': description,
        'associations': associations,
        'attributes': attributes,
        'methods': methods,
        'custom_image_file': {'file': custom_image_file_path}
    })
    if cancel:
        view.cancel.click()
    else:
        view.add.click()
    view.flash.assert_no_error()

    entity = self.instantiate(
        name=name, description=description, attributes=attributes, associations=associations,
        methods=methods, custom_image_file_path=custom_image_file_path
    )
    return entity


# entity methods
@MiqImplementationContext.external_for(GenericObjectDefinition.update, ViaUI)
def update(self, updates, reset=False, cancel=False):
    """Update generic object definition

    Args:
        updates: dict, with fields to update
    """
    view = navigate_to(self, 'Edit')
    view.fill({
        'name': updates.get('name'),
        'description': updates.get('description'),
        'associations': updates.get('associations'),
        'attributes': updates.get('attributes'),
        'methods': updates.get('methods'),
        'custom_image_file': {'file': updates.get('custom_image_file_path')}
    })
    if reset:
        view.reset.click()
    if cancel:
        view.cancel.click()
    elif not reset and not cancel:
        view.save.click()
        view = self.create_view(GenericObjectDefinitionDetailsView, override=updates)
        assert view.is_displayed
        view.flash.assert_no_error()


@MiqImplementationContext.external_for(GenericObjectDefinition.delete, ViaUI)
def delete(self):
    """Delete generic object definition
    """
    view = navigate_to(self, 'Details')

    view.configuration.item_select(
        'Remove this Generic Object Classes from Inventory', handle_alert=True)
    view = self.create_view(GenericObjectDefinitionAllView, wait='15s')
    view.flash.assert_no_error()


@MiqImplementationContext.external_for(GenericObjectDefinition.exists.getter, ViaUI)
def exists(self):
    try:
        navigate_to(self, 'Details')
        return True
    except (CandidateNotFound, ItemNotFound):
        return False


@MiqImplementationContext.external_for(GenericObjectDefinition.generic_objects.getter, ViaUI)
def generic_objects(self):
    return self.collections.generic_objects


@MiqImplementationContext.external_for(GenericObjectDefinition.generic_object_buttons.getter, ViaUI)
def generic_object_buttons(self):
    return self.collections.generic_object_buttons


@MiqImplementationContext.external_for(GenericObjectDefinition.instance_count.getter, ViaUI)
def instance_count(self):
    view = navigate_to(self, "Details")
    return int(view.summary("Relationships").get_text_of("Instances"))


@MiqImplementationContext.external_for(GenericObjectDefinition.add_button, ViaUI)
def add_button(self, name, description, request, **kwargs):
    return self.generic_object_buttons.create(name, description, request, **kwargs)


# navigator registers
@navigator.register(GenericObjectDefinitionCollection)
class All(CFMENavigateStep):
    VIEW = GenericObjectDefinitionAllView

    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Automation', 'Automate', 'Generic Objects')

    def resetter(self, *args, **kwargs):
        self.view.accordion.fill({'classes': {'tree': ['All Generic Object Classes']}})


@navigator.register(GenericObjectDefinitionCollection)
class Add(CFMENavigateStep):
    VIEW = GenericObjectDefinitionAddView

    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Add a new Generic Object Class')


@navigator.register(GenericObjectDefinition)
class Details(CFMENavigateStep):
    VIEW = GenericObjectDefinitionDetailsView

    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()


@navigator.register(GenericObjectDefinition)
class Edit(CFMENavigateStep):
    VIEW = GenericObjectDefinitionEditView

    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select('Edit this Generic Object Class')


@navigator.register(GenericObjectDefinition)
class Instances(CFMENavigateStep):
    VIEW = GenericObjectInstanceAllView

    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.summary('Relationships').click_at('Instances')
