from navmazing import NavigateToAttribute
from widgetastic.widget import View
from widgetastic_manageiq import (Button, Table, Checkbox, Input, LineChart,
                                  SummaryFormItem, BootstrapSelect)
from widgetastic_patternfly import Tab

from cfme.base.login import BaseLoggedInPage
from cfme.utils.appliance import NavigatableMixin
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep

locator = ('.//h3[normalize-space(.)={}]/following-sibling::dl//'
           'dt[normalize-space(.)={}]/following-sibling::dd')


class PlanningView(BaseLoggedInPage):
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

    @View.nested
    class planning_summary(View):  # noqa

        @View.nested
        class summary(Tab):  # noqa
            display_vms_limit = BootstrapSelect('display_vms')
            vm_planning_chart = LineChart(id='miq_chart_planning_0')
            table = Table('//table[@class="table table-bordered table-striped"]')
            vm_mode = SummaryFormItem('Reference VM Profile', 'Source', locator=locator)
            cpu_speed = SummaryFormItem('Reference VM Profile', 'CPU Speed', locator=locator)
            vcpu_count = SummaryFormItem('Reference VM Profile', 'vCPU Count', locator=locator)
            memory_size = SummaryFormItem('Reference VM Profile', 'Memory Size', locator=locator)
            disk_space = SummaryFormItem('Reference VM Profile', 'Disk Space', locator=locator)
            target_type = SummaryFormItem('Target Options/Limits', 'Show', locator=locator)
            cpu_speed_limit = SummaryFormItem('Target Options/Limits', 'CPU Speed', locator=locator)
            vcpu_per_core = SummaryFormItem('Target Options/Limits', 'vCPU per Core',
                                            locator=locator)
            memory_size_limit = SummaryFormItem('Target Options/Limits', 'Memory Size',
                                                locator=locator)
            datastore_space_limit = SummaryFormItem('Target Options/Limits', 'Datastore Space',
                                                    locator=locator)
            trend_for_past = SummaryFormItem('Trend Options', 'Trend for Past', locator=locator)

        @View.nested
        class report(Tab):  # noqa
            table = Table('//table[@class="table table-striped table-bordered"]')
            vm_mode = SummaryFormItem('Reference VM Profile', 'Source', locator=locator)
            cpu_speed = SummaryFormItem('Reference VM Profile', 'CPU Speed', locator=locator)
            vcpu_count = SummaryFormItem('Reference VM Profile', 'vCPU Count', locator=locator)
            memory_size = SummaryFormItem('Reference VM Profile', 'Memory Size', locator=locator)
            disk_space = SummaryFormItem('Reference VM Profile', 'Disk Space', locator=locator)
            target_type = SummaryFormItem('Target Options/Limits', 'Show', locator=locator)
            cpu_speed_limit = SummaryFormItem('Target Options/Limits', 'CPU Speed', locator=locator)
            vcpu_per_core = SummaryFormItem('Target Options/Limits', 'vCPU per Core',
                                            locator=locator)
            memory_size_limit = SummaryFormItem('Target Options/Limits', 'Memory Size',
                                                locator=locator)
            datastore_space_limit = SummaryFormItem('Target Options/Limits', 'Datastore Space',
                                                    locator=locator)
            trend_for_past = SummaryFormItem('Trend Options', 'Trend for Past', locator=locator)

    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Optimize', 'Planning'])


class Planning(NavigatableMixin):
    pass


@navigator.register(Planning, 'All')
class All(CFMENavigateStep):
    VIEW = PlanningView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Optimize', 'Planning')
