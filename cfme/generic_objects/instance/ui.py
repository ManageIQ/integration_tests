from navmazing import NavigateToAttribute
from widgetastic.widget import ParametrizedLocator
from widgetastic.widget import ParametrizedString
from widgetastic.widget import ParametrizedView
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import Button
from widgetastic_patternfly import CandidateNotFound
from widgetastic_patternfly import Dropdown

from cfme.common import BaseLoggedInPage
from cfme.common import Taggable
from cfme.common import TagPageView
from cfme.generic_objects.instance import GenericObjectInstance
from cfme.generic_objects.instance import GenericObjectInstanceCollection
from cfme.utils.appliance import MiqImplementationContext
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.appliance.implementations.ui import ViaUI
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import ParametrizedSummaryTable


# views
class GenericObjectInstanceToolbar(View):
    policy = Dropdown(text='Policy')
    download = Dropdown(text='Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class GenericObjectInstanceAllView(BaseLoggedInPage):
    title = Text('//div[@id="main-content"]//h1')
    toolbar = View.nested(GenericObjectInstanceToolbar)
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        return (
            self.toolbar.policy.is_displayed and
            '(All Generic Objects)' in self.entities.title.text
        )


class GenericObjectInstanceDetailsView(BaseLoggedInPage):
    @View.nested
    class toolbar(View):   # noqa
        policy = Dropdown(text='Policy')
        view_selector = View.nested(ItemsToolBarViewSelector)

    title = Text('//div[@id="main-content"]//h1')
    summary = ParametrizedSummaryTable()

    @property
    def is_displayed(self):
        return (
            self.title.text == '{} (Summary)'.format(self.context['object'].name)
        )


class MyServiceGenericObjectInstanceView(BaseLoggedInPage):
    @View.nested
    class toolbar(View):    # noqa
        reload = Button(title='Refresh this page')

        @ParametrizedView.nested
        class group(ParametrizedView):   # noqa
            PARAMETERS = ("group_name",)
            custom_button = Dropdown(text=ParametrizedString('{group_name}'))

        @ParametrizedView.nested
        class button(ParametrizedView):    # noqa
            PARAMETERS = ("button_name",)
            custom_button = Text(ParametrizedLocator('//button[contains(@id, "custom__custom") and'
                                                     ' normalize-space()={button_name|quote}]'))

    title = Text('//div[@id="main-content"]//h1')
    summary = ParametrizedSummaryTable()

    @property
    def is_displayed(self):
        return (
            self.title.text == self.context['object'].name
        )


# entity methods
@MiqImplementationContext.external_for(GenericObjectInstance.exists.getter, ViaUI)
def exists(self):
    if self.definition.instance_count > 0:
        try:
            navigate_to(self, 'Details')
            return True
        except CandidateNotFound:
            return False
    else:
        return False


@MiqImplementationContext.external_for(GenericObjectInstance.add_tag, ViaUI)
def add_tag(self, tag=None, cancel=False, reset=False, details=True):
    return Taggable.add_tag(self, tag=tag, cancel=cancel, reset=reset, details=details)


@MiqImplementationContext.external_for(GenericObjectInstance.remove_tag, ViaUI)
def remove_tag(self, tag, cancel=False, reset=False, details=True):
    Taggable.remove_tag(self, tag=tag, cancel=cancel, reset=reset, details=details)


@MiqImplementationContext.external_for(GenericObjectInstance.get_tags, ViaUI)
def get_tags(self, tenant="My Company Tags"):
    return Taggable.get_tags(self, tenant=tenant)


# navigator registers
@navigator.register(GenericObjectInstanceCollection, 'All')
class All(CFMENavigateStep):
    VIEW = GenericObjectInstanceAllView

    prerequisite = NavigateToAttribute('parent', 'Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.summary('Relationships').click_at('Instances')


@navigator.register(GenericObjectInstance, 'Details')
class DefinitionDetails(CFMENavigateStep):
    VIEW = GenericObjectInstanceDetailsView

    prerequisite = NavigateToAttribute('definition', 'Instances')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()


@navigator.register(GenericObjectInstance, 'EditTags')
class EditTags(CFMENavigateStep):
    VIEW = TagPageView

    prerequisite = NavigateToAttribute('definition', 'Instances')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).check()
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


@navigator.register(GenericObjectInstance, 'MyServiceDetails')
class MyServiceDetails(CFMENavigateStep):
    VIEW = MyServiceGenericObjectInstanceView

    prerequisite = NavigateToAttribute('my_service', 'GenericObjectInstance')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()
