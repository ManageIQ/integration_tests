# -*- coding: utf-8 -*-
import os

from lxml.html import document_fromstring
from widgetastic.widget import (
    View, TableRow, Text, TextInput, ParametrizedView, Image, ConditionalSwitchableView)
from widgetastic_patternfly import (
    BreadCrumb, Dropdown, BootstrapSelect, Input, CheckableBootstrapTreeview)

from cfme.base.login import BaseLoggedInPage
from cfme.exceptions import TemplateNotFound, displayed_not_implemented
from cfme.utils.log import logger
from cfme.utils.wait import wait_for
from widgetastic_manageiq import (
    Calendar, Checkbox, Button, ItemsToolBarViewSelector, Table, MultiBoxSelect, RadioGroup,
    BaseEntitiesView, JSBaseEntity, BaseNonInteractiveEntitiesView, PaginationPane, DriftComparison,
    ParametrizedSummaryTable, WaitTab
)


class InstanceEntity(JSBaseEntity):
    @property
    def data(self):
        data_dict = super(InstanceEntity, self).data
        if 'quadicon' in data_dict and data_dict['quadicon']:
            try:
                quad_data = document_fromstring(data_dict['quadicon'])
                data_dict['os'] = quad_data.xpath(self.QUADRANT.format(pos="a"))[0].get('src')
                data_dict['vendor'] = quad_data.xpath(self.QUADRANT.format(pos="c"))[0].get('src')
                data_dict['no_snapshot'] = quad_data.xpath(self.QUADRANT.format(pos="d"))[0].text
            except IndexError:
                return {}

            try:
                state_property = 'src' if self.browser.product_version == 'master' else 'style'
                state = quad_data.xpath(self.QUADRANT.format(pos="b"))[0].get(state_property)

                try:
                    state = state.split('"')[1]
                except IndexError:
                    pass
                try:
                    state = state.split("'")[1]
                except IndexError:
                    pass

                state = os.path.split(state)[1]
                state = os.path.splitext(state)[0]
                state = state.split("-")[1]
            except IndexError:
                state = ''

            data_dict['state'] = state

            try:
                policy = quad_data.xpath(self.QUADRANT.format(pos="g"))[0].get('src')
            except Exception:
                policy = None

            data_dict['policy'] = policy
        elif data_dict.get('quad'):
            # 5.10 doesn't have quadicon
            data_dict['os'] = data_dict['quad']['topLeft']['tooltip']
            data_dict['vendor'] = data_dict['quad']['bottomLeft']['tooltip']
            try:
                data_dict['no_snapshots'] = data_dict['total_snapshots']
            # openstack instances require this
            except KeyError:
                data_dict['no_snapshots'] = data_dict['quad']['bottomRight']['text']
            data_dict['state'] = data_dict['quad']['topRight']['tooltip']

        return data_dict


class SelectableTableRow(TableRow):

    @property
    def selected(self):
        return 'selected' in self.browser.classes(self)


class SelectTable(Table):
    """Wigdet for non-editable table. used for selecting value"""

    Row = SelectableTableRow

    def fill(self, values):
        """Clicks on item - fill by selecting required values"""
        if self.row(**values).selected:
            return False
        else:
            self.row(**values).click()
            return True

    @property
    def currently_selected(self):
        """Return values of the selected row"""
        for row in self.rows:
            if row.selected:
                return row.read()
        else:
            self.logger.info('Nothing is currently selected')
            return None

    def read(self):
        return self.currently_selected

    def read_content(self):
        """This is a default Table.read() method for those who will need table content"""
        return super(SelectTable, self).read()


