import pytest
from lxml.html import document_fromstring
from widgetastic.exceptions import NoSuchElementException
from widgetastic.utils import Version
from widgetastic.widget import ConditionalSwitchableView
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapNav
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import BreadCrumb
from widgetastic_patternfly import Dropdown

from cfme.common import BaseLoggedInPage
from cfme.common import CompareView
from cfme.common import TimelinesView
from cfme.common.host_views import HostEntitiesView
from cfme.utils.version import VersionPicker
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import Button
from widgetastic_manageiq import Checkbox
from widgetastic_manageiq import DetailsToolBarViewSelector
from widgetastic_manageiq import Input
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import JSBaseEntity
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import PaginationPane
from widgetastic_manageiq import ParametrizedStatusBox
from widgetastic_manageiq import ParametrizedSummaryTable
from widgetastic_manageiq import Search
from widgetastic_manageiq import WaitTab


class ProviderEntity(JSBaseEntity):
    @property
    def data(self):
        data_dict = super().data
        try:
            if 'quadicon' in data_dict and data_dict['quadicon']:
                quad_data = document_fromstring(data_dict['quadicon'])
                data_dict['no_host'] = int(quad_data.xpath(self.QUADRANT.format(pos="a"))[0].text)
                data_dict['vendor'] = quad_data.xpath(self.QUADRANT.format(pos="c"))[0].get('src')
                data_dict['creds'] = quad_data.xpath(self.QUADRANT.format(pos="d"))[0].get('src')
            return data_dict
        except (IndexError, TypeError, NoSuchElementException):
            return {}


class ProviderDetailsToolBar(View):
    """
    represents provider toolbar and its controls
    """
    monitoring = Dropdown(text='Monitoring')
    configuration = Dropdown(text='Configuration')
    reload = Button(title='Refresh this page')
    policy = Dropdown(text='Policy')
    authentication = Dropdown(text='Authentication')
    download = Button(title='Print or export summary')

    view_selector = View.nested(DetailsToolBarViewSelector)


class SummaryAccordionView(View):

    @View.nested
    class properties(Accordion):    # noqa
        ACCORDION_NAME = "Properties"
        tree = BootstrapNav(locator='//div[@id="ems_prop"]//ul')

    @View.nested
    class relationships(Accordion):    # noqa
        ACCORDION_NAME = "Relationships"
        tree = BootstrapNav(locator='//div[@id="ems_rel"]//ul')


class ProviderDetailsView(BaseLoggedInPage):
    """
     main Details page
    """
    title = Text('//div[@id="main-content"]//h1')
    breadcrumb = BreadCrumb(locator='//ol[@class="breadcrumb"]')
    toolbar = View.nested(ProviderDetailsToolBar)

    entities = ConditionalSwitchableView(reference='toolbar.view_selector',
                                         ignore_bad_reference=True)

    @entities.register('Summary View', default=True)
    class ProviderDetailsSummaryView(View):
        """
        represents Details page when it is switched to Summary aka Tables view
        """
        summary = ParametrizedSummaryTable()
        sidebar = View.nested(SummaryAccordionView)

    @entities.register('Dashboard View')
    class ProviderDetailsDashboardView(View):
        """
         represents Details page when it is switched to Dashboard aka Widgets view
        """
        cards = ParametrizedStatusBox()

    @property
    def is_displayed(self):
        subtitle = 'Summary'
        if self.toolbar.view_selector.is_displayed:
            subtitle = self.toolbar.view_selector.selected.split(' ')[0]

        title = '{name} ({subtitle})'.format(
            name=self.context['object'].name,
            subtitle=subtitle
        )
        return (self.logged_in_as_current_user and
                self.breadcrumb.is_displayed and
                self.breadcrumb.active_location == title)  # BZ 1703744


