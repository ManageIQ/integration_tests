from navmazing import NavigateToAttribute
from widgetastic.widget import Text, View
from widgetastic_patternfly import Dropdown, CandidateNotFound

from cfme.base.login import BaseLoggedInPage
from cfme.utils.appliance import MiqImplementationContext
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to, ViaUI
from widgetastic_manageiq import (ItemsToolBarViewSelector, BaseEntitiesView,
    ParametrizedSummaryTable)
from . import GenericObjectInstance, GenericObjectInstanceCollection


class GenericObjectInstanceToolbar(View):
    """
    Represents provider toolbar and its controls
    """
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
    title = Text('//div[@id="main-content"]//h1')
    policy = Dropdown(text='Policy')
    summary = ParametrizedSummaryTable()

    @property
    def is_displayed(self):
        return (
            self.title.text == '{} (Summary)'.format(self.context['object'].name)
        )


@MiqImplementationContext.external_for(GenericObjectInstance.exists.getter, ViaUI)
def exists(self):
    try:
        navigate_to(self, 'Details')
        return True
    except CandidateNotFound:
        return False


@navigator.register(GenericObjectInstanceCollection, 'All')
class All(CFMENavigateStep):
    VIEW = GenericObjectInstanceAllView

    prerequisite = NavigateToAttribute('parent', 'Details')

    def step(self):
        self.prerequisite_view.summary('Relationships').click_at('Instances')


@navigator.register(GenericObjectInstance, 'Details')
class Details(CFMENavigateStep):
    VIEW = GenericObjectInstanceDetailsView

    def prerequisite(self):
        return navigate_to(self.obj.definition, 'Instances')

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()