class VMToolbar(View):
    """
    Toolbar view for vms/instances collection destinations
    """
    "Refresh this page"
    reload = Button(title='Refresh this page')
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    lifecycle = Dropdown('Lifecycle')
    power = Dropdown('Power Operations')  # title
    download = Dropdown('Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class VMEntities(BaseEntitiesView):
    """
    Entities view for vms/instances collection destinations
    """
    @property
    def entity_class(self):
        return InstanceEntity

    paginator = PaginationPane()
    adv_search_clear = Text('//div[@id="main-content"]//h1//span[@id="clear_search"]/a')


class HostAllVMsView(BaseLoggedInPage):
    """
    This view is used in test_host_relationships
    """

    title = Text(".//div[@id='main-content']//h1")

    @property
    def is_displayed(self):
        if self.browser.product_version < "5.9":
            title = "{} (All VMs)".format(self.context["object"].name)
        else:
            title = "{} (All Direct VMs)".format(self.context["object"].name)
        return (
            self.navigation.currently_selected == ["Compute", "Infrastructure", "Hosts"] and
            self.title.text == title
        )


class ProviderAllVMsView(BaseLoggedInPage):
    """
    This view is used in test_provider_relationships
    """

    title = Text(".//div[@id='main-content']//h1")

    @property
    def is_displayed(self):
        msg = "{} (All Direct VMs)".format(self.context["object"].name)
        return (
            self.navigation.currently_selected == ["Compute", "Infrastructure", "Providers"] and
            self.title.text == msg
        )


class VMDetailsEntities(View):
    """
    Details entities view for vms/instances details destinations

    VM's have 3-4 more tables, should inherit and add them there.
    """
    title = Text('//div[@id="main-content"]//h1//span[@id="explorer_title_text"]')
    summary = ParametrizedView.nested(ParametrizedSummaryTable)


class VMPropertyDetailView(View):
    title = Text('//div[@id="main-content"]//h1//span[@id="explorer_title_text"]')
    table = Table('//div[@id="gtl_div"]//table')

    paginator = PaginationPane()


class BasicProvisionFormView(View):
    @View.nested
    class request(WaitTab):  # noqa
        TAB_NAME = 'Request'
        email = Input(name='requester__owner_email')
        first_name = Input(name='requester__owner_first_name')
        last_name = Input(name='requester__owner_last_name')
        notes = Input(name='requester__request_notes')
        manager_name = Input(name='requester__owner_manager')

    @View.nested
    class purpose(WaitTab):  # noqa
        TAB_NAME = 'Purpose'
        apply_tags = CheckableBootstrapTreeview('all_tags_treebox')

    @View.nested
    class catalog(WaitTab):  # noqa
        TAB_NAME = 'Catalog'

        # Filling catalog template first so that environment tab gets enough time to load
        catalog_name = SelectTable('//div[@id="prov_vm_div"]/table')
        vm_name = Input(name='service__vm_name')
        vm_description = Input(name='service__vm_description')
        vm_filter = BootstrapSelect('service__vm_filter')
        num_vms = BootstrapSelect('service__number_of_vms')
        provision_type = BootstrapSelect('service__provision_type')
        linked_clone = Input(name='service__linked_clone')
        pxe_server = BootstrapSelect('service__pxe_server_id')
        pxe_image = SelectTable('//div[@id="prov_pxe_img_div"]/table')
        iso_file = SelectTable('//div[@id="prov_iso_img_div"]/table')

    @View.nested
    class environment(WaitTab):  # noqa
        TAB_NAME = 'Environment'
        automatic_placement = Checkbox(id='environment__placement_auto')
        # Cloud
        availability_zone = BootstrapSelect('environment__placement_availability_zone')
        cloud_network = BootstrapSelect('environment__cloud_network')
        cloud_subnet = BootstrapSelect('environment__cloud_subnet')
        cloud_tenant = BootstrapSelect('environment__cloud_tenant')  # exists for azure in catalogs
        security_groups = BootstrapSelect('environment__security_groups')
        resource_groups = BootstrapSelect('environment__resource_group')
        public_ip_address = BootstrapSelect('environment__floating_ip_address')
        # Infra
        provider_name = BootstrapSelect('environment__placement_ems_name')
        datacenter = BootstrapSelect('environment__placement_dc_name')
        cluster = BootstrapSelect('environment__placement_cluster_name')
        resource_pool = BootstrapSelect('environment__placement_rp_name')
        folder = BootstrapSelect('environment__placement_folder_name')
        host_filter = BootstrapSelect('environment__host_filter')
        host_name = SelectTable('//div[@id="prov_host_div"]/table')
        datastore_create = Input('environment__new_datastore_create')
        datastore_filter = BootstrapSelect('environment__ds_filter')
        datastore_name = SelectTable('//div[@id="prov_ds_div"]/table')

    @View.nested
    class hardware(WaitTab):  # noqa
        TAB_NAME = 'Hardware'
        num_sockets = BootstrapSelect('hardware__number_of_sockets')
        cores_per_socket = BootstrapSelect('hardware__cores_per_socket')
        num_cpus = BootstrapSelect('hardware__number_of_cpus')
        memory = BootstrapSelect('hardware__vm_memory')
        disk_format = RadioGroup(locator=('//div[@id="hardware"]'
                                          '//div[./div[contains(@class, "radio")]]'))
        vm_limit_cpu = Input(name='hardware__cpu_limit')
        vm_limit_memory = Input(name='hardware__memory_limit')
        vm_reserve_cpu = Input(name='hardware__cpu_reserve')
        vm_reserve_memory = Input(name='hardware__memory_reserve')

    @View.nested
    class network(WaitTab):  # noqa
        TAB_NAME = 'Network'
        vlan = BootstrapSelect('network__vlan')

    @View.nested
    class properties(WaitTab):  # noqa
        TAB_NAME = 'Properties'
        instance_type = BootstrapSelect('hardware__instance_type')
        guest_keypair = BootstrapSelect('hardware__guest_access_key_pair')
        hardware_monitoring = BootstrapSelect('hardware__monitoring')
        boot_disk_size = BootstrapSelect('hardware__boot_disk_size')
        # GCE
        is_preemptible = Checkbox(name='hardware__is_preemptible')

    @View.nested
    class customize(WaitTab):  # noqa
        TAB_NAME = 'Customize'
        # Common
        customize_type = BootstrapSelect('customize__sysprep_enabled')
        root_password = Input(name='customize__root_password')
        address_mode = RadioGroup(locator=('//div[@id="customize"]'
                                           '//div[./div[contains(@class, "radio")]]'))
        hostname = Input(name='customize__hostname')
        ip_address = Input(name='customize__ip_addr')
        subnet_mask = Input(name='customize__subnet_mask')
        gateway = Input(name='customize__gateway')
        dns_servers = Input(name='customize__dns_servers')
        dns_suffixes = Input(name='customize__dns_suffixes')
        specification_name = Table('//div[@id="prov_vc_div"]/table')
        admin_username = Input(name='customize__root_username')
        linux_host_name = Input(name='customize__linux_host_name')
        linux_domain_name = Input(name='customize__linux_domain_name')
        custom_template = SelectTable('//div[@id="prov_template_div"]/table')

    @View.nested
    class schedule(WaitTab):  # noqa
        TAB_NAME = 'Schedule'
        # Common
        schedule_type = RadioGroup(locator=('//div[@id="schedule"]'
                                            '//div[./div[contains(@class, "radio")]]'))
        provision_date = Calendar('miq_date_1')
        provision_start_hour = BootstrapSelect('start_hour')
        provision_start_min = BootstrapSelect('start_min')
        power_on = Checkbox(name='schedule__vm_auto_start')
        retirement = BootstrapSelect('schedule__retirement')
        retirement_warning = BootstrapSelect('schedule__retirement_warn')
        # Infra
        stateless = Input(name='schedule__stateless')


class ProvisionView(BaseLoggedInPage):
    """
    The provisioning view, with nested ProvisioningForm as `form` attribute.
    Handles template selection before Provisioning form with `before_fill` method
    """
    title = Text('#explorer_title_text')
    breadcrumb = BreadCrumb()
    image_table = Table('//div[@id="pre_prov_div"]//table')

    @View.nested
    class sidebar(View):  # noqa
        increase_button = Text(locator='//div[contains(@class, "resize-right")]')
        decrease_button = Text(locator='//div[contains(@class, "resize-left")]')

    @View.nested
    class form(BasicProvisionFormView):  # noqa
        """First page of provision form is image selection
        Second page of form is tabbed with nested views
        """
        continue_button = Button('Continue')  # Continue button on 1st page, image selection
        submit_button = Button('Submit')  # Submit for 2nd page, tabular form
        cancel_button = Button('Cancel')

        def _select_template(self, template_name, provider_name):
            try:
                row = self.parent.image_table.row(name=template_name, provider=provider_name)
                row.click()
            except IndexError:
                raise TemplateNotFound('Cannot find template "{}" for provider "{}"'
                                       .format(template_name, provider_name))

        def before_fill(self, values):
            # Provision from image is a two part form,
            # this completes the image selection before the tabular parent form is filled
            template_name = values.get('template_name')
            provider_name = values.get('provider_name')
            if template_name is None or provider_name is None:
                logger.error('template_name "{}", or provider_name "{}" not passed to '
                             'provisioning form', template_name, provider_name)
            # try to find the template anyway, even if values weren't passed
            self._select_template(template_name, provider_name)
            # workaround for provision table template select(template was not clicked)
            if self.continue_button.disabled:
                self.parent.sidebar.decrease_button.click()
                self._select_template(template_name, provider_name)
            self.continue_button.click()
            wait_for(self.browser.plugin.ensure_page_safe, delay=.1, num_sec=10)

    is_displayed = displayed_not_implemented


class CloneVmView(BaseLoggedInPage):
    title = Text('#explorer_title_text')

    @View.nested
    class form(BasicProvisionFormView):  # noqa
        submit_button = Button('Submit')
        cancel_button = Button('Cancel')

    is_displayed = displayed_not_implemented


class MigrateVmView(BaseLoggedInPage):
    title = Text('#explorer_title_text')

    @View.nested
    class form(BasicProvisionFormView):  # noqa
        submit = Button('Submit')
        cancel = Button('Cancel')

    is_displayed = displayed_not_implemented


class PublishVmView(BaseLoggedInPage):
    title = Text('#explorer_title_text')

    @View.nested
    class form(BasicProvisionFormView):  # noqa
        submit_button = Button('Submit')
        cancel_button = Button('Cancel')

    is_displayed = displayed_not_implemented


class RetirementView(BaseLoggedInPage):
    """
    Set Retirement date view for vms/instances
    The title actually as Instance|VM.VM_TYPE string in it, otherwise the same
    """
    title = Text('#explorer_title_text')

    @View.nested
    class form(View):  # noqa
        retirement_date = Calendar(name='retirementDate')
        remove_date = Image(locator='.//div[@id="retirement_date_div"]//a/img[@alt="Set to blank"]')
        retirement_warning = BootstrapSelect(id='retirementWarning')
        entities = View.nested(BaseNonInteractiveEntitiesView)
        save = Button('Save')
        cancel = Button('Cancel')

    # TODO match quadicon and title
    is_displayed = displayed_not_implemented


class RetirementViewWithOffset(RetirementView):
    """The form portion, with 59z+ offset mode selection"""
    @View.nested
    class form(View):  # noqa
        retirement_mode = BootstrapSelect(id='formMode')
        retirement_date = ConditionalSwitchableView(reference='retirement_mode')

        @retirement_date.register('Specific Date and Time', default=True)
        class RetirementDateSelectionView(View):
            datetime_select = TextInput(id='retirement_date_datepicker')

        @retirement_date.register('Time Delay from Now')
        class RetirementOffsetSelectionView(View):
            # TODO unique widget for these touchspin elements, with singular fill method
            # will allow for consistent fill of view.form
            months = TextInput(name='months')
            weeks = TextInput(name='weeks')
            days = TextInput(name='days')
            hours = TextInput(name='hours')
            retirement_offset_datetime = Text(
                locator='.//div[@id="retirement_date_result_div"]/input[@id="retirement_date"]')

        retirement_warning = BootstrapSelect(id='retirementWarning')
        entities = View.nested(BaseNonInteractiveEntitiesView)
        save = Button('Save')
        cancel = Button('Cancel')


class EditView(BaseLoggedInPage):
    """
    Edit vms/instance page
    The title actually as Instance|VM.VM_TYPE string in it, otherwise the same
    """
    title = Text('#explorer_title_text')

    @View.nested
    class form(View):  # noqa
        """The form portion of the view"""
        custom_identifier = TextInput(id='custom_1')
        description = TextInput(id='description')
        parent_vm = BootstrapSelect(id='chosen_parent')
        # MultiBoxSelect element only has table ID in CFME 5.8+
        # https://bugzilla.redhat.com/show_bug.cgi?id=1463265
        child_vms = MultiBoxSelect(id='child-vm-select')
        save_button = Button('Save')
        reset_button = Button('Reset')
        cancel_button = Button('Cancel')

    # Only name is displayed
    is_displayed = displayed_not_implemented


class SetOwnershipView(BaseLoggedInPage):
    """
    Set vms/instance ownership page
    The title actually as Instance|VM.VM_TYPE string in it, otherwise the same
    """
    @View.nested
    class form(View):  # noqa
        user_name = BootstrapSelect('user_name')
        group_name = BootstrapSelect('group_name')
        entities = View.nested(BaseNonInteractiveEntitiesView)
        save_button = Button('Save')
        reset_button = Button('Reset')
        cancel_button = Button('Cancel')

    # TODO match quadicon using entities, no provider match through icon asset yet
    is_displayed = displayed_not_implemented


class RenameVmView(BaseLoggedInPage):
    """Rename VM page for VMs"""

    title = Text('#explorer_title_text')

    @View.nested
    class form(View):  # noqa
        vm_name = Input("name")
        save_button = Button('Save')
        reset_button = Button('Reset')
        cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return self.title.text == 'Renaming VM "{}"'.format(self.context['object'].name)


class ManagementEngineView(BaseLoggedInPage):
    """
    Edit management engine relationship page
    The title actually as Instance|VM.VM_TYPE string in it, otherwise the same
    """

    @View.nested
    class form(View):  # noqa
        server = BootstrapSelect('server_id')
        save_button = Button('Save')
        reset_button = Button('Reset')
        cancel_button = Button('Cancel')

    # Only name is displayed
    is_displayed = displayed_not_implemented


class PolicySimulationView(BaseLoggedInPage):
    """
    Policy Simulation page for vms/instances
    """
    @View.nested
    class form(View):  # noqa
        policy = BootstrapSelect('policy_id')
        # TODO policies table, ability to remove
        entities = View.nested(BaseNonInteractiveEntitiesView)
        cancel_button = Button('Cancel')

    # TODO match quadicon
    is_displayed = displayed_not_implemented


class RightSizeView(BaseLoggedInPage):
    """
    Right Size recommendations page for vms/instances
    """
    # TODO new table widget for right-size tables
    # They're H3 headers with the table as following-sibling

    # Only name is displayed
    is_displayed = displayed_not_implemented


class DriftHistory(BaseLoggedInPage):
    title = Text('#explorer_title_text')
    breadcrumb = BreadCrumb(locator='.//ol[@class="breadcrumb"]')
    history_table = Table(locator='.//div[@id="main_div"]/table')
    analyze_button = Button(title="Select up to 10 timestamps for Drift Analysis")

    @property
    def is_displayed(self):
        return (
            "Drift History" in self.title.text and
            self.history_table.is_displayed
        )


class DriftAnalysis(BaseLoggedInPage):
    title = Text('#explorer_title_text')
    apply_button = Button("Apply")
    drift_sections = CheckableBootstrapTreeview(tree_id="all_sectionsbox")
    drift_analysis = DriftComparison(locator=".//div[@id='compare-grid']")

    @View.nested
    class toolbar(View):  # noqa
        all_attributes = Button(title="All attributes")
        different_values_attributes = Button(title="Attributes with different values")
        same_values_attributes = Button(title="Attributes with same values")
        details_mode = Button(title="Details Mode")
        exists_mode = Button(title="Exists Mode")

    @property
    def is_displayed(self):
        return (
            self.title.text == 'Drift for VM or Template "{}"'.format(self.context["object"].name)
        )
