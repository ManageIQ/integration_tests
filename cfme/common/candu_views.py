from widgetastic.widget import ConditionalSwitchableView
from widgetastic.widget import Table
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import DatePicker

from widgetastic_manageiq import LineChart


class OptionForm(View):
    interval = BootstrapSelect(id='perf_typ')
    compare_to = BootstrapSelect(id='compare_to')
    group_by = BootstrapSelect(id='perf_cat')
    show_weeks_back = BootstrapSelect(id='perf_days')
    show_mints_back = BootstrapSelect(id='perf_minutes')
    range = Text("//div[label[contains(.,'Range')]]//p")
    time_profile = Text("//div[label[contains(.,'Time Profile')]]//p")
    calendar = DatePicker(id='miq_date_1')


class VMUtilizationView(View):
    """A base view for VM Utilization"""
    title = Text(".//div[@id='main-content']//h1")
    options = View.nested(OptionForm)

    @property
    def is_displayed(self):
        if self.options.compare_to.is_displayed:
            return (
                "Capacity & Utilization data for Virtual Machine" in self.title.text and
                self.options.compare_to.selected_option == "<Nothing>"
            )
        else:
            return 'Capacity & Utilization data for {}'.format(self.context['object'].VM_TYPE) in self.title.text



class UtilizationZoomView(View):
    chart = LineChart(id='miq_chart_parent_candu_0')
    child_chart = LineChart(id='miq_chart_parent_candu_0_2')
    table = Table('//*[@id="candu_charts_div"]/table')


class HostInfraUtilizationView(View):
    """View for Infrastructure provider Host Utilization"""
    title = Text(".//div[@id='main-content']//h1")
    options = View.nested(OptionForm)
    interval_type = ConditionalSwitchableView(reference='options.interval')

    @interval_type.register('Daily', default=True)
    class HostInfraDailyUtilizationView(View):
        """A view for Daily Interval Host Utilization"""
        host_cpu = LineChart(id='miq_chart_parent_candu_0')
        host_cpu_vm_avg = LineChart(id='miq_chart_parent_candu_0_2')
        host_cpu_state = LineChart(id='miq_chart_parent_candu_1')
        host_cpu_state_vm_avg = LineChart(id='miq_chart_parent_candu_1_2')
        host_memory = LineChart(id='miq_chart_parent_candu_2')
        host_memory_vm_avg = LineChart(id='miq_chart_parent_candu_2_2')
        host_disk = LineChart(id='miq_chart_parent_candu_3')
        host_disk_vm_avg = LineChart(id='miq_chart_parent_candu_3_2')
        host_network = LineChart(id='miq_chart_parent_candu_4')
        host_network_vm_avg = LineChart(id='miq_chart_parent_candu_4_2')
        host_vm = LineChart(id='miq_chart_parent_candu_5')

    @interval_type.register('Hourly')
    class HostInfraHourlyUtilizationView(View):
        """A view for Hourly Interval Host Utilization"""
        host_cpu = LineChart(id='miq_chart_parent_candu_0')
        host_cpu_vm_avg = LineChart(id='miq_chart_parent_candu_0_2')
        host_cpu_state = LineChart(id='miq_chart_parent_candu_1')
        host_cpu_state_vm_avg = LineChart(id='miq_chart_parent_candu_1_2')
        host_memory = LineChart(id='miq_chart_parent_candu_2')
        host_memory_vm_avg = LineChart(id='miq_chart_parent_candu_2_2')
        host_disk = LineChart(id='miq_chart_parent_candu_3')
        host_disk_vm_avg = LineChart(id='miq_chart_parent_candu_3_2')
        host_network = LineChart(id='miq_chart_parent_candu_4')
        host_network_vm_avg = LineChart(id='miq_chart_parent_candu_4_2')
        host_vm = LineChart(id='miq_chart_parent_candu_5')

    @interval_type.register('Most Recent Hour')
    class HostInfraRecentHourUtilizationView(View):
        """A view for Most Recent Hour Interval Host Utilization"""
        host_cpu = LineChart(id='miq_chart_parent_candu_0')
        host_memory = LineChart(id='miq_chart_parent_candu_2')
        host_disk = LineChart(id='miq_chart_parent_candu_3')
        host_network = LineChart(id='miq_chart_parent_candu_4')

    @property
    def is_displayed(self):
        expected_title = "{} Capacity & Utilization".format(self.context['object'].name)
        return self.title.text == expected_title and self.options.interval.is_displayed