class InfraProviderDetailsView(ProviderDetailsView):
    """
     Infra Details page
    """
    @property
    def is_displayed(self):
        return (super().is_displayed and
                self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'])


class CloudProviderDetailsView(ProviderDetailsView):
    """
     Cloud Details page
    """
    @property
    def is_displayed(self):
        return (super().is_displayed and
                self.navigation.currently_selected == ['Compute', 'Clouds', 'Providers'])


class PhysicalProviderDetailsView(ProviderDetailsView):
    """
     Physical  Details page
    """
    @property
    def is_displayed(self):
        return (super().is_displayed and
                self.navigation.currently_selected == ['Compute',
                                                       'Physical Infrastructure',
                                                       'Providers'])


class ProviderTimelinesView(TimelinesView, BaseLoggedInPage):
    """
     represents Timelines page
    """
    pass


class InfraProvidersDiscoverView(BaseLoggedInPage):
    """
     Discover View from Infrastructure Providers page
    """
    title = Text('//div[@id="main-content"]//h1')

    vmware = Checkbox('discover_type_virtualcenter')
    scvmm = Checkbox('discover_type_scvmm')
    rhevm = Checkbox('discover_type_rhevm')
    osp_infra = Checkbox('discover_type_openstack_infra')

    from_ip1 = Input('from_first')
    from_ip2 = Input('from_second')
    from_ip3 = Input('from_third')
    from_ip4 = Input('from_fourth')
    to_ip4 = Input('to_fourth')

    start = Button('Start')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] and
                self.title.text == 'Infrastructure Providers Discovery')


class CloudProvidersDiscoverView(BaseLoggedInPage):
    """
     Discover View from Infrastructure Providers page
    """
    title = Text('//div[@id="main-content"]//h1')

    discover_type = BootstrapSelect('discover_type_selected')

    fields = ConditionalSwitchableView(reference='discover_type')

    @fields.register('Amazon EC2', default=True)
    class Amazon(View):
        username = Input(name='userid')
        password = Input(name='password')
        confirm_password = Input(name='verify')

    @fields.register('Azure')
    class Azure(View):
        client_id = Input(name='client_id')
        client_key = Input(name='client_key')
        tenant_id = Input(name='azure_tenant_id')
        subscription = Input(name='subscription')

    start = Button('Start')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ['Compute', 'Clouds', 'Providers'] and
                self.title.text == 'Cloud Providers Discovery')


class NodesToolBar(View):
    """
     represents nodes toolbar and its controls (exists for Infra OpenStack provider)
    """
    configuration = Dropdown(text='Configuration')
    policy = Dropdown(text='Policy')
    power = Dropdown(text='Power')
    download = Dropdown(text='Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class ProviderNodesView(BaseLoggedInPage):
    """
     represents main Nodes view (exists for Infra OpenStack provider)
    """
    title = Text('//div[@id="main-content"]//h1')
    toolbar = View.nested(NodesToolBar)
    including_entities = View.include(HostEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        title = '{name} (All Managed Hosts)'.format(name=self.context['object'].name)
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] and
                self.title.text == title)


class ProviderVmsTemplatesView(BaseLoggedInPage):
    """
     represents Templates view (exists for Infra providers)
    """
    title = Text('//div[@id="main-content"]//h1')
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @View.nested
    class toolbar(View):  # noqa
        configuration = Dropdown(text='Configuration')
        policy = Dropdown(text='Policy')
        power = Dropdown(text='Power')
        download = Dropdown(text='Download')
        view_selector = View.nested(ItemsToolBarViewSelector)


class ProviderTemplatesView(ProviderVmsTemplatesView):

    @property
    def is_displayed(self):
        title = VersionPicker({
            Version.lowest(): '{name} (All VM Templates)'.format(
                name=getattr(self.context['object'], 'name', None) or getattr(
                    self.context['object'].parent, 'name', None)),
            '5.10': '{name} (All VM Templates and Images)'.format(
                name=getattr(self.context['object'], 'name', None) or getattr(
                    self.context['object'].parent, 'name', None)),
        }).pick(self.extra.appliance.version)
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] and
                self.title.text == title)


class ProviderVmsView(ProviderVmsTemplatesView):

    @property
    def is_displayed(self):
        title = '{name} (All Direct VMs)'.format(name=self.context['object'].name)
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] and
                self.title.text == title)


