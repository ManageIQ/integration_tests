# -*- coding: utf-8 -*-
from time import sleep

import os
from lxml.html import document_fromstring
from widgetastic.exceptions import NoSuchElementException
from widgetastic.widget import (
    View, Text, TextInput, ParametrizedView, Image, ConditionalSwitchableView)
from widgetastic_patternfly import (
    Dropdown, BootstrapSelect, Tab, Input, CheckableBootstrapTreeview)

from cfme.base.login import BaseLoggedInPage
from cfme.exceptions import TemplateNotFound
from widgetastic_manageiq import (Calendar,
                                  Checkbox,
                                  SummaryTable,
                                  Button,
                                  ItemsToolBarViewSelector,
                                  Table,
                                  MultiBoxSelect,
                                  RadioGroup,
                                  VersionPick,
                                  Version,
                                  BaseEntitiesView,
                                  NonJSBaseEntity,
                                  BaseListEntity,
                                  BaseQuadIconEntity,
                                  BaseTileIconEntity,
                                  JSBaseEntity,
                                  BaseNonInteractiveEntitiesView,
                                  BreadCrumb,
                                  PaginationPane,
                                  DriftComparison)


class InstanceQuadIconEntity(BaseQuadIconEntity):
    """ Provider child of Quad Icon entity

    """
    @property
    def data(self):
        br = self.browser
        try:
            if br.product_version > '5.8':
                state = br.get_attribute('style', self.QUADRANT.format(pos='b'))
                state = state.split('"')[1]
            else:
                state = br.get_attribute('src', self.QUADRANT.format(pos='b'))

            state = os.path.split(state)[1]
            state = os.path.splitext(state)[0]
        except NoSuchElementException:
            return {}
        except IndexError:
            state = ''

        if br.is_displayed(self.QUADRANT.format(pos='g')):
            policy = br.get_attribute('src', self.QUADRANT.format(pos='g'))
        else:
            policy = None

        return {
            "os": br.get_attribute('src', self.QUADRANT.format(pos='a')),
            "state": state,
            "vendor": br.get_attribute('src', self.QUADRANT.format(pos='c')),
            "no_snapshot": br.text(self.QUADRANT.format(pos='d')),
            "policy": policy,
        }


class InstanceTileIconEntity(BaseTileIconEntity):
    """ Provider child of Tile Icon entity

    """
    quad_icon = ParametrizedView.nested(InstanceQuadIconEntity)


class InstanceListEntity(BaseListEntity):
    """ Provider child of List entity

    """
    pass


class NonJSInstanceEntity(NonJSBaseEntity):
    """ Provider child of Proxy entity

    """
    quad_entity = InstanceQuadIconEntity
    list_entity = InstanceListEntity
    tile_entity = InstanceTileIconEntity


class JSInstanceEntity(JSBaseEntity):
    @property
    def data(self):
        data_dict = super(JSInstanceEntity, self).data
        if 'quadicon' in data_dict and data_dict['quadicon']:
            try:
                quad_data = document_fromstring(data_dict['quadicon'])
                data_dict['os'] = quad_data.xpath(self.QUADRANT.format(pos="a"))[0].get('src')
                data_dict['vendor'] = quad_data.xpath(self.QUADRANT.format(pos="c"))[0].get('src')
                data_dict['no_snapshot'] = quad_data.xpath(self.QUADRANT.format(pos="d"))[0].text
            except IndexError:
                return {}

            try:
                state = quad_data.xpath(self.QUADRANT.format(pos="b"))[0].get('style')
                try:
                    state = state.split('"')[1]
                except IndexError:
                    state = state.split("'")[1]
                state = os.path.split(state)[1]
                state = os.path.splitext(state)[0]
            except IndexError:
                state = ''

            data_dict['state'] = state

            try:
                policy = quad_data.xpath(self.QUADRANT.format(pos="g"))[0].get('src')
            except:
                policy = None

            data_dict['policy'] = policy

        return data_dict


def InstanceEntity():  # noqa
    """ Temporary wrapper for Instance Entity during transition to JS based Entity

    """
    return VersionPick({
        Version.lowest(): NonJSInstanceEntity,
        '5.9': JSInstanceEntity,
    })


class SelectTable(Table):
    """Wigdet for non-editable table. used for selecting value"""
    def fill(self, values):
        """Clicks on item - fill by selecting required value"""
        value = values.get('name', '<None>')
        changed = False
        if value != self.currently_selected:
            changed = True
            self.row(name=value).click()
        return changed

    @property
    def currently_selected(self):
        """Return Name of the selected row"""
        selected = self.browser.elements(
            ".//tr[@class='selected']/td[1]",
            parent=self)
        result = map(self.browser.text, selected)
        if len(result) == 0:
            self.logger.info('Nothing is currently selected')
            return None
        else:
            return result[0]

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
    reload = Button(title=VersionPick({Version.lowest(): 'Reload current display',
                                       '5.9': 'Refresh this page'}))
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
        return InstanceEntity().pick(self.browser.product_version)

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
    properties = SummaryTable(title='Properties')
    lifecycle = SummaryTable(title='Lifecycle')
    relationships = SummaryTable(title='Relationships')
    vmsafe = SummaryTable(title='VMsafe')
    attributes = SummaryTable(title='Custom Attributes')  # Only displayed when assigned
    compliance = SummaryTable(title='Compliance')
    power_management = SummaryTable(title='Power Management')
    security = SummaryTable(title='Security')
    configuration = SummaryTable(title='Configuration')
    diagnostics = SummaryTable(title='Diagnostics')
    smart_management = SummaryTable(title='Smart Management')
    datastore_allocation_summary = SummaryTable(title='Datastore Allocation Summary')


