from widgetastic.widget import View
from widgetastic_manageiq import ManageIQTree, TimelinesChart
from widgetastic_patternfly import Accordion

from cfme.base.login import BaseLoggedInPage


class CloudIntelTimelinesView(BaseLoggedInPage):

    chart = TimelinesChart(locator='//div/*[@class="timeline-pf-chart"]')

    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Cloud Intel', 'Timelines']
        )

    @View.nested
    class timelines(Accordion): # noqa
        tree = ManageIQTree()
