import re
import random
from functools import partial
from random import sample
from traceback import format_exc


from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic_patternfly import (SelectorDropdown, Dropdown, BootstrapSelect,
                                    Input, Button, Tab)
from widgetastic.widget import Text, View, TextInput
from wrapanapi.utils import eval_strings
from widgetastic.xpath import quote


from cfme.base.login import BaseLoggedInPage
from cfme.common.provider import BaseProvider, DefaultEndpoint, DefaultEndpointForm

from cfme import exceptions
from cfme.fixtures import pytest_selenium as sel
from cfme.common.provider_views import BeforeFillMixin,\
    ContainersProviderAddView, ContainersProvidersView,\
    ContainersProviderEditView, ProvidersView
from cfme.base.credential import TokenCredential
from cfme.web_ui import (
    Quadicon, toolbar as tb, InfoBlock, Region, match_location, PagedTable)
from utils import version
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.browser import ensure_browser_open, browser
from utils.pretty import Pretty
from utils.varmeth import variable
from utils.log import logger
from utils.wait import wait_for


paged_tbl = PagedTable(table_locator="//div[@id='list_grid']//table")

cfg_btn = partial(tb.select, 'Configuration')
mon_btn = partial(tb.select, 'Monitoring')
pol_btn = partial(tb.select, 'Policy')

details_page = Region(infoblock_type='detail')


match_page = partial(match_location, controller='ems_container',
                     title='Containers Providers')


class ContainersProviderDefaultEndpoint(DefaultEndpoint):
    """Represents Containers Provider default endpoint"""
    credential_class = TokenCredential

    @property
    def view_value_mapping(self):
        out = {
            'hostname': self.hostname,
            'password': self.token,
            'confirm_password': self.token,
            'api_port': self.api_port
        }
        if version.current_version() >= '5.8':
            out['sec_protocol'] = self.sec_protocol
            if self.sec_protocol.lower() == 'ssl trusting custom ca' and \
                    hasattr(self, 'get_ca_cert'):
                out['trusted_ca_certificates'] = self.get_ca_cert()
        return out


class ContainersProviderEndpointsForm(View):
    """
     represents default Containers Provider endpoint form in UI (Add/Edit dialogs)
    """
    @View.nested
    class default(Tab, DefaultEndpointForm, BeforeFillMixin):  # NOQA
        TAB_NAME = 'Default'
        sec_protocol = BootstrapSelect('default_security_protocol')
        # trusted_ca_certificates appears only in 5.8
        trusted_ca_certificates = TextInput('default_tls_ca_certs')
        api_port = Input('default_api_port')

    @View.nested
    class hawkular(Tab, BeforeFillMixin):  # NOQA
        TAB_NAME = 'Hawkular'
        sec_protocol = BootstrapSelect(id='hawkular_security_protocol')
        # trusted_ca_certificates appears only in 5.8
        trusted_ca_certificates = TextInput('hawkular_tls_ca_certs')
        hostname = Input('hawkular_hostname')
        api_port = Input('hawkular_api_port')
        validate = Button('Validate')


