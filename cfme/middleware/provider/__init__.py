from navmazing import NavigateToSibling, NavigateToAttribute

from functools import partial
from random import sample
import os
import re

from cfme.common import Validatable, SummaryMixin
from cfme.common.provider import import_all_modules_of
from cfme.common.provider import BaseProvider
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import (
    Region, Form, AngularSelect, InfoBlock, Input, Quadicon,
    form_buttons, toolbar as tb, paginator, fill, FileInput,
    CFMECheckbox, Select, flash
)
from utils import version
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.db import cfmedb


cfg_btn = partial(tb.select, 'Configuration')
mon_btn = partial(tb.select, 'Monitoring')
pol_btn = partial(tb.select, 'Policy')
pwr_btn = partial(tb.select, 'Power')
download_btn = partial(tb.select, "Download")
download_summary_btn = partial(tb.select, "Download summary in PDF format")
deploy_btn = partial(tb.select, 'Deployments')
operations_btn = partial(tb.select, 'Operations')
auth_btn = partial(tb.select, 'Authentication')
jdbc_btn = partial(tb.select, 'JDBC Drivers')
datasources_btn = partial(tb.select, 'Datasources')

LIST_TABLE_LOCATOR = "//div[@id='list_grid']/table"


details_page = Region(infoblock_type='detail')


def _db_select_query(name=None, type=None):
    """column order: `id`, `name`, `type`"""
    t_ems = cfmedb()['ext_management_systems']
    query = cfmedb().session.query(t_ems.id, t_ems.name, t_ems.type)
    if name:
        query = query.filter(t_ems.name == name)
    if type:
        query = query.filter(t_ems.type == type)
    return query


def _get_providers_page():
    navigate_to(MiddlewareProvider, 'All')


properties_form = Form(
    fields=[
        ('type_select', AngularSelect('emstype')),
        ('name_text', Input('name')),
        ('hostname_text', Input('default_hostname')),
        ('port_text', Input('default_api_port'))
    ])


@BaseProvider.add_base_type
class MiddlewareProvider(BaseProvider):
    in_version = ('5.7', version.LATEST)
    category = "middleware"
    page_name = 'middleware'
    string_name = 'Middleware'
    provider_types = {}
    STATS_TO_MATCH = []
    property_tuples = []
    detail_page_suffix = 'provider_detail'
    edit_page_suffix = 'provider_edit_detail'
    refresh_text = "Refresh items and relationships"
    quad_name = None
    _properties_form = properties_form
    add_provider_button = form_buttons.FormButton("Add")
    save_button = form_buttons.FormButton("Save changes")
    taggable_type = 'ExtManagementSystem'


