
import os
import re
from random import sample

from navmazing import NavigateToSibling, NavigateToAttribute
from selenium.common.exceptions import NoSuchElementException

from cfme.common import Validatable, SummaryMixin, TagPageView
from cfme.common.provider import BaseProvider
from cfme.common.provider_views import (
    MiddlewareProviderAddView,
    MiddlewareProviderEditView,
    MiddlewareProvidersView,
    MiddlewareProviderDetailsView)
from cfme.exceptions import MiddlewareProviderNotFound
from cfme.middleware.provider.middleware_views import (ProviderMessagingAllView,
    ProviderDeploymentAllView, ProviderDatasourceAllView,
    ProviderServerAllView, MiddlewareProviderTimelinesView,
    ProviderDomainsAllView)
from cfme.utils import version
from cfme.utils.appliance import current_appliance
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.wait import wait_for


def _db_select_query(name=None, type=None):
    """column order: `id`, `name`, `type`"""
    t_ems = current_appliance.db.client['ext_management_systems']
    query = current_appliance.db.client.session.query(t_ems.id, t_ems.name, t_ems.type)
    if name:
        query = query.filter(t_ems.name == name)
    if type:
        query = query.filter(t_ems.type == type)
    return query


def _get_providers_page():
    return navigate_to(MiddlewareProvider, 'All')


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
    taggable_type = 'ExtManagementSystem'
    db_types = ["MiddlewareManager"]


@navigator.register(MiddlewareProvider, 'All')
class All(CFMENavigateStep):
    VIEW = MiddlewareProvidersView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Middleware', 'Providers')

    def resetter(self):
        # Reset view
        self.view.toolbar.view_selector.select('List View')


@navigator.register(MiddlewareProvider, 'Add')
class Add(CFMENavigateStep):
    VIEW = MiddlewareProviderAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Add a New Middleware Provider')


@navigator.register(MiddlewareProvider, 'Details')
class Details(CFMENavigateStep):
    VIEW = MiddlewareProviderDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.view_selector.select('List View')
        try:
            entity = self.prerequisite_view.entities.get_entity(by_name=self.obj.name)
        except NoSuchElementException:
            raise MiddlewareProviderNotFound(
                "Middleware Provider '{}' not found in table".format(self.obj.name))
        entity.click()


@navigator.register(MiddlewareProvider, 'Edit')
class Edit(CFMENavigateStep):
    VIEW = MiddlewareProviderEditView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name).check()
        self.prerequisite_view.toolbar.configuration \
            .item_select('Edit Selected Middleware Providers')


@navigator.register(MiddlewareProvider, 'EditFromDetails')
class EditFromDetails(CFMENavigateStep):
    VIEW = MiddlewareProviderEditView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this Middleware Provider')


@navigator.register(MiddlewareProvider, 'EditTags')
class EditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name).check()
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


