from widgetastic.widget import Table
from widgetastic.widget import Text
from widgetastic_patternfly import Button

from cfme.base.login import BaseLoggedInPage


class OptimizationView(BaseLoggedInPage):
    title = Text('//*[@id="main-content"]//h1')
    table = Table('//*[@id="main_div"]//table', column_widgets={"Action": Button("contains", "Queue Report")})
    refresh = Button(title="Refresh the list")

    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user
            and self.title.text == "Optimization"
            and self.table.is_displayed
            and self.navigation.currently_selected == ["Overview", "Optimization"]
        )

    # def queue_report(self, report_name):
    #     row = next(row for row in self.table.rows() if row["Report name"].text == report_name)
    #     report_run = int(row["Report runs"].text)
    #     row.action.widget.click()
    #     assert int(row["Report runs"].text) == report_run + 1
    #     self.flash.assert_no_error()