class AzoneCloudUtilizationView(View):
    """View for Cloud provider Azone Utilization for Hourly and Daily"""
    title = Text(".//div[@id='main-content']//h1")
    options = View.nested(OptionForm)

    azone_cpu = LineChart(id='miq_chart_parent_candu_0')
    azone_cpu_avg = LineChart(id='miq_chart_parent_candu_0_2')
    azone_memory = LineChart(id='miq_chart_parent_candu_1')
    azone_memory_avg = LineChart(id='miq_chart_parent_candu_1_2')
    azone_disk = LineChart(id='miq_chart_parent_candu_2')
    azone_disk_avg = LineChart(id='miq_chart_parent_candu_2_2')
    azone_network = LineChart(id='miq_chart_parent_candu_3')
    azone_network_avg = LineChart(id='miq_chart_parent_candu_3_2')
    azone_instance = LineChart(id='miq_chart_parent_candu_4')

    @property
    def is_displayed(self):
        expected_title = "{} Capacity & Utilization".format(self.context["object"].name)
        return self.title.text == expected_title


class ClusterInfraUtilizationView(View):
    """View for Infrastructure provider Cluster Utilization Hourly and Daily"""
    title = Text(".//div[@id='main-content']//h1")
    options = View.nested(OptionForm)

    cluster_cpu = LineChart(id="miq_chart_parent_candu_0")
    cluster_cpu_vm_host_avg = LineChart(id="miq_chart_parent_candu_0_2")
    cluster_cpu_state = LineChart(id="miq_chart_parent_candu_1")
    cluster_cpu_state_vm_host_avg = LineChart(id="miq_chart_parent_candu_1_2")
    cluster_memory = LineChart(id="miq_chart_parent_candu_2")
    cluster_memory_vm_host_avg = LineChart(id="miq_chart_parent_candu_2_2")
    cluster_disk = LineChart(id="miq_chart_parent_candu_3")
    cluster_disk_vm_host_avg = LineChart(id="miq_chart_parent_candu_3_2")
    cluster_network = LineChart(id="miq_chart_parent_candu_4")
    cluster_network_vm_host_avg = LineChart(id="miq_chart_parent_candu_4_2")
    cluster_host = LineChart(id="miq_chart_parent_candu_5")
    cluster_vm = LineChart(id="miq_chart_parent_candu_6")

    @property
    def is_displayed(self):
        expected_title = "{} Capacity & Utilization".format(self.context['object'].name)
        return self.title.text == expected_title


class DatastoreInfraUtilizationView(View):
    """View for Infrastructure provider Datastore Utilization Hourly and Daily"""

    title = Text(".//div[@id='main-content']//h1")
    options = View.nested(OptionForm)
    interval_type = ConditionalSwitchableView(reference="options.interval")

    @interval_type.register("Hourly", default=True)
    class DatastoreInfraHourlyUtilizationView(View):
        datastore_used_disk_space = LineChart(id="miq_chart_parent_candu_5")
        datastore_hosts = LineChart(id="miq_chart_parent_candu_6")
        datastore_vms = LineChart(id="miq_chart_parent_candu_7")

    @interval_type.register("Daily")
    class DatastoreInfraDailyUtilizationView(View):
        datastore_use_space_by_type = LineChart(id="miq_chart_parent_candu_0")
        datastore_disk_files_space_by_type = LineChart(id="miq_chart_parent_candu_1")
        datastore_snapshot_files_space_by_type = LineChart(id="miq_chart_parent_candu_2")
        datastore_memory_files_space_by_type = LineChart(id="miq_chart_parent_candu_3")
        datastore_vms_by_type = LineChart(id="miq_chart_parent_candu_4")
        datastore_used_disk_space = LineChart(id="miq_chart_parent_candu_5")
        datastore_hosts = LineChart(id="miq_chart_parent_candu_6")
        datastore_vms = LineChart(id="miq_chart_parent_candu_7")

    @property
    def is_displayed(self):
        expected_title = "{} Capacity & Utilization".format(self.context["object"].name)
        return self.title.text == expected_title
