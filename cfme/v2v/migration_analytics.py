import attr
from navmazing import NavigateToAttribute
from widgetastic.widget import View
from widgetastic_patternfly import Button
from widgetastic_patternfly import Text

from cfme.common import BaseLoggedInPage
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import SummaryTable


class MigrationAnalyticsView(BaseLoggedInPage):

    @property
    def in_explorer(self):
        return self.logged_in_as_current_user and self.navigation.currently_selected == [
            "Migration", "Migration Analytics"
        ]

    @property
    def is_displayed(self):
        return self.in_explorer


@attr.s
class MigrationAnalytics(BaseEntity):
    pass


@attr.s
class MigrationAnalyticsCollection(BaseCollection):
    """Collection for migration analytics"""

    ENTITY = MigrationAnalytics


class MigrationAnalyticsAllView(MigrationAnalyticsView):

    get_started = Text('.//div[contains(@class, "blank-slate-pf-main-action")]/button')
    title = Text('.//div[contains(@class, "blank-slate-pf full-page-empty")]/h4')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == "Examine your virtual environment using Red Hat Migration Analytics"
        )


class MigrationAnalyticsSummaryView(View):

    title = Text('.//div[contains(@class, "environment-summary")]/h2')
    collect_inventory_data = Button('.//div[contains(@class, "reports-summary")]/button')
    summary = SummaryTable('.//div[contains(@class, "environment-summary")]/table')

    @property
    def is_displayed(self):
        return self.title.text == "Environment Summary"


@navigator.register(MigrationAnalyticsCollection, "All")
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")
    VIEW = MigrationAnalyticsAllView

    def step(self):
        self.prerequisite_view.navigation.select("Migration", "Migration Analytics")
