# -*- coding: utf-8 -*-

from widgetastic.widget import View, Text, TextInput, Select
from widgetastic_patternfly import (Dropdown,
                                    FlashMessages,
                                    BootstrapSwitch,
                                    BootstrapNav,
                                    Tab)

from cfme.base.login import BaseLoggedInPage
from widgetastic_manageiq import (Accordion,
                                  BreadCrumb,
                                  SummaryTable,
                                  Button,
                                  TimelinesView,
                                  ItemsToolBarViewSelector,
                                  Table,
                                  BaseEntitiesView,
                                  FileInput,
                                  Search)


LIST_TABLE_LOCATOR = '//div[@id="list_grid" or contains(@class, "miq-data-table")]//table'
TITLE_LOCATOR = '//div[@id="main-content"]//h1'
FLASH_MESSAGE_LOCATOR = './/div[@id="flash_msg_div"]'\
                        '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]'
TITLE_LOCATOR = '//div[@id="main-content"]//h1'


class ServerToolbar(View):
    """The toolbar on the main page"""
    policy = Dropdown('Policy')
    download = Dropdown('Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class ServerDetailsToolbar(View):
    """The toolbar on the details page"""
    monitoring = Dropdown('Monitoring')
    policy = Dropdown('Policy')
    power = Dropdown('Power')
    deployments = Dropdown('Deployments')
    drivers = Dropdown('JDBC Drivers')
    datasources = Dropdown('Datasources')
    download = Button(title='Download summary in PDF format')
    generate_jdr = Button(title='Enqueue generation of new JDR report')


class JDRToolbar(View):
    """The toolbar on the JDR Reports list"""
    download_list = Dropdown('Download list of JDR')
    delete = Button('Delete')
    view_selector = View.nested(ItemsToolBarViewSelector)


class JDREntitiesView(View):
    """Entities on the JDR Reports list"""
    title = Text('//div[@id="mw_dr_header"]//h3')
    table = Table('//div[@id="mw_dr_section"]//table')
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages(FLASH_MESSAGE_LOCATOR)


class JDRAllView(View):
    """The "all" view -- a list of JDR Reports"""
    toolbar = View.nested(JDRToolbar)
    including_entities = View.include(JDREntitiesView, use_parent=True)


class ServerDetailsAccordion(View):
    """The accordian on the details page"""
    @View.nested
    class server(Accordion):           # noqa
        pass

    @View.nested
    class properties(Accordion):  # noqa
        nav = BootstrapNav('//div[@id="middleware_server_prop"]//ul')

    @View.nested
    class relationships(Accordion):  # noqa
        nav = BootstrapNav('//div[@id="middleware_server_rel"]//ul')


class ServerEntitiesView(BaseEntitiesView):
    """Entities on the main list page"""
    title = Text(TITLE_LOCATOR)
    table = Table(LIST_TABLE_LOCATOR)
    search = View.nested(Search)
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages(FLASH_MESSAGE_LOCATOR)


class ServerDetailsEntities(View):
    """Entities on the details page"""
    breadcrumb = BreadCrumb()
    title = Text(TITLE_LOCATOR)
    properties = SummaryTable(title='Properties')
    relationships = SummaryTable(title='Relationships')
    smart_management = SummaryTable(title='Smart Management')
    flash = FlashMessages(FLASH_MESSAGE_LOCATOR)


class PowerOperationForm(View):
    """Entities on the Power Operations widget"""
    title = Text('//div[@id="op_params_div"]//h4')
    timeout = TextInput("timeout")
    suspend_button = Button(title="Suspend")
    stop_button = Button(title="Stop")
    shutdown_button = Button(title="Shutdown")
    cancel_button = Button(title="Cancel")


class ServerView(BaseLoggedInPage):
    """Base view for header and nav checking, navigatable views should inherit this"""
    @property
    def in_server(self):
        nav_chain = ['Middleware', 'Servers']
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == nav_chain)


class ServerAllView(ServerView):
    """The "all" view -- a list of servers"""
    @property
    def is_displayed(self):
        return (
            self.in_server and
            self.entities.title.text == 'Middleware Servers')

    toolbar = View.nested(ServerToolbar)
    including_entities = View.include(ServerEntitiesView, use_parent=True)


