import attr

from navmazing import NavigateToAttribute, NavigateToSibling
from cfme.base.login import BaseLoggedInPage
from widgetastic.widget import View

from widgetastic_patternfly import Text, TextInput, Button
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import (navigator, CFMENavigateStep,
    can_skip_badness_test)


# Views


class MigrationDashboardView(BaseLoggedInPage):
    create_infrastructure_mapping = Text(locator='(//a|//button)'
        '[text()="Create Infrastructure Mapping"]')
    create_migration_plan = Text(locator='(//a|//button)[text()="Create Migration Plan"]')

    @property
    def is_displayed(self):
        return self.navigation.currently_selected == ['Compute', 'Migration']


class AddInfrastructureMappingView(View):
    title = Text(locator='.//h4[contains(@class,"modal-title")]')
    name = TextInput(name='name')
    description = TextInput(name='description')
    back_btn = Button('Back')
    next_btn = Button('Next')
    cancel_btn = Button('Cancel')

    @property
    def is_displayed(self):
        return (self.title.text == 'Infrastructure Mapping Wizard')


class AddMigrationPlanView(View):
    title = Text(locator='.//h4[contains(@class,"modal-title")]')
    name = TextInput(name='name')
    description = TextInput(name='description')
    back_btn = Button('Back')
    next_btn = Button('Next')
    cancel_btn = Button('Cancel')

    @property
    def is_displayed(self):
        return (self.title.text == 'Migration Plan Wizard')

# Collections Entities


@attr.s
class InfrastructureMapping(BaseEntity):
    """Class representing v2v infrastructure mappings"""
    category = 'infrastructuremapping'
    string_name = 'Infrastructure Mapping'


@attr.s
class InfrastructureMappingCollection(BaseCollection):
    """Collection object for Migration mapping object"""
    ENTITY = InfrastructureMapping


@attr.s
class MigrationPlan(BaseEntity):
    """Class representing v2v infrastructure mappings"""
    category = 'migrationplan'
    string_name = 'Migration Plan'


@attr.s
class MigrationPlanCollection(BaseCollection):
    """Collection object for Migration mapping object"""
    ENTITY = MigrationPlan


# Navigations

@navigator.register(InfrastructureMappingCollection, 'All')
@navigator.register(MigrationPlanCollection, 'All')
class All(CFMENavigateStep):
    VIEW = MigrationDashboardView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Migration')

    def resetter(self):
        """Reset the view"""
        self.view.browser.refresh()


@navigator.register(InfrastructureMappingCollection, 'Add')
class AddInfrastructureMapping(CFMENavigateStep):
    VIEW = AddInfrastructureMappingView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.create_infrastructure_mapping.click()

    @can_skip_badness_test  # because it loops over and over as it cannot handle the modal
    def resetter(self):
        # Reset the view
        self.view.browser.refresh()


@navigator.register(MigrationPlanCollection, 'Add')
class AddMigrationPlan(CFMENavigateStep):
    VIEW = AddMigrationPlanView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.create_migration_plan.click()

    @can_skip_badness_test  # because it loops over and over as it cannot handle the modal
    def resetter(self):
        # Reset the view
        self.view.browser.refresh()
