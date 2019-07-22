from widgetastic.widget import View
from widgetastic_patternfly import Accordion

from cfme.base.login import BaseLoggedInPage
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import TimelinesChart


class CloudIntelTimelinesView(BaseLoggedInPage):

    chart = TimelinesChart(locator='//div/*[@class="timeline-pf-chart"]')

    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user
            and self.navigation.currently_selected
            == [self.context["object"].appliance.server.intel_name, "Timelines"]
        )

    @View.nested
    class timelines(Accordion): # noqa
        tree = ManageIQTree()
