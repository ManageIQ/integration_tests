from widgetastic.widget import Table
from widgetastic.widget import Text
from widgetastic_patternfly import Button

from cfme.base.login import BaseLoggedInPage


class OptimizationView(BaseLoggedInPage):
    title = Text('//*[@id="main-content"]//h1')
    table = Table('//*[@id="main_div"]//table', column_widgets={"Actions": Button()})

    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user
            and self.title.text == "Optimization"
            and self.navigation.currently_selected == ["Overview", "Optimization"]
        )
