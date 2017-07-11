# -*- coding: utf-8 -*-
from widgetastic.utils import VersionPick, Version
from widgetastic.widget import View, Text, ConditionalSwitchableView
from widgetastic_patternfly import Dropdown, BootstrapSelect, FlashMessages

from cfme.base.login import BaseLoggedInPage
from widgetastic_manageiq import (BreadCrumb,
                                  SummaryTable,
                                  Button,
                                  TimelinesView,
                                  DetailsToolBarViewSelector,
                                  ItemsToolBarViewSelector,
                                  Checkbox,
                                  Input,
                                  Table,
                                  FileInput,
                                  BaseEntitiesView,
                                  DynaTree,
                                  BootstrapTreeview,
                                  ProviderEntity)


class ProviderDetailsToolBar(View):
    """
    represents provider toolbar and its controls
    """
    monitoring = Dropdown(text='Monitoring')
    configuration = Dropdown(text='Configuration')
    reload = Button(title='Reload Current Display')
    policy = Dropdown(text='Policy')
    authentication = Dropdown(text='Authentication')

    view_selector = View.nested(DetailsToolBarViewSelector)


class ProviderDetailsSummaryView(View):
    """
    represents Details page when it is switched to Summary aka Tables view
    """
    properties = SummaryTable(title="Properties")
    status = SummaryTable(title="Status")
    relationships = SummaryTable(title="Relationships")
    overview = SummaryTable(title="Overview")
    smart_management = SummaryTable(title="Smart Management")


class ProviderDetailsDashboardView(View):
    """
     represents Details page when it is switched to Dashboard aka Widgets view
    """
    # todo: need to develop this page
    pass


class ProviderDetailsView(BaseLoggedInPage):
    """
     main Details page
    """
    title = Text('//div[@id="main-content"]//h1')
    breadcrumb = BreadCrumb(locator='//ol[@class="breadcrumb"]')
    flash = FlashMessages('.//div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
                          'contains(@class, "flash_text_div")]')
    toolbar = View.nested(ProviderDetailsToolBar)

    @View.nested
    class contents(View):  # NOQA
        # this is switchable view that gets replaced with concrete view.
        # it gets changed according to currently chosen view type  every time
        # when it is accessed
        # it is provided provided by __getattribute__
        pass

    def __getattribute__(self, item):
        # todo: to replace this code with switchable views asap
        if item == 'contents':
            if self.context['object'].appliance.version >= '5.7':
                view_type = self.toolbar.view_selector.selected
                # cloud provider details view doesn't have such switch, BZ(1460772)
                if view_type == 'Summary View':
                    return ProviderDetailsSummaryView(parent=self)

                elif view_type == 'Dashboard View':
                    return ProviderDetailsDashboardView(parent=self)

                else:
                    raise Exception('The content view type "{v}" for provider "{p}" doesnt '
                                    'exist'.format(v=view_type, p=self.context['object'].name))
            else:
                return ProviderDetailsSummaryView(parent=self)  # 5.6 has only only Summary view

        else:
            return super(ProviderDetailsView, self).__getattribute__(item)

    @property
    def is_displayed(self):
        if (not self.toolbar.view_selector.is_displayed or
                self.toolbar.view_selector.selected == 'Summary View'):
            subtitle = 'Summary'
        else:
            subtitle = 'Dashboard'

        title = '{name} ({subtitle})'.format(name=self.context['object'].name,
                                             subtitle=subtitle)
        return (self.logged_in_as_current_user and
                self.breadcrumb.is_displayed and
                self.breadcrumb.active_location == title)


class InfraProviderDetailsView(ProviderDetailsView):
    """
     Infra Details page
    """
    @property
    def is_displayed(self):
        return (super(InfraProviderDetailsView, self).is_displayed and
                self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'])


class CloudProviderDetailsView(ProviderDetailsView):
    """
     Cloud Details page
    """
    @property
    def is_displayed(self):
        return (super(CloudProviderDetailsView, self).is_displayed and
                self.navigation.currently_selected == ['Compute', 'Clouds', 'Providers'])


class ProviderTimelinesView(TimelinesView, BaseLoggedInPage):
    """
     represents Timelines page
    """
    @property
    def is_displayed(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] and
                TimelinesView.is_displayed)


class InfraProvidersDiscoverView(BaseLoggedInPage):
    """
     Discover View from Infrastructure Providers page
    """
    title = Text('//div[@id="main-content"]//h1')

    vmware = Checkbox('discover_type_virtualcenter')
    scvmm = Checkbox('discover_type_scvmm')
    rhevm = Checkbox('discover_type_rhevm')

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