@navigator.register(MiddlewareProvider, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Middleware', 'Providers')

    def resetter(self):
        # Reset view and selection
        tb.select("Grid View")
        sel.check(paginator.check_all())
        sel.uncheck(paginator.check_all())


@navigator.register(MiddlewareProvider, 'Add')
class Add(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        cfg_btn('Add a New Middleware Provider')


@navigator.register(MiddlewareProvider, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.click(Quadicon(self.obj.name, self.obj.quad_name))


@navigator.register(MiddlewareProvider, 'Edit')
class Edit(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.check(Quadicon(self.obj.name, self.obj.quad_name).checkbox())
        cfg_btn('Edit Selected Middleware Provider')


@navigator.register(MiddlewareProvider, 'EditFromDetails')
class EditFromDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        cfg_btn('Edit this Middleware Provider')


@navigator.register(MiddlewareProvider, 'EditTags')
class EditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.check(Quadicon(self.obj.name, self.obj.quad_name).checkbox())
        pol_btn('Edit Tags')


@navigator.register(MiddlewareProvider, 'EditTagsFromDetails')
class EditTagsFromDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        pol_btn('Edit Tags')


@navigator.register(MiddlewareProvider, 'TimelinesFromDetails')
class TimelinesFromDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        mon_btn('Timelines')


@navigator.register(MiddlewareProvider, 'ProviderServers')
class ProviderServers(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        sel.click(InfoBlock.element('Relationships', 'Middleware Servers'))


@navigator.register(MiddlewareProvider, 'ProviderDatasources')
class ProviderDatasources(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        sel.click(InfoBlock.element('Relationships', 'Middleware Datasources'))


@navigator.register(MiddlewareProvider, 'ProviderDeployments')
class ProviderDeployments(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        sel.click(InfoBlock.element('Relationships', 'Middleware Deployments'))


@navigator.register(MiddlewareProvider, 'ProviderDomains')
class ProviderDomains(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        sel.click(InfoBlock.element('Relationships', 'Middleware Domains'))


@navigator.register(MiddlewareProvider, 'ProviderMessagings')
class ProviderMessagings(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        sel.click(InfoBlock.element('Relationships', 'Middleware Messagings'))


@navigator.register(MiddlewareProvider, 'TopologyFromDetails')
class TopologyFromDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        sel.click(InfoBlock('Overview', 'Topology'))


class MiddlewareBase(Validatable):
    """
    MiddlewareBase class used to define common functions across pages.
    Also used to override existing function when required.
    """

    def download_summary(self):
        self.load_details(refresh=False)
        download_summary_btn()

    def get_detail(self, *ident):
        """ Gets details from the details infoblock
        Args:
            *ident: Table name and Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the summary's value.
        """
        return InfoBlock.text(*ident)


import_form = Form(
    fields=[
        ("file_select", FileInput("upload[file]")),
        ("enable_deployment", CFMECheckbox("enable_deployment_cb")),
        ("runtime_name", Input("runtime_name_input", use_id=True)),
        ("force_deployment", CFMECheckbox("force_deployment_cb")),
        ('deploy_button', form_buttons.FormButton("Deploy", ng_click="addDeployment()")),
        ('cancel_button', form_buttons.FormButton("Cancel"))
    ]
)

jdbc_driver_form = Form(
    fields=[
        ("file_select", FileInput("jdbc_driver[file]")),
        ("jdbc_driver_name", Input("jdbc_driver_name_input")),
        ("jdbc_module_name", Input("jdbc_module_name_input")),
        ("jdbc_driver_class", Input("jdbc_driver_class_input")),
        ("major_version", Input("major_version_input")),
        ("minor_version", Input("minor_version_input")),
        ('deploy_button', form_buttons.FormButton("Deploy", ng_click="addJdbcDriver()")),
        ('cancel_button', form_buttons.FormButton("Cancel"))
    ]
)


datasource_form = Form(
    fields=[
        ("ds_type", Select("//select[@id='chooose_datasource_input']")),
        ("ds_name", Input("ds_name_input")),
        ("jndi_name", Input("jndi_name_input")),
        ("driver_name", Input("jdbc_ds_driver_name_input")),
        ("driver_module_name", Input("jdbc_modoule_name_input")),
        ("driver_class", Input("jdbc_ds_driver_input")),
        ("ds_url", Input("connection_url_input")),
        ("username", Input("user_name_input")),
        ("password", Input("password_input")),
        ("sec_domain", Input("security_domain_input", use_id=True)),
        ('next0_button', form_buttons.FormButton('Next', ng_click="addDatasourceChooseNext()")),
        ('next1_button', form_buttons.FormButton('Next', ng_click="addDatasourceStep1Next()")),
        ('next2_button', form_buttons.FormButton('Next', ng_click="addDatasourceStep2Next()")),
        ('back1_button', form_buttons.FormButton('Back', ng_click="addDatasourceStep1Back()")),
        ('back2_button', form_buttons.FormButton('Back', ng_click="addDatasourceStep2Back()")),
        ('back3_button', form_buttons.FormButton('Back', ng_click="finishAddDatasourceBack()")),
        ('finish_button', form_buttons.FormButton('Finish', ng_click="finishAddDatasource()")),
        ('cancel_button', form_buttons.FormButton('Cancel', ng_click="reset()"))
    ]
)


def get_random_list(items, limit):
    """In tests, when we have big list iterating through each element will take lot of time.
    To avoid this, select random list with limited numbers"""
    if len(items) > limit:
        return sample(items, limit)
    else:
        return items


def parse_properties(props):
    """Parses provided properties in string format into dictionary format.
    It splits string into lines and splits each line into key and value."""
    properties = {}
    for line in props.splitlines():
        pair = line.split(': ')
        if len(pair) == 2:
            properties.update({pair[0]: pair[1].replace('\'', '')})
    return properties


def download(extension):
    extensions_mapping = {'txt': 'Text', 'csv': 'CSV', 'pdf': 'PDF'}
    try:
        download_btn("Download as {}".format(extensions_mapping[extension]))
    except:
        raise ValueError("Unknown extention. check the extentions_mapping")


def get_server_name(path):
    if len(path.resource_id) > 3:
        # this is the domain mode case, take the server value
        return re.sub(r'.*server%3D', '', path.resource_id[2])
    else:
        # for standalone servers
        return re.sub(r'~~$', '', path.resource_id[0])


class Container(SummaryMixin):

    def add_deployment(self, filename, runtime_name=None, enable_deploy=True,
                       overwrite=False, cancel=False):
        """Clicks to "Add Deployment" button, in opened window fills fields by provided parameters,
        and deploys.

        Args:
            filename: Full path to file to import.
            runtime_name: Runtime name of deployment archive.
            enable_deploy: Whether to enable deployment archive or keep disabled.
            cancel: Whether to click Cancel instead of commit.
        """
        self.load_details()
        deploy_btn("Add Deployment")
        fill(
            import_form,
            {"file_select": filename,
             "runtime_name": runtime_name,
             "enable_deployment": enable_deploy,
             "force_deployment": overwrite}
        )
        sel.click(import_form.cancel_button if cancel else import_form.deploy_button)
        flash.assert_success_message('Deployment "{}" has been initiated on this server.'
                    .format(runtime_name if runtime_name else os.path.basename(filename)))

    def add_jdbc_driver(self, filename, driver_name, module_name, driver_class,
                        major_version=None, minor_version=None, cancel=False):
        """Clicks to "Add JDBC Driver" button, in opened window fills fields by provided parameters,
        and deploys.

        Args:
            filename: Full path to JDBC Driver to import.
            driver_name: Name of newly created JDBC Driver.
            module_name: Name on Module to register on server side.
            driver_class: JDBC Driver Class.
            major_version: Major version of JDBC driver, optional.
            minor_version: Minor version of JDBC driver, optional.
            cancel: Whether to click Cancel instead of commit.
        """
        self.load_details(refresh=True)
        jdbc_btn("Add JDBC Driver")
        fill(jdbc_driver_form,
            {
                "file_select": filename,
                "jdbc_driver_name": driver_name,
                "jdbc_module_name": module_name,
                "jdbc_driver_class": driver_class,
                "major_version": major_version,
                "minor_version": minor_version
            })
        sel.click(jdbc_driver_form.cancel_button if cancel else jdbc_driver_form.deploy_button)
        flash.assert_success_message('JDBC Driver "{}" has been installed on this server.'
                    .format(driver_name))

    def add_datasource(self, ds_type, ds_name, jndi_name, driver_name,
               driver_module_name, driver_class, ds_url,
               username, password=None, sec_domain=None, cancel=False):
        """Clicks to "Add Datasource" button,
        in opened window fills fields by provided parameter by clicking 'Next',
        and submits the form by clicking 'Finish'.

        Args:
            ds_type: Type of database.
            ds_name: Name of newly created Datasource.
            jndi_name: JNDI Name of Datasource.
            driver_name: JDBC Driver name in Datasource.
            driver_module_name: Module name of JDBC Driver used in datasource.
            driver_class: JDBC Driver Class.
            ds_url: Database connection URL in jdbc format.
            username: Database username.
            password: Databasae password, optional.
            sec_domain: Security Domain, optional.
            cancel: Whether to click Cancel instead of commit.
        """
        self.load_details(refresh=True)
        datasources_btn("Add Datasource", invokes_alert=True)
        fill(datasource_form,
            {
                "ds_type": ds_type
            })
        sel.click(datasource_form.cancel_button if cancel else datasource_form.next0_button)
        fill(datasource_form,
            {
                "ds_name": ds_name,
                "jndi_name": jndi_name
            })
        sel.click(datasource_form.cancel_button if cancel else datasource_form.next1_button)
        fill(datasource_form,
            {
                "driver_name": driver_name,
                "driver_module_name": driver_module_name,
                "driver_class": driver_class
            })
        sel.click(datasource_form.cancel_button if cancel else datasource_form.next2_button)
        fill(datasource_form,
            {
                "ds_url": ds_url,
                "username": username,
                "password": password,
                "sec_domain": sec_domain
            })
        sel.click(datasource_form.cancel_button if cancel else datasource_form.finish_button)
        flash.assert_no_errors()


class Deployable(SummaryMixin):

    def undeploy(self):
        """
        Clicks on "Undeploy" menu item and verifies message shown
        """
        self.load_details()
        operations_btn("Undeploy", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Undeployment initiated for selected deployment(s)')

    def restart(self):
        """
        Clicks on "Restart" menu item and verifies message shown
        """
        self.load_details()
        operations_btn("Restart", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Restart initiated for selected deployment(s)')

    def disable(self):
        """
        Clicks on "Disable" menu item and verifies message shown
        """
        self.load_details()
        operations_btn("Disable", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Disable initiated for selected deployment(s)')

    def enable(self):
        """
        Clicks on "Enable" menu item and verifies message shown
        """
        self.load_details()
        operations_btn("Enable", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Enable initiated for selected deployment(s)')


import_all_modules_of('cfme.middleware.provider')