class ContainersProvider(BaseProvider, Pretty):
    PLURAL = 'Providers'
    provider_types = {}
    in_version = ('5.5', version.LATEST)
    category = "container"
    pretty_attrs = ['name', 'key', 'zone']
    STATS_TO_MATCH = [
        'num_project',
        'num_service',
        'num_replication_controller',
        'num_pod',
        'num_node',
        'num_image_registry',
        'num_container']
    # TODO add 'num_volume'
    string_name = "Containers"
    page_name = "containers"
    detail_page_suffix = 'provider_detail'
    edit_page_suffix = 'provider_edit_detail'
    quad_name = None
    db_types = ["ContainerManager"]
    endpoints_form = ContainersProviderEndpointsForm

    def __init__(
            self,
            name=None,
            key=None,
            zone=None,
            endpoints=None,
            provider_data=None,
            appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.key = key
        self.zone = zone
        self.endpoints = endpoints
        self.provider_data = provider_data

    @property
    def view_value_mapping(self):
        return {
            'name': self.name,
            'prov_type': self.type,
            'zone': self.zone,
        }

    def _on_detail_page(self):
        """ Returns ``True`` if on the providers detail page, ``False`` if not."""
        ensure_browser_open()
        return sel.is_displayed(
            '//div//h1[contains(., "{} (Summary)")]'.format(self.name))

    def load_details(self, refresh=False):
        navigate_to(self, 'Details')
        if refresh:
            tb.refresh()

    def get_detail(self, *ident):
        """ Gets details from the details infoblock

        Args:
            *ident: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the InfoBlock's value.
        """
        navigate_to(self, 'Details')
        return details_page.infoblock.text(*ident)

    @variable(alias='db')
    def num_project(self):
        return self._num_db_generic('container_projects')

    @num_project.variant('ui')
    def num_project_ui(self):
        return int(self.get_detail("Relationships", "Projects"))

    @variable(alias='db')
    def num_service(self):
        return self._num_db_generic('container_services')

    @num_service.variant('ui')
    def num_service_ui(self):
        if self.appliance.version < "5.7":
            name = "Services"
        else:
            name = "Container Services"
        return int(self.get_detail("Relationships", name))

    @variable(alias='db')
    def num_replication_controller(self):
        return self._num_db_generic('container_replicators')

    @num_replication_controller.variant('ui')
    def num_replication_controller_ui(self):
        return int(self.get_detail("Relationships", "Replicators"))

    @variable(alias='db')
    def num_container_group(self):
        return self._num_db_generic('container_groups')

    @num_container_group.variant('ui')
    def num_container_group_ui(self):
        return int(self.get_detail("Relationships", "Pods"))

    @variable(alias='db')
    def num_pod(self):
        # potato tomato
        return self.num_container_group()

    @num_pod.variant('ui')
    def num_pod_ui(self):
        # potato tomato
        return self.num_container_group(method='ui')

    @variable(alias='db')
    def num_node(self):
        return self._num_db_generic('container_nodes')

    @num_node.variant('ui')
    def num_node_ui(self):
        return int(self.get_detail("Relationships", "Nodes"))

    @variable(alias='db')
    def num_container(self):
        # Containers are linked to providers through container definitions and then through pods
        res = self.appliance.db.client.engine.execute(
            "SELECT count(*) "
            "FROM ext_management_systems, container_groups, container_definitions, containers "
            "WHERE containers.container_definition_id=container_definitions.id "
            "AND container_definitions.container_group_id=container_groups.id "
            "AND container_groups.ems_id=ext_management_systems.id "
            "AND ext_management_systems.name='{}'".format(self.name))
        return int(res.first()[0])

    @num_container.variant('ui')
    def num_container_ui(self):
        return int(self.get_detail("Relationships", "Containers"))

    @variable(alias='db')
    def num_image(self):
        return self._num_db_generic('container_images')

    @num_image.variant('ui')
    def num_image_ui(self):
        if self.appliance.version < "5.7":
            name = "Images"
        else:
            name = "Container Images"
        return int(self.get_detail("Relationships", name))

    @variable(alias='db')
    def num_image_registry(self):
        return self._num_db_generic('container_image_registries')

    @num_image_registry.variant('ui')
    def num_image_registry_ui(self):
        return int(self.get_detail("Relationships", "Image Registries"))

    def pods_per_ready_status(self):
        """Grabing the Container Statuses Summary of the pods from API"""
        #  TODO: Add later this logic to wrapanapi
        entities = self.mgmt.api.get('pod')[1]['items']
        out = {}
        for entity_j in entities:
            out[entity_j['metadata']['name']] = {
                condition['type']: eval_strings([condition['status']]).pop()
                for condition in entity_j['status'].get('conditions', [])
            }
        return out


@navigator.register(ContainersProvider, 'All')
class All(CFMENavigateStep):
    VIEW = ContainersProvidersView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Providers')

    def resetter(self):
        # Reset view and selection
        tb.select("Grid View")
        from cfme.web_ui import paginator
        paginator.check_all()
        paginator.uncheck_all()


@navigator.register(ContainersProvider, 'Add')
class Add(CFMENavigateStep):
    VIEW = ContainersProviderAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        cfg_btn(version.pick({
            version.LOWEST: 'Add a New Containers Provider',
            '5.7': 'Add Existing Containers Provider'
        }))


class LoggingableView(View):

    monitor = Dropdown('Monitoring')

    def get_logging_url(self):

        def report_kibana_failure():
            raise RuntimeError("Kibana not found in the window title or content")

        browser_instance = browser()

        all_windows_before = browser_instance.window_handles
        appliance_window = browser_instance.current_window_handle

        self.monitor.item_select('External Logging')

        all_windows_after = browser_instance.window_handles

        new_windows = set(all_windows_after) - set(all_windows_before)

        if not new_windows:
            raise RuntimeError("No logging window was open!")

        logging_window = new_windows.pop()
        browser_instance.switch_to_window(logging_window)

        logging_url = browser_instance.current_url

        wait_for(lambda: "kibana" in
                         browser_instance.title.lower() + " " +
                         browser_instance.page_source.lower(),
                 fail_func=report_kibana_failure, num_sec=60, delay=5)

        browser_instance.close()
        browser_instance.switch_to_window(appliance_window)

        return logging_url


class ProviderDetailsView(BaseLoggedInPage, LoggingableView):

    @property
    def is_displayed(self):
        return match_page(summary="{} (Summary)".format(self.obj.name))


@navigator.register(ContainersProvider, 'Details')
class Details(CFMENavigateStep):
    VIEW = ProviderDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.click(Quadicon(self.obj.name, self.obj.quad_name))

    def resetter(self):
        tb.select("Summary View")


@navigator.register(ContainersProvider, 'Edit')
class Edit(CFMENavigateStep):
    VIEW = ContainersProviderEditView
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.check(Quadicon(self.obj.name, self.obj.quad_name).checkbox())
        cfg_btn('Edit Selected Containers Provider')


@navigator.register(ContainersProvider, 'EditFromDetails')
class EditFromDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        cfg_btn('Edit this Containers Provider')


@navigator.register(ContainersProvider, 'EditTags')
class EditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.check(Quadicon(self.obj.name, self.obj.quad_name).checkbox())
        pol_btn('Edit Tags')


@navigator.register(ContainersProvider, 'EditTagsFromDetails')
class EditTagsFromDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        pol_btn('Edit Tags')


@navigator.register(ContainersProvider, 'TimelinesFromDetails')
class TimelinesFromDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        mon_btn('Timelines')


@navigator.register(ContainersProvider, 'TopologyFromDetails')
class TopologyFromDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        sel.click(InfoBlock('Overview', 'Topology'))


class AdHocMetricsView(BaseLoggedInPage):
    filter_dropdown = SelectorDropdown('uib-tooltip', 'Filter by')
    filter_result_header = Text('h5.ng-binding')
    apply_btn = Button("Apply Filters")

    selected_filter = None

    @property
    def is_displayed(self):
        return False

    def wait_for_filter_option_to_load(self):
        wait_for(lambda: bool(self.filter_dropdown.items), delay=5, num_sec=60)

    def wait_for_results_to_load(self):
        wait_for(lambda: bool(int(self.filter_result_header.text.split()[0])),
                 delay=5, num_sec=60)

    def apply_filter(self):
        self.apply_btn.click()

    def set_filter(self, desired_filter):
        self.selected_filter = desired_filter
        self.filter_dropdown.fill_with(desired_filter)

    def get_random_filter(self):
        return str(random.choice(self.filter_dropdown.items))

    def get_total_results_count(self):
        return int(self.filter_result_header.text.split()[0])


@navigator.register(ContainersProvider, 'AdHoc')
class AdHocMain(CFMENavigateStep):
    VIEW = AdHocMetricsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.monitor.item_select('Ad hoc Metrics')


class ContainerObjectAllBaseView(ProvidersView):
    """Base class for container object All view.
    TITLE_TEXT should be defined in child."""

    policy = Dropdown('Policy')
    download = Dropdown('Download')

    @property
    def table(self):
        return self.entities.elements

    def title(self):
        if not hasattr(self, 'TITLE_TEXT'):
            raise Exception('TITLE_TEXT is not defined for destination {} ("All").'
                            .format(self.__class__.__name__))
        return Text('//h1[normalize-space(.) = {}]'.format(quote(self.TITLE_TEXT)))

    @property
    def is_displayed(self):
        return self.title.is_displayed


# Common methods:

class ContainersTestItem(object):
    """This is a generic test item. Especially used for parametrized functions
    """
    __test__ = False

    def __init__(self, obj, polarion_id, **additional_attrs):
        """Args:
            * obj: The container object in this test (e.g. Image)
            * The polarion test case ID
        """
        self.obj = obj
        self.polarion_id = polarion_id
        for name, value in additional_attrs.items():
            self.__setattr__(name, value)

    def pretty_id(self):
        return '{} ({})'.format(
            getattr(self.obj, '__name__', str(self.obj)),
            self.polarion_id)

    @classmethod
    def get_pretty_id(cls, obj):
        """Since sometimes the test object is wrapped within markers,
        it's difficult to find get it inside the args tree.
        hence we use this to get the object and all pretty_id function.

        Args:
            * obj: Either a ContainersTestItem or a marker that include it
        returns:
            str pretty id
        """
        if isinstance(obj, cls):
            return obj.pretty_id()
        elif hasattr(obj, 'args') and hasattr(obj, '__iter__'):
            for arg in obj.args:
                pretty_id = cls.get_pretty_id(arg)
                if pretty_id:
                    return pretty_id


class Labelable(object):
    """Provide the functionality to set labels"""
    _LABEL_NAMEVAL_PATTERN = re.compile(r'^[A-Za-z0-9_.]+$')

    def get_labels(self):
        """List labels"""
        return self.mgmt.list_labels()

    def set_label(self, name, value):

        """Sets a label to the object instance

        Args:
            :var name: the name of the label
            :var value: the value of the label

        Returns:
            self.mgmt.set_label return value.
        """
        assert self._LABEL_NAMEVAL_PATTERN.match(name), \
            'name part ({}) must match the regex pattern {}'.format(
                name, self._LABEL_NAMEVAL_PATTERN.pattern)
        assert self._LABEL_NAMEVAL_PATTERN.match(value), \
            'value part ({}) must match the regex pattern {}'.format(
                value, self._LABEL_NAMEVAL_PATTERN.pattern)
        return self.mgmt.set_label(name, value)

    def remove_label(self, name, silent_failure=False):
        """Remove label by name.
        :var: name: name of label
        :var: silent_failure: whether to raise an error or not in case of failure.

        Returns:
            :py:type:`bool` pass or fail
        Raises:
            :py:class:`LabelNotFoundException`.
        """
        try:
            self.mgmt.delete_label(name)
            return True
        except Exception:  # TODO: add appropriate exception in wrapanapi
            failure_signature = format_exc()
            if silent_failure:
                logger.warning(failure_signature)
                return False
            raise exceptions.LabelNotFoundException(failure_signature)


def navigate_and_get_rows(provider, obj, count, silent_failure=False):
    """Get <count> random rows from the obj list table,
    if <count> is greater that the number of rows, return number of rows.

    Args:
        provider: containers provider
        obj: the containers object
        table: the object's Table object
        count: number of random rows to return
        silent_failure: If True and no records found for obj, it'll
                        return None instead of raise exception

    return: list of rows"""

    view = navigate_to(obj, 'All')
    view.toolbar.view_selector.list_button.click()
    if sel.is_displayed_text("No Records Found.") and silent_failure:
        return []
    view.entities.paginator.set_items_per_page(1000)
    rows = list(view.table.rows())
    if not rows:
        return []

    return sample(rows, min(count, len(rows)))