class ProviderServerAllView(ServerView):
    """The "all" view -- a list of provider's servers"""
    @property
    def is_displayed(self):
        expected_title = '{} (All Middleware Servers)'.format(self.context['object'].name)
        return (
            self.in_server and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(ServerToolbar)
    including_entities = View.include(ServerEntitiesView, use_parent=True)


class ServerGroupServerAllView(ServerView):
    """The "all" view -- a list of server group servers"""
    @property
    def is_displayed(self):
        nav_chain = ['Middleware', 'Domains']
        expected_title = '{name} (All Middleware Servers)'.format(name=self.context['object'].name)
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == nav_chain and
            self.title.text == expected_title)

    toolbar = View.nested(ServerToolbar)
    including_entities = View.include(ServerEntitiesView, use_parent=True)


class ServerDetailsView(ServerView):
    """The details page of a datasource"""
    @property
    def is_displayed(self):
        """Is this page being displayed?"""
        expected_title = '{} (Summary)'.format(self.context['object'].name)
        return (
            self.in_server and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(ServerDetailsToolbar)
    sidebar = View.nested(ServerDetailsAccordion)
    entities = View.nested(ServerDetailsEntities)
    power_operation_form = View.nested(PowerOperationForm)
    flash = FlashMessages(FLASH_MESSAGE_LOCATOR)
    jdr_reports = View.nested(JDRAllView)


class DatasourceAllToolbar(View):
    """The toolbar on the main page"""
    back = Button('Show {} Summary')
    policy = Dropdown('Policy')
    operations = Dropdown('Operations')
    download = Dropdown('Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class DatasourceDetailsToolbar(View):
    """The toolbar on the details page"""
    monitoring = Dropdown('Monitoring')
    policy = Dropdown('Policy')
    download = Button(title='Download summary in PDF format')


class DatasourceDetailsAccordion(View):
    """The accordian on the details page"""
    @View.nested
    class datasource(Accordion):           # noqa
        pass

    @View.nested
    class properties(Accordion):  # noqa
        nav = BootstrapNav('//div[@id="middleware_datasource_prop"]//ul')

    @View.nested
    class relationships(Accordion):  # noqa
        nav = BootstrapNav('//div[@id="middleware_datasource_rel"]//ul')


class DatasourceEntitiesView(BaseEntitiesView):
    """Entities on the main list page"""
    title = Text(TITLE_LOCATOR)
    table = Table(LIST_TABLE_LOCATOR)
    search = View.nested(Search)
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages(FLASH_MESSAGE_LOCATOR)


class DatasourceDetailsEntities(View):
    """Entities on the details page"""
    breadcrumb = BreadCrumb()
    title = Text(TITLE_LOCATOR)
    properties = SummaryTable(title='Properties')
    relationships = SummaryTable(title='Relationships')
    smart_management = SummaryTable(title='Smart Management')
    flash = FlashMessages(FLASH_MESSAGE_LOCATOR)


class DatasourceView(BaseLoggedInPage):
    """Base view for header and nav checking, navigatable views should inherit this"""
    @property
    def in_datasource(self):
        nav_chain = ['Middleware', 'Datasources']
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == nav_chain)


class DatasourceAllView(DatasourceView):
    """The "all" view -- a list of datasources"""
    @property
    def is_displayed(self):
        return (
            self.in_datasource and
            self.entities.title.text == 'Middleware Datasources')

    toolbar = View.nested(DatasourceAllToolbar)
    including_entities = View.include(DatasourceEntitiesView, use_parent=True)


class DatasourceDetailsView(DatasourceView):
    """The details page of a datasource"""
    @property
    def is_displayed(self):
        """Is this page being displayed?"""
        expected_title = '{} (Summary)'.format(self.context['object'].name)
        return (
            self.in_datasource and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(DatasourceDetailsToolbar)
    sidebar = View.nested(DatasourceDetailsAccordion)
    entities = View.nested(DatasourceDetailsEntities)
    flash = FlashMessages(FLASH_MESSAGE_LOCATOR)


class ServerDatasourceAllView(DatasourceView):
    """The "all" view -- a list of server's datasources"""
    @property
    def is_displayed(self):
        expected_title = '{} (All Middleware Datasources)'.format(self.context['object'].name)
        return (
            self.in_datasource and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(DatasourceAllToolbar)
    including_entities = View.include(DatasourceEntitiesView, use_parent=True)


class ProviderDatasourceAllView(DatasourceView):
    """The "all" view -- a list of provider's datasources"""
    @property
    def is_displayed(self):
        expected_title = '{} (All Middleware Datasources)'.format(self.context['object'].name)
        return (
            self.in_datasource and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(DatasourceAllToolbar)
    including_entities = View.include(DatasourceEntitiesView, use_parent=True)


class AddDatasourceForm(View):
    """Entities on the Add Datasource widget"""
    title = Text('//div[@id="ds_add_div"]//h4')
    ds_type = Select("//select[@id='chooose_datasource_input']")
    xa_ds = BootstrapSwitch(id="xa_ds_cb")
    ds_name = TextInput("ds_name_input")
    jndi_name = TextInput("jndi_name_input")
    driver_name = TextInput("jdbc_ds_driver_name_input")
    driver_module_name = TextInput("jdbc_modoule_name_input")
    driver_class = TextInput("jdbc_ds_driver_input")
    existing_driver = Select("//select[@id='existing_jdbc_driver_input']")
    ds_url = TextInput("connection_url_input")
    username = TextInput("user_name_input")
    password = TextInput("password_input")
    sec_domain = TextInput(id="security_domain_input")
    next_button = Button(title='Next')
    back_button = Button(title='Back')
    finish_button = Button(title='Finish')
    cancel_button = Button(title='Cancel')

    @View.nested
    class tab_specify_driver(Tab):  # noqa
        TAB_NAME = 'Specify Driver'

    @View.nested
    class tab_existing_driver(Tab):  # noqa
        TAB_NAME = 'Existing Driver'


class AddDatasourceView(DatasourceView):
    """The "Add" view -- new datasources"""
    @property
    def is_displayed(self):
        """ This view is opened as a widget box after clicking on toolbar operation """
        return False

    form = View.nested(AddDatasourceForm)
    flash = FlashMessages(FLASH_MESSAGE_LOCATOR)


class AddJDBCDriverForm(View):
    """Entities on the Add JDBC Driver widget"""
    title = Text('//div[@id="jdbc_add_div"]//h4')
    file_select = FileInput("jdbc_driver[file]")
    jdbc_driver_name = TextInput("jdbc_driver_name_input")
    jdbc_module_name = TextInput("jdbc_module_name_input")
    jdbc_driver_class = TextInput("jdbc_driver_class_input")
    driver_xa_datasource_class = TextInput("driver_xa_datasource_class_name_input")
    major_version = TextInput("major_version_input")
    minor_version = TextInput("minor_version_input")
    deploy_button = Button(title="Deploy")
    cancel_button = Button(title="Cancel")


class AddJDBCDriverView(View):
    """The "Add" view -- new JDBC Drivers"""
    @property
    def is_displayed(self):
        """ This view is opened as a widget box after clicking on toolbar operation """
        return False

    form = View.nested(AddJDBCDriverForm)
    flash = FlashMessages(FLASH_MESSAGE_LOCATOR)


class DeploymentAllToolbar(View):
    """The toolbar on the main page"""
    back = Button('Show {} Summary')
    policy = Dropdown('Policy')
    operations = Dropdown('Operations')
    download = Dropdown('Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class DeploymentDetailsToolbar(View):
    """The toolbar on the details page"""
    policy = Dropdown('Policy')
    operations = Dropdown('Operations')
    download = Button(title='Download summary in PDF format')


class DeploymentDetailsAccordion(View):
    """The accordian on the details page"""
    @View.nested
    class deployment(Accordion):           # noqa
        pass

    @View.nested
    class properties(Accordion):  # noqa
        nav = BootstrapNav('//div[@id="middleware_deployment_prop"]//ul')

    @View.nested
    class relationships(Accordion):  # noqa
        nav = BootstrapNav('//div[@id="middleware_deployment_rel"]//ul')


class DeploymentEntitiesView(BaseEntitiesView):
    """Entities on the main list page"""
    title = Text(TITLE_LOCATOR)
    table = Table(LIST_TABLE_LOCATOR)
    search = View.nested(Search)
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages(FLASH_MESSAGE_LOCATOR)


class DeploymentDetailsEntities(View):
    """Entities on the details page"""
    breadcrumb = BreadCrumb()
    title = Text(TITLE_LOCATOR)
    properties = SummaryTable(title='Properties')
    relationships = SummaryTable(title='Relationships')
    smart_management = SummaryTable(title='Smart Management')
    flash = FlashMessages(FLASH_MESSAGE_LOCATOR)


class DeploymentView(BaseLoggedInPage):
    """Base view for header and nav checking, navigatable views should inherit this"""
    @property
    def in_deployment(self):
        nav_chain = ['Middleware', 'Deployments']
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == nav_chain)


class DeploymentAllView(DeploymentView):
    """The "all" view -- a list of deployments"""
    @property
    def is_displayed(self):
        return (
            self.in_deployment and
            self.entities.title.text == 'Middleware Deployments')

    toolbar = View.nested(DatasourceAllToolbar)
    including_entities = View.include(DeploymentEntitiesView, use_parent=True)


class DeploymentDetailsView(DeploymentView):
    """The details page of a deployment"""
    @property
    def is_displayed(self):
        """Is this page being displayed?"""
        expected_title = '{} (Summary)'.format(self.context['object'].name)
        return (
            self.in_deployment and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(DeploymentDetailsToolbar)
    sidebar = View.nested(DeploymentDetailsAccordion)
    entities = View.nested(DeploymentDetailsEntities)
    flash = FlashMessages(FLASH_MESSAGE_LOCATOR)


class ServerDeploymentAllView(DeploymentView):
    """The "all" view -- a list of server's deployments"""
    @property
    def is_displayed(self):
        expected_title = '{} (All Middleware Deployments)'.format(self.context['object'].name)
        return (
            self.in_deployment and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(DeploymentAllToolbar)
    including_entities = View.include(DeploymentEntitiesView, use_parent=True)


class ProviderDeploymentAllView(DeploymentView):
    """The "all" view -- a list of provider's deployments"""
    @property
    def is_displayed(self):
        expected_title = '{} (All Middleware Deployments)'.format(self.context['object'].name)
        return (
            self.in_deployment and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(DeploymentAllToolbar)
    including_entities = View.include(DeploymentEntitiesView, use_parent=True)


class AddDeploymentForm(View):
    """Entities on the Add Deployment widget"""
    title = Text('//div[@id="ds_add_div"]//h4')
    file_select = FileInput("upload[file]")
    enable_deployment = BootstrapSwitch(id="enable_deployment_cb")
    runtime_name = TextInput(id="runtime_name_input")
    force_deployment = BootstrapSwitch(id="force_deployment_cb")
    deploy_button = Button(title="Deploy")
    cancel_button = Button(title="Cancel")


class AddDeploymentView(DeploymentView):
    """The "Add" view -- new deployments"""
    @property
    def is_displayed(self):
        """ This view is opened as a widget box after clicking on toolbar operation """
        return False

    form = View.nested(AddDeploymentForm)
    flash = FlashMessages(FLASH_MESSAGE_LOCATOR)


class DomainToolbar(View):
    """The toolbar on the main page"""
    policy = Dropdown('Policy')
    download = Dropdown('Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class DomainDetailsToolbar(View):
    """The toolbar on the details page"""
    policy = Dropdown('Policy')
    power = Dropdown('Power')
    download = Button(title='Download summary in PDF format')


class DomainDetailsAccordion(View):
    """The accordian on the details page"""
    @View.nested
    class domain(Accordion):           # noqa
        pass

    @View.nested
    class properties(Accordion):  # noqa
        nav = BootstrapNav('//div[@id="middleware_domain_prop"]//ul')

    @View.nested
    class relationships(Accordion):  # noqa
        nav = BootstrapNav('//div[@id="middleware_domain_rel"]//ul')


class DomainEntitiesView(BaseEntitiesView):
    """Entities on the main list page"""
    title = Text(TITLE_LOCATOR)
    table = Table(LIST_TABLE_LOCATOR)
    search = View.nested(Search)
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages(FLASH_MESSAGE_LOCATOR)


class DomainDetailsEntities(View):
    """Entities on the details page"""
    breadcrumb = BreadCrumb()
    title = Text(TITLE_LOCATOR)
    properties = SummaryTable(title='Properties')
    relationships = SummaryTable(title='Relationships')
    smart_management = SummaryTable(title='Smart Management')
    flash = FlashMessages(FLASH_MESSAGE_LOCATOR)


class DomainView(BaseLoggedInPage):
    """Base view for header and nav checking, navigatable views should inherit this"""
    @property
    def in_domain(self):
        nav_chain = ['Middleware', 'Domains']
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == nav_chain)


class DomainAllView(DomainView):
    """The "all" view -- a list of domains"""
    @property
    def is_displayed(self):
        return (
            self.in_domain and
            self.entities.title.text == 'Middleware Domains')

    toolbar = View.nested(DomainToolbar)
    including_entities = View.include(DomainEntitiesView, use_parent=True)


class ProviderDomainsAllView(DomainView):
    """The "all" view -- a list of provider's domains"""
    @property
    def is_displayed(self):
        expected_title = '{} (All Middleware Domains)'.format(self.context['object'].name)
        return (
            self.in_domain and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(DomainToolbar)
    including_entities = View.include(DomainEntitiesView, use_parent=True)


class DomainDetailsView(DomainView):
    """The details page of a domain"""
    @property
    def is_displayed(self):
        """Is this page being displayed?"""
        expected_title = '{} (Summary)'.format(self.context['object'].name)
        return (
            self.in_domain and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(DomainDetailsToolbar)
    sidebar = View.nested(DomainDetailsAccordion)
    entities = View.nested(DomainDetailsEntities)


class ProviderDomainAllView(DomainView):
    """The "all" view -- a list of provider's domains"""
    @property
    def is_displayed(self):
        expected_title = '{} (All Middleware Domains)'.format(self.context['object'].name)
        return (
            self.in_domain and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(DomainToolbar)
    including_entities = View.include(DomainEntitiesView, use_parent=True)


class MessagingAllToolbar(View):
    """The toolbar on the main page"""
    back = Button('Show {} Summary')
    policy = Dropdown('Policy')
    download = Dropdown('Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class MessagingDetailsToolbar(View):
    """The toolbar on the details page"""
    monitoring = Dropdown('Monitoring')
    policy = Dropdown('Policy')
    download = Button(title='Download summary in PDF format')


class MessagingDetailsAccordion(View):
    """The accordian on the details page"""
    @View.nested
    class messaging(Accordion):           # noqa
        pass

    @View.nested
    class properties(Accordion):  # noqa
        nav = BootstrapNav('//div[@id="middleware_messaging_prop"]//ul')

    @View.nested
    class relationships(Accordion):  # noqa
        nav = BootstrapNav('//div[@id="middleware_messaging_rel"]//ul')


class MessagingEntitiesView(BaseEntitiesView):
    """Entities on the main list page"""
    title = Text(TITLE_LOCATOR)
    table = Table(LIST_TABLE_LOCATOR)
    search = View.nested(Search)
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages(FLASH_MESSAGE_LOCATOR)


class MessagingDetailsEntities(View):
    """Entities on the details page"""
    breadcrumb = BreadCrumb()
    title = Text(TITLE_LOCATOR)
    properties = SummaryTable(title='Properties')
    relationships = SummaryTable(title='Relationships')
    smart_management = SummaryTable(title='Smart Management')
    flash = FlashMessages(FLASH_MESSAGE_LOCATOR)


class MessagingView(BaseLoggedInPage):
    """Base view for header and nav checking, navigatable views should inherit this"""
    @property
    def in_messaging(self):
        nav_chain = ['Middleware', 'Messagings']
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == nav_chain)


class MessagingAllView(MessagingView):
    """The "all" view -- a list of deployments"""
    @property
    def is_displayed(self):
        return (
            self.in_messaging and
            self.entities.title.text == 'Middleware Messagings')

    toolbar = View.nested(MessagingAllToolbar)
    including_entities = View.include(MessagingEntitiesView, use_parent=True)


class MessagingDetailsView(MessagingView):
    """The details page of a deployment"""
    @property
    def is_displayed(self):
        """Is this page being displayed?"""
        expected_title = '{} (Summary)'.format(self.context['object'].name)
        return (
            self.in_messaging and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(MessagingDetailsToolbar)
    sidebar = View.nested(MessagingDetailsAccordion)
    entities = View.nested(MessagingDetailsEntities)


class ServerMessagingAllView(MessagingView):
    """The "all" view -- a list of server's messagings"""
    @property
    def is_displayed(self):
        expected_title = '{} (All Middleware Messagings)'.format(self.context['object'].name)
        return (
            self.in_messaging and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(MessagingAllToolbar)
    including_entities = View.include(MessagingEntitiesView, use_parent=True)


class ProviderMessagingAllView(MessagingView):
    """The "all" view -- a list of provider's messagings"""
    @property
    def is_displayed(self):
        expected_title = '{} (All Middleware Messagings)'.format(self.context['object'].name)
        return (
            self.in_messaging and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(MessagingAllToolbar)
    including_entities = View.include(MessagingEntitiesView, use_parent=True)


class ServerGroupToolbar(View):
    """The toolbar on the main page"""
    download = Dropdown('Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class ServerGroupDetailsToolbar(View):
    """The toolbar on the details page"""
    policy = Dropdown('Policy')
    power = Dropdown('Power')
    deployments = Dropdown('Deployments')
    download = Button(title='Download summary in PDF format')


class ServerGroupDetailsAccordion(View):
    """The accordian on the details page"""
    @View.nested
    class server_group(Accordion):           # noqa
        pass

    @View.nested
    class properties(Accordion):  # noqa
        nav = BootstrapNav('//div[@id="middleware_server_prop"]//ul')

    @View.nested
    class relationships(Accordion):  # noqa
        nav = BootstrapNav('//div[@id="middleware_server_rel"]//ul')


class ServerGroupEntitiesView(BaseEntitiesView):
    """Entities on the main list page"""
    title = Text(TITLE_LOCATOR)
    table = Table(LIST_TABLE_LOCATOR)
    search = View.nested(Search)
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages(FLASH_MESSAGE_LOCATOR)


class ServerGroupDetailsEntities(View):
    """Entities on the details page"""
    breadcrumb = BreadCrumb()
    title = Text(TITLE_LOCATOR)
    properties = SummaryTable(title='Properties')
    relationships = SummaryTable(title='Relationships')
    smart_management = SummaryTable(title='Smart Management')
    flash = FlashMessages(FLASH_MESSAGE_LOCATOR)


class ServerGroupView(BaseLoggedInPage):
    """Base view for header and nav checking, navigatable views should inherit this"""


class ServerGroupDetailsView(ServerGroupView):
    """The details page of a server group"""
    @property
    def is_displayed(self):
        """Is this page being displayed?"""
        expected_title = '{} (Summary)'.format(self.context['object'].name)
        return (
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(ServerGroupDetailsToolbar)
    sidebar = View.nested(ServerGroupDetailsAccordion)
    entities = View.nested(ServerGroupDetailsEntities)
    power_operation_form = View.nested(PowerOperationForm)
    flash = FlashMessages(FLASH_MESSAGE_LOCATOR)


class DomainServerGroupAllView(DomainView):
    """The "all" view -- a list of domain's server groups"""
    @property
    def is_displayed(self):
        expected_title = '{} (All Middleware Server Groups)' \
            .format(self.context['object'].domain.name)
        return (
            self.in_server_group and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(ServerGroupToolbar)
    including_entities = View.include(ServerGroupEntitiesView, use_parent=True)


class MiddlewareProviderTimelinesView(TimelinesView, BaseLoggedInPage):
    @property
    def is_displayed(self):
        return False
        #     (
        # self.logged_in_as_current_user and
        # self.navigation.currently_selected == ['Middleware', 'Providers'] and
        # # TODO unique identifier for middleware timelines
        # self.is_timelines)
