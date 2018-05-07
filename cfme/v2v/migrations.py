import attr

from navmazing import NavigateToAttribute
from cfme.base.login import BaseLoggedInPage

from widgetastic_patternfly import Text
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep


# Views


class MigrationDashboardView(BaseLoggedInPage):
    create_infrastructure_mapping = Text(locator='(//a|//button)'
        '[text()="Create Infrastructure Mapping"]')
    create_migration_plan = Text(locator='(//a|//button)[text()="Create Migration Plan"]')

    @property
    def is_displayed(self):
        return self.navigation.currently_selected == ['Compute', 'Migration']


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