class ProviderToolBar(View):
    """
     represents provider toolbar and its controls
    """
    configuration = Dropdown(text='Configuration')
    policy = Dropdown(text='Policy')
    authentication = Dropdown(text='Authentication')
    download = Dropdown(text='Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class ProviderSideBar(View):
    """
    represents left side bar. it usually contains navigation, filters, etc
    """
    pass


class ProviderEntitiesView(BaseEntitiesView):
    """
     represents child class of Entities view for Provider entities
    """
    @property
    def entity_class(self):
        return ProviderEntity


class ProvidersView(BaseLoggedInPage):
    """
    represents Main view displaying all providers
    """
    @property
    def is_displayed(self):
        return self.logged_in_as_current_user

    paginator = PaginationPane()
    toolbar = View.nested(ProviderToolBar)
    sidebar = View.nested(ProviderSideBar)
    search = View.nested(Search)
    including_entities = View.include(ProviderEntitiesView, use_parent=True)
    add_button = Button('Add a Provider')

    @View.nested
    class my_filters(Accordion):  # noqa
        ACCORDION_NAME = "My Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()


class ContainerProvidersView(ProvidersView):
    """
     represents Main view displaying all Containers providers
    """
    SUMMARY_TEXT = 'Containers Providers'

    @property
    def table(self):
        return self.entities.elements

    @property
    def paginator(self):
        return self.entities.paginator

    @property
    def is_displayed(self):
        return (super().is_displayed and
                self.navigation.currently_selected == ['Compute', 'Containers', 'Providers'] and
                self.entities.title.text == self.SUMMARY_TEXT)

    @property
    def summary_text(self):
        return self.SUMMARY_TEXT


class InfraProvidersView(ProvidersView):
    """
     represents Main view displaying all Infra providers
    """
    @property
    def is_displayed(self):
        return (super().is_displayed and
                self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] and
                self.entities.title.text == 'Infrastructure Providers')


class CloudProvidersView(ProvidersView):
    """
     represents Main view displaying all Cloud providers
    """
    @property
    def is_displayed(self):
        return (super().is_displayed and
                self.navigation.currently_selected == ['Compute', 'Clouds', 'Providers'] and
                self.entities.title.text == 'Cloud Providers')


class NetworkProvidersView(ProvidersView):
    """
     represents Main view displaying all Network providers
    """
    @property
    def is_displayed(self):
        return (super().is_displayed and
                self.navigation.currently_selected == ['Networks', 'Providers'] and
                self.entities.title.text == 'Network Managers')


class PhysicalProvidersView(ProvidersView):
    """
     represents Main view displaying all Infra providers
    """
    @property
    def is_displayed(self):
        return (super().is_displayed and
                self.navigation.currently_selected == [
                    'Compute', 'Physical Infrastructure', 'Providers'] and
                self.entities.title.text == 'Physical Infrastructure Providers')


class BeforeFillMixin:
    """
     this mixin is used to activate appropriate tab before filling this tab
    """

    def before_fill(self):
        if self.exists and not self.is_active():
            self.select()


class ProviderAddView(BaseLoggedInPage):
    """
     represents Provider Add View
    """
    title = Text('//div[@id="main-content"]//h1')
    name = Input('name')
    prov_type = BootstrapSelect(id='emstype')
    zone = Input('zone')
    add = Button('Add')
    cancel = Button('Cancel')

    @View.nested
    class endpoints(View):  # NOQA
        # this is switchable view that gets replaced with concrete view.
        # it gets changed according to currently chosen provider type
        # look at cfme.common.provider.BaseProvider.create() method
        pass

    @property
    def is_displayed(self):
        return (
            self.title.is_displayed and self.name.is_displayed and
            self.prov_type.is_displayed and self.zone.is_displayed and
            self.add.is_displayed and self.cancel.is_displayed
        )


class InfraProviderAddView(ProviderAddView):
    api_version = BootstrapSelect(id='api_version')  # only for OpenStack
    keystone_v3_domain_id = Input('keystone_v3_domain_id')  # OpenStack only

    @property
    def is_displayed(self):
        return (super().is_displayed and
                self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] and
                self.title.text == 'Add New Infrastructure Provider')


class CloudProviderAddView(ProviderAddView):
    """
     represents Cloud Provider Add View
    """
    # bug in cfme this field has different ids for cloud and infra add views
    prov_type = BootstrapSelect(id='ems_type')
    region = BootstrapSelect(id='provider_region')  # Azure/AWS/GCE
    tenant_id = Input('azure_tenant_id')  # only for Azure
    subscription = Input('subscription')  # only for Azure
    project_id = Input('project')  # only for Azure
    # bug in cfme this field has different ids for cloud and infra add views
    api_version = BootstrapSelect(id='ems_api_version')  # only for OpenStack
    keystone_v3_domain_id = Input('keystone_v3_domain_id')  # OpenStack only
    infra_provider = BootstrapSelect(id='ems_infra_provider_id')  # OpenStack only
    tenant_mapping = Checkbox(name='tenant_mapping_enabled')  # OpenStack only

    @property
    def is_displayed(self):
        return (super().is_displayed and
                self.navigation.currently_selected == ['Compute', 'Clouds', 'Providers'] and
                self.title.text == 'Add New Cloud Provider')