class VMPropertyDetailView(View):
    title = Text('//div[@id="main-content"]//h1//span[@id="explorer_title_text"]')
    table = Table('//div[@id="gtl_div"]//table')

    paginator = PaginationPane()


class BasicProvisionFormView(View):
    @View.nested
    class request(Tab):  # noqa
        TAB_NAME = 'Request'
        email = Input(name='requester__owner_email')
        first_name = Input(name='requester__owner_first_name')
        last_name = Input(name='requester__owner_last_name')
        notes = Input(name='requester__request_notes')
        manager_name = Input(name='requester__owner_manager')

    @View.nested
    class purpose(Tab):  # noqa
        TAB_NAME = 'Purpose'
        apply_tags = CheckableBootstrapTreeview('all_tags_treebox')

    @View.nested
    class catalog(Tab):  # noqa
        TAB_NAME = 'Catalog'
        vm_name = Input(name='service__vm_name')
        vm_description = Input(name='service__vm_description')
        vm_filter = BootstrapSelect('service__vm_filter')
        num_vms = BootstrapSelect('service__number_of_vms')
        catalog_name = SelectTable('//div[@id="prov_vm_div"]/table')
        provision_type = BootstrapSelect('service__provision_type')
        linked_clone = Input(name='service__linked_clone')
        pxe_server = BootstrapSelect('service__pxe_server_id')
        pxe_image = SelectTable('//div[@id="prov_pxe_img_div"]/table')
        iso_file = SelectTable('//div[@id="prov_iso_img_div"]/table')

    @View.nested
    class environment(Tab):  # noqa
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
    class hardware(Tab):  # noqa
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
    class network(Tab):  # noqa
        TAB_NAME = 'Network'
        vlan = BootstrapSelect('network__vlan')

    @View.nested
    class properties(Tab):  # noqa
        TAB_NAME = 'Properties'
        instance_type = BootstrapSelect('hardware__instance_type')
        guest_keypair = BootstrapSelect('hardware__guest_access_key_pair')
        hardware_monitoring = BootstrapSelect('hardware__monitoring')
        boot_disk_size = BootstrapSelect('hardware__boot_disk_size')
        # GCE
        is_preemptible = Checkbox(name='hardware__is_preemptible')

    @View.nested
    class customize(Tab):  # noqa
        TAB_NAME = 'Customize'
        # Common
        dns_servers = Input(name='customize__dns_servers')
        dns_suffixes = Input(name='customize__dns_suffixes')
        customize_type = BootstrapSelect('customize__sysprep_enabled')
        specification_name = Table('//div[@id="prov_vc_div"]/table')
        admin_username = Input(name='customize__root_username')
        root_password = Input(name='customize__root_password')
        linux_host_name = Input(name='customize__linux_host_name')
        linux_domain_name = Input(name='customize__linux_domain_name')
        ip_address = Input(name='customize__ip_addr')
        subnet_mask = Input(name='customize__subnet_mask')
        gateway = Input(name='customize__gateway')
        custom_template = SelectTable('//div[@id="prov_template_div"]/table')
        hostname = Input(name='customize__hostname')

    @View.nested
    class schedule(Tab):  # noqa
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

    @View.nested
    class form(BasicProvisionFormView):  # noqa
        """First page of provision form is image selection
        Second page of form is tabbed with nested views
        """
        image_table = Table('//div[@id="pre_prov_div"]//table')
        continue_button = Button('Continue')  # Continue button on 1st page, image selection
        submit_button = Button('Submit')  # Submit for 2nd page, tabular form
        cancel_button = Button('Cancel')

        def before_fill(self, values):
            # Provision from image is a two part form,
            # this completes the image selection before the tabular parent form is filled
            template_name = values.get('template_name',
                                       self.parent_view.context['object'].template_name)
            provider_name = self.parent_view.context['object'].provider.name
            try:
                row = self.image_table.row(name=template_name,
                                           provider=provider_name)
            except IndexError:
                raise TemplateNotFound('Cannot find template "{}" for provider "{}"'
                                       .format(template_name, provider_name))
            row.click()
            self.continue_button.click()
            # TODO timing, wait_displayed is timing out and can't get it to stop in is_displayed
            sleep(3)
            self.flush_widget_cache()

    @property
    def is_displayed(self):
        return False


class CloneVmView(BaseLoggedInPage):
    title = Text('#explorer_title_text')

    @View.nested
    class form(BasicProvisionFormView):  # noqa
        submit_button = Button('Submit')
        cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return False


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

    @property
    def is_displayed(self):
        # TODO match quadicon and title
        return False


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

    @property
    def is_displayed(self):
        # Only name is displayed
        return False


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

    @property
    def is_displayed(self):
        # TODO match quadicon using entities, no provider match through icon asset yet
        return False


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

    @property
    def is_displayed(self):
        # Only the name is displayed
        return False


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

    @property
    def is_displayed(self):
        # TODO match quadicon
        return False


class RightSizeView(BaseLoggedInPage):
    """
    Right Size recommendations page for vms/instances
    """
    # TODO new table widget for right-size tables
    # They're H3 headers with the table as following-sibling

    @property
    def is_displayed(self):
        # Only name is displayed
        return False


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
