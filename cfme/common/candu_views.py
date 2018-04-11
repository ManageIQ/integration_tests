from widgetastic_manageiq import LineChart
from widgetastic.widget import View, Text, TextInput
from widgetastic_patternfly import BootstrapSelect


class OptionForm(View):
    interval = BootstrapSelect(id='perf_typ')
    compare_to = BootstrapSelect(id='compare_to')
    show_weeks_back = BootstrapSelect(id='perf_days')
    show_mints_back = BootstrapSelect(id='perf_minutes')
    range = Text("//div[label[contains(.,'Range')]]//p")
    time_profile = Text("//div[label[contains(.,'Time Profile')]]//p")
    calender = TextInput(locator=".//input[@id='miq_date_1']")


class VMUtilizationView(View):
    """A base view for VM Utilization"""
    title = Text(".//div[@id='main-content']//h1")
    options = View.nested(OptionForm)

    vm_cpu = LineChart(id='miq_chart_parent_candu_0')
    vm_cpu_state = LineChart(id='miq_chart_parent_candu_1')
    vm_memory = LineChart(id='miq_chart_parent_candu_2')
    vm_disk = LineChart(id='miq_chart_parent_candu_3')
    vm_network = LineChart(id='miq_chart_parent_candu_4')


class VMUtilizationAllView(VMUtilizationView):
    """A All view without select compare to option"""

    @property
    def is_displayed(self):
        if self.options.compare_to.is_displayed:
            return (
                "Capacity & Utilization data for Virtual Machine" in self.title.text and
                self.options.compare_to.selected_option == "<Nothing>"
            )
        else:
            return "Capacity & Utilization data for Virtual Machine" in self.title.text