@navigator.register(MiddlewareProvider, 'EditTagsFromDetails')
class EditTagsFromDetails(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


@navigator.register(MiddlewareProvider, 'Timelines')
class Timelines(CFMENavigateStep):
    VIEW = MiddlewareProviderTimelinesView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.monitoring.item_select('Timelines')


@navigator.register(MiddlewareProvider, 'ProviderServers')
class ProviderServers(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')
    VIEW = ProviderServerAllView

    def step(self):
        self.prerequisite_view.entities.relationships.click_at('Middleware Servers')


@navigator.register(MiddlewareProvider, 'ProviderDatasources')
class ProviderDatasources(CFMENavigateStep):
    VIEW = ProviderDatasourceAllView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.entities.relationships.click_at('Middleware Datasources')


@navigator.register(MiddlewareProvider, 'ProviderDeployments')
class ProviderDeployments(CFMENavigateStep):
    VIEW = ProviderDeploymentAllView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.entities.relationships.click_at('Middleware Deployments')


@navigator.register(MiddlewareProvider, 'ProviderDomains')
class ProviderDomains(CFMENavigateStep):
    VIEW = ProviderDomainsAllView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.entities.relationships.click_at('Middleware Domains')


@navigator.register(MiddlewareProvider, 'ProviderMessagings')
class ProviderMessagings(CFMENavigateStep):
    VIEW = ProviderMessagingAllView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.entities.relationships.click_at('Middleware Messagings')


@navigator.register(MiddlewareProvider, 'TopologyFromDetails')
class TopologyFromDetails(CFMENavigateStep):
    # TODO Topology should be converted to widgetastic
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.entities.overview.click_at('Topology')


class MiddlewareBase(Validatable):
    """
    MiddlewareBase class used to define common functions across pages.
    Also used to override existing function when required.
    """

    def download_summary(self):
        view = self.load_details(refresh=False)
        view.toolbar.download()

    def get_detail(self, *ident):
        """ Gets details from the details infoblock

        The function first ensures that we are on the detail page for the specific cluster.

        Args:
            ident: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"

        Returns: A string representing the contents of the InfoBlock's value.
        """
        view = self.load_details()
        return getattr(view.contents if hasattr(view, 'contents') else view.entities,
                       ident[0].lower().replace(' ', '_')).get_text_of(ident[1])


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


def download(view, extension):
    extensions_mapping = {'txt': 'Text', 'csv': 'CSV', 'pdf': 'PDF'}
    try:
        view.toolbar.download.item_select("Download as {}".format(extensions_mapping[extension]))
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
        view = navigate_to(self, 'AddDeployment')
        view.form.fill({
            "file_select": filename,
        })
        view.form.fill({
            "runtime_name": runtime_name,
            "enable_deployment": enable_deploy,
            "force_deployment": overwrite
        })
        view.form.cancel_button.click() if cancel else view.form.deploy_button.click()
        view.flash.assert_success_message(self.deployment_message
                    .format(runtime_name if runtime_name else os.path.basename(filename)))

    def add_jdbc_driver(self, filename, driver_name, module_name, driver_class, xa_class=None,
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
        view = navigate_to(self, 'AddJDBCDriver')
        view.form.fill({
            "file_select": filename,
            "jdbc_driver_name": driver_name,
            "jdbc_module_name": module_name,
            "jdbc_driver_class": driver_class,
            "driver_xa_datasource_class": xa_class,
            "major_version": major_version,
            "minor_version": minor_version
        })
        view.form.cancel_button.click() if cancel else view.form.deploy_button.click()
        view.flash.assert_success_message('JDBC Driver "{}" has been installed on this server.'
                    .format(driver_name))

    def add_datasource(self, ds_type, ds_name, jndi_name, ds_url,
               xa_ds=False, driver_name=None,
               existing_driver=None, driver_module_name=None, driver_class=None,
               username=None, password=None, sec_domain=None, cancel=False):
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
        view = navigate_to(self, 'AddDatasource')
        if self.appliance.version >= '5.8':
            view.form.fill({'xa_ds': xa_ds})
        view.form.fill({'ds_type': ds_type})
        view.form.next_button.click()
        view.form.fill({
            "ds_name": ds_name,
            "jndi_name": jndi_name
        })
        view.form.next_button.click()
        if existing_driver and self.appliance.version >= '5.8':
            view.form.tab_existing_driver.select()
            wait_for(lambda: existing_driver in
                     [option.text for option in view.form.existing_driver.all_options],
                 delay=3, num_sec=6,
                 message='JDBC Driver {} must be listed in existing drivers'
                 .format(existing_driver))
            view.form.fill({
                "existing_driver": existing_driver
            })
        else:
            view.form.fill({
                "driver_name": driver_name,
                "driver_module_name": driver_module_name,
                "driver_class": driver_class
            })
        view.form.next_button.click()
        view.form.fill({
            "ds_url": ds_url,
            "username": username,
            "password": password,
            "sec_domain": sec_domain
        })
        view.form.cancel_button.click() if cancel else view.form.finish_button.click()
        view.flash.assert_no_error()

    def is_immutable(self):
        view = self.load_details()
        return not (view.toolbar.power.is_displayed or
                    view.toolbar.deployments.is_displayed or
                    view.toolbar.drivers.is_displayed or
                    view.toolbar.datasources.is_displayed)


class Deployable(SummaryMixin):

    def undeploy(self):
        """
        Clicks on "Undeploy" menu item and verifies message shown
        """
        view = self.load_details()
        view.toolbar.operations.item_select("Undeploy", handle_alert=True)
        view.flash.assert_success_message('Undeployment initiated for selected deployment(s)')

    def restart(self):
        """
        Clicks on "Restart" menu item and verifies message shown
        """
        view = self.load_details()
        view.toolbar.operations.item_select("Restart", handle_alert=True)
        view.flash.assert_success_message('Restart initiated for selected deployment(s)')

    def disable(self):
        """
        Clicks on "Disable" menu item and verifies message shown
        """
        view = self.load_details()
        view.toolbar.operations.item_select("Disable", handle_alert=True)
        view.flash.assert_success_message('Disable initiated for selected deployment(s)')

    def enable(self):
        """
        Clicks on "Enable" menu item and verifies message shown
        """
        view = self.load_details()
        view.toolbar.operations.item_select("Enable", handle_alert=True)
        view.flash.assert_success_message('Enable initiated for selected deployment(s)')


class Reportable(SummaryMixin):
    def generate_jdr(self):
        view = self.load_details()
        view.toolbar.generate_jdr.click()
        view.flash.assert_success_message('Generate JDR report initiated for selected server(s)')
