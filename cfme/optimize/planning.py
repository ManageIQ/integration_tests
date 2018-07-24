from navmazing import NavigateToAttribute
from widgetastic.widget import View
from widgetastic_patternfly import Tab

from cfme.base.login import BaseLoggedInPage
from cfme.modeling.base import BaseCollection
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep
from widgetastic_manageiq import (BootstrapSelect, Button, Checkbox, Input, LineChart,
                                  SummaryFormItem, Table)


class PlanningFilter(BaseLoggedInPage):
    # Reference VM Selection
    filter_type = BootstrapSelect('filter_typ')
    filter_value = BootstrapSelect('filter_value')
    chosen_vm = BootstrapSelect('chosen_vm')
    # VM Options
    vm_mode = BootstrapSelect('vm_mode')
    cpu_speed = Checkbox('trend_cpu')
    cpu_speed_input = Input('trend_cpu_val')
    vcpu_count = Checkbox('trend_vcpus')
    vcpu_count_input = Input('trend_vcpus_val')
    memory_size = Checkbox('trend_memory')
    memory_size_input = Input('trend_memory_val')
    disk_space = Checkbox('trend_storage')
    disk_space_input = Input('trend_storage_val')
    # Target Options / Limits
    target_type = BootstrapSelect('target_typ')
    cpu_speed_limit = BootstrapSelect('limit_cpu')
    vcpu_per_core_limit = BootstrapSelect('limit_vcpus')
    memory_size_limit = BootstrapSelect('limit_memory')
    datastore_space_limit = BootstrapSelect('limit_storage')
    # Trend Options
    trends_for_past = BootstrapSelect('trend_days')

    submit = Button('Submit')
    reset = Button('Reset')


class PlanningSummaryTab(Tab):
    TAB_NAME = "Summary"

    display_vms_limit = BootstrapSelect('display_vms')
    vm_planning_chart = LineChart(id='miq_chart_planning_0')
    table = Table('//table[@class="table table-bordered table-striped"]')
    vm_mode = SummaryFormItem('Reference VM Profile', 'Source')
    cpu_speed = SummaryFormItem('Reference VM Profile', 'CPU Speed')
    vcpu_count = SummaryFormItem('Reference VM Profile', 'vCPU Count')
    memory_size = SummaryFormItem('Reference VM Profile', 'Memory Size')
    disk_space = SummaryFormItem('Reference VM Profile', 'Disk Space')
    target_type = SummaryFormItem('Target Options/Limits', 'Show')
    cpu_speed_limit = SummaryFormItem('Target Options/Limits', 'CPU Speed')
    vcpu_per_core = SummaryFormItem('Target Options/Limits', 'vCPU per Core')
    memory_size_limit = SummaryFormItem('Target Options/Limits', 'Memory Size')
    datastore_space_limit = SummaryFormItem('Target Options/Limits', 'Datastore Space')
    trend_for_past = SummaryFormItem('Trend Options', 'Trend for Past')


class PlanningReportTab(Tab):
    TAB_NAME = "Report"

    table = Table('//table[@class="table table-striped table-bordered"]')
    vm_mode = SummaryFormItem('Reference VM Profile', 'Source')
    cpu_speed = SummaryFormItem('Reference VM Profile', 'CPU Speed')
    vcpu_count = SummaryFormItem('Reference VM Profile', 'vCPU Count')
    memory_size = SummaryFormItem('Reference VM Profile', 'Memory Size')
    disk_space = SummaryFormItem('Reference VM Profile', 'Disk Space')
    target_type = SummaryFormItem('Target Options/Limits', 'Show')
    cpu_speed_limit = SummaryFormItem('Target Options/Limits', 'CPU Speed')
    vcpu_per_core = SummaryFormItem('Target Options/Limits', 'vCPU per Core')
    memory_size_limit = SummaryFormItem('Target Options/Limits', 'Memory Size')
    datastore_space_limit = SummaryFormItem('Target Options/Limits', 'Datastore Space')
    trend_for_past = SummaryFormItem('Trend Options', 'Trend for Past')


class PlanningView(BaseLoggedInPage):

    planning_filter = View.nested(PlanningFilter)

    @View.nested
    class planning_summary(View):  # noqa
        summary = View.nested(PlanningSummaryTab)
        report = View.nested(PlanningReportTab)

    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Optimize', 'Planning'])


class PlanningCollection(BaseCollection):
    pass


@navigator.register(PlanningCollection, 'All')
class All(CFMENavigateStep):
    VIEW = PlanningView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Optimize', 'Planning')