class ContainerProviderSettingView(View):
    """
       Settings view for Container Providers
      """

    @View.nested
    class proxy(WaitTab, BeforeFillMixin):  # NOQA

        TAB_NAME = 'Proxy'
        http_proxy = Input('provider_options_proxy_settings_http_proxy')

    @View.nested
    class advanced(WaitTab, BeforeFillMixin):  # NOQA

        TAB_NAME = 'Advanced'
        adv_http = Input('provider_options_image_inspector_options_http_proxy')
        adv_https = Input('provider_options_image_inspector_options_https_proxy')
        no_proxy = Input('provider_options_image_inspector_options_no_proxy')
        image_repo = Input('provider_options_image_inspector_options_repository')
        image_reg = Input('provider_options_image_inspector_options_registry')
        image_tag = Input('provider_options_image_inspector_options_image_tag')
        cve_loc = Input('provider_options_image_inspector_options_cve_url')


class ContainerProviderAddView(ProviderAddView):
    """
     Additional widgets for Container
    """
    COND_WIDGETS = ['prov_type', 'metrics_type', 'alerts_type', 'virt_type']

    prov_type = BootstrapSelect(id='ems_type')
    metrics_type = BootstrapSelect(id='metrics_selection')
    alerts_type = BootstrapSelect(id='alerts_selection')
    virt_type = BootstrapSelect(id='virtualization_selection')
    included_settings = View.include(ContainerProviderSettingView, use_parent=True)

    def before_fill(self, values):
        for widget_name in self.COND_WIDGETS:
            widget = getattr(self, widget_name)
            if widget.is_displayed:
                widget.fill(values.get(widget_name) or 'Disabled')

    @property
    def is_displayed(self):
        return (super(ProviderAddView, self).is_displayed and
                self.navigation.currently_selected == ['Compute', 'Containers', 'Providers'] and
                self.title.text == 'Add New Containers Provider')


class PhysicalProviderAddView(ProviderAddView):
    """
     represents Provider Add View
    """

    @property
    def is_displayed(self):
        return (super().is_displayed and
                self.navigation.currently_selected == [
                    'Compute', 'Physical Infrastructure', 'Providers'] and
                self.title.text == 'Add New Physical Infrastructure Provider')


class ProviderEditView(ProviderAddView):
    """
     represents Provider Edit View
    """
    prov_type = Text(locator='//label[@name="emstype"]')

    # only in edit view
    vnc_start_port = Input('host_default_vnc_port_start')
    vnc_end_port = Input('host_default_vnc_port_end')
    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        provider_obj = self.context['object']
        expected_title = "Edit {type} Providers '{name}'".format(type=provider_obj.string_name,
                                                                 name=provider_obj.name)

        return (
            self.logged_in_as_current_user and
            self.title.text == expected_title and
            self.navigation.currently_selected == [
                'Compute',
                ('Clouds' if provider_obj.string_name == "Cloud" else provider_obj.string_name),
                'Providers'
            ]
        )


class ContainerProviderEditView(ProviderEditView):
    """
     Additional widgets for builds 5.9 and up
    """

    COND_WIDGETS = ['prov_type', 'metrics_type', 'alerts_type']

    metrics_type = BootstrapSelect(id='metrics_selection')
    alerts_type = BootstrapSelect(id='alerts_selection')
    virt_type = BootstrapSelect(id='virtualization_selection')
    included_settings = View.include(ContainerProviderSettingView, use_parent=True)

    def before_fill(self, values):
        for widget in self.COND_WIDGETS:
            if values.get(widget):
                getattr(self, widget).fill(values.get(widget))


class TemplatesCompareView(CompareView):
    """Compare Templates page."""

    @property
    def is_displayed(self):
        title = "Compare VM Template and Image"
        return (self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers']
                and self.title.text == title)

    def verify_checked_items_compared(self, checkedList, view):
        # The first and last header items do not contain template names, so are not iterated upon.
        for header_with_template in view.comparison_table.headers[1:-1]:
            try:
                # Split and slice are used to remove extra characters in the header item
                checkedList.remove(header_with_template.split(' ')[0])
            except ValueError:
                pytest.fail(f"Entity {header_with_template.split(' ')[0]} is in compare view, "
                            f"but was not checked.")
            except TypeError:
                pytest.fail('No entities found in compare view.')
        if len(checkedList) > 0:
            pytest.fail(f'Some checked items did not appear in the compare view: {checkedList}.')
        return True