class ProvidersManagePoliciesView(BaseLoggedInPage):
    """
     Provider's Manage Policies view
    """
    policies = VersionPick({Version.lowest(): DynaTree('protect_treebox'),
                            '5.7': BootstrapTreeview('protectbox')})
    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return False


class ProvidersEditTagsView(BaseLoggedInPage):
    """
     Provider's Edit Tags view
    """
    tag_category = BootstrapSelect('tag_cat')
    tag = BootstrapSelect('tag_add')
    chosen_tags = Table(locator='//div[@id="assignments_div"]/table')

    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return False


class NodesToolBar(View):
    """
     represents nodes toolbar and its controls (exists for Infra OpenStack provider)
    """
    configuration = Dropdown(text='Configuration')
    policy = Dropdown(text='Policy')
    power = Dropdown(text='Power')
    download = Dropdown(text='Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class ProviderRegisterNodesView(View):
    """
     represents Register Nodes view (exists for Infra OpenStack provider)
    """
    file = FileInput(locator='//input[@id="nodes_json_file"]')
    register = Button('Register')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return False


class ProviderNodesView(BaseLoggedInPage):
    """
     represents main Nodes view (exists for Infra OpenStack provider)
    """
    title = Text('//div[@id="main-content"]//h1')
    toolbar = View.nested(NodesToolBar)
    entities = View.nested(View)  # left it for future

    @property
    def is_displayed(self):
        title = '{name} (All Managed Hosts)'.format(name=self.context['object'].name)
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

    toolbar = View.nested(ProviderToolBar)
    sidebar = View.nested(ProviderSideBar)
    including_entities = View.include(ProviderEntitiesView, use_parent=True)


class InfraProvidersView(ProvidersView):
    """
     represents Main view displaying all Infra providers
    """
    @property
    def is_displayed(self):
        return (super(InfraProvidersView, self).is_displayed and
                self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] and
                self.entities.title.text == 'Infrastructure Providers')


class CloudProvidersView(ProvidersView):
    """
     represents Main view displaying all Cloud providers
    """
    @property
    def is_displayed(self):
        return (super(CloudProvidersView, self).is_displayed and
                self.navigation.currently_selected == ['Compute', 'Clouds', 'Providers'] and
                self.entities.title.text == 'Cloud Providers')


class BeforeFillMixin(object):
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
    keystone_v3_domain_id = Input('keystone_v3_domain_id')  # OpenStack only
    zone = Input('zone')
    flash = FlashMessages('.//div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
                          'contains(@class, "flash_text_div")]')

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
        return self.logged_in_as_current_user


class InfraProviderAddView(ProviderAddView):
    api_version = BootstrapSelect(id='api_version')  # only for OpenStack

    @property
    def is_displayed(self):
        return (super(InfraProviderAddView, self).is_displayed and
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
    infra_provider = BootstrapSelect(id='ems_infra_provider_id')  # OpenStack only
    tenant_mapping = Checkbox(name='tenant_mapping_enabled')  # OpenStack only

    @property
    def is_displayed(self):
        return (super(CloudProviderAddView, self).is_displayed and
                self.navigation.currently_selected == ['Compute', 'Clouds', 'Providers'] and
                self.title.text == 'Add New Cloud Provider')


class ProviderEditView(ProviderAddView):
    """
     represents Provider Edit View
    """
    prov_type = Text(locator='//label[@name="emstype"]')

    # only in edit view
    vnc_start_port = Input('host_default_vnc_port_start')
    vnc_end_port = Input('host_default_vnc_port_end')
    flash = FlashMessages('.//div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
                          'contains(@class, "flash_text_div")]')

    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return self.logged_in_as_current_user


class InfraProviderEditView(ProviderEditView):
    """
     represents Infra Provider Edit View
    """
    @property
    def is_displayed(self):
        return (super(InfraProviderEditView, self).is_displayed and
                self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] and
                self.title.text == 'Edit Infrastructure Provider')


class CloudProviderEditView(ProviderEditView):
    """
     represents Cloud Provider Edit View
    """
    @property
    def is_displayed(self):
        return (super(CloudProviderEditView, self).is_displayed and
                self.navigation.currently_selected == ['Compute', 'Clouds', 'Providers'] and
                self.title.text == 'Edit Cloud Provider')
