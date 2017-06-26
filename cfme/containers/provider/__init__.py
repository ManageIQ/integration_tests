from functools import partial
from random import sample
import re
import json

from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.common.provider import BaseProvider
from cfme import exceptions
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import (
    Quadicon, Form, AngularSelect, form_buttons, Input, toolbar as tb,
    InfoBlock, Region, paginator, match_location, PagedTable, CheckboxTable)
from cfme.web_ui.tabstrip import TabStripForm
from utils import deferred_verpick, version
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.browser import ensure_browser_open
from utils.pretty import Pretty
from utils.varmeth import variable
from utils.log import logger


paged_tbl = PagedTable(table_locator="//div[@id='list_grid']//table")

cfg_btn = partial(tb.select, 'Configuration')
mon_btn = partial(tb.select, 'Monitoring')
pol_btn = partial(tb.select, 'Policy')

details_page = Region(infoblock_type='detail')


properties_form = Form(
    fields=[
        ('type_select', AngularSelect('server_emstype')),
        ('name_text', Input('name')),
        ('hostname_text', Input('hostname')),
        ('port_text', Input('port'))
    ])

properties_form_56 = TabStripForm(
    fields=[
        ('type_select', AngularSelect('ems_type')),
        ('name_text', Input('name'))
    ],
    tab_fields={
        "Default": [
            ('hostname_text', Input("default_hostname")),
            ('port_text', Input("default_api_port")),
            ('sec_protocol', AngularSelect("default_security_protocol", exact=True)),
        ],
        "Hawkular": [
            ('hawkular_hostname', Input("hawkular_hostname")),
            ('hawkular_api_port', Input("hawkular_api_port"))
        ],
    })

properties_form_58 = TabStripForm(
    fields=[
        ('type_select', AngularSelect('ems_type')),
        ('name_text', Input('name'))
    ],
    tab_fields={
        "Default": [
            ('hostname_text', Input("default_hostname")),
            ('port_text', Input("default_api_port")),
            ('sec_protocol', AngularSelect("default_security_protocol", exact=True)),
            ('trusted_ca_certificates', Input("default_tls_ca_certs"))
        ],
        "Hawkular": [
            ('hawkular_hostname', Input("hawkular_hostname")),
            ('hawkular_api_port', Input("hawkular_api_port")),
            ('hawkular_sec_protocol', AngularSelect("hawkular_security_protocol", exact=True)),
            ('hawkular_ca_certificates', Input("hawkular_tls_ca_certs"))
        ],
    })


prop_region = Region(
    locators={
        'properties_form': {
            version.LOWEST: properties_form,
            '5.6': properties_form_56,
            '5.8': properties_form_58
        }
    }
)

match_page = partial(match_location, controller='ems_container',
                     title='Containers Providers')


class ContainersProvider(BaseProvider, Pretty):
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
    refresh_text = "Refresh items and relationships"
    quad_name = None
    db_types = ["ContainerManager"]
    _properties_region = prop_region  # This will get resolved in common to a real form
    add_provider_button = deferred_verpick(
        {version.LOWEST: form_buttons.FormButton("Add this Containers Provider"),
         '5.6': form_buttons.add})
    save_button = deferred_verpick(
        {version.LOWEST: form_buttons.save,
         '5.6': form_buttons.angular_save})

    def __init__(
            self,
            name=None,
            credentials=None,
            key=None,
            zone=None,
            hawkular=None,
            hostname=None,
            api_port=None,
            sec_protocol=None,
            hawkular_sec_protocol=None,
            hawkular_hostname=None,
            hawkular_api_port=None,
            provider_data=None,
            appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        if not credentials:
            credentials = {}
        self.name = name
        self.credentials = credentials
        self.key = key
        self.zone = zone
        self.hawkular = hawkular
        self.hostname = hostname
        self.api_port = api_port
        self.sec_protocol = sec_protocol
        self.hawkular_sec_protocol = hawkular_sec_protocol
        self.hawkular_hostname = hawkular_hostname
        self.hawkular_api_port = hawkular_api_port
        self.provider_data = provider_data

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


@navigator.register(ContainersProvider, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def am_i_here(self):
        return match_page(summary='Pods')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Providers')

    def resetter(self):
        # Reset view and selection
        tb.select("Grid View")
        sel.check(paginator.check_all())
        sel.uncheck(paginator.check_all())


@navigator.register(ContainersProvider, 'Add')
class Add(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        cfg_btn(version.pick({
            version.LOWEST: 'Add a New Containers Provider',
            '5.7': 'Add Existing Containers Provider'
        }))


@navigator.register(ContainersProvider, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return match_page(summary="{} (Summary)".format(self.obj.name))

    def step(self):
        sel.click(Quadicon(self.obj.name, self.obj.quad_name))

    def resetter(self):
        tb.select("Summary View")


@navigator.register(ContainersProvider, 'Edit')
class Edit(CFMENavigateStep):
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


class Labelable(object):
    """Provide the functionality to set labels"""
    _LABEL_NAMEVAL_PATTERN = re.compile(r'^[A-Za-z0-9_.]+$')
    _CONTAINER_OBJECTS = {
        # <object_name>: <resource name>
        'Image': 'image',
        'Node': 'node',
        'Pod': 'pod',
        'Project': 'namespace',
        'Replicator': 'rc',
        'Route': 'route',
        'Service': 'service',
        'Template': 'template',
        'Volume': 'persistentVolume'
    }

    @property
    def _cli_resource_name(self):
        return ('sha256:{}'.format(self.sha256) if
               (self.__class__.__name__ == 'Image') else self.name)

    @property
    def _cli_resource_type(self):
        return self._CONTAINER_OBJECTS[self.__class__.__name__]

    def _get_json(self):
        "Getting resource json"
        if hasattr(self, 'project_name'):
            self.provider.cli.run_command('oc project {}'.format(self.project_name))
        return json.loads(str(self.provider.cli.run_command(
            'oc get {} {} -o json'.
            format(
                self._cli_resource_type, self._cli_resource_name
            )
        )))

    def _get_metadata(self):
        """Get object metadata"""
        return self._get_json()['metadata']

    def get_labels(self):
        """List labels"""
        return self._get_metadata().get('labels', {})

    def set_label(self, name, value):

        """Sets a label to the object instance

        Args:
            :var name: the name of the label
            :var value: the value of the label

        Returns:
            :py:class:`SSHResult`

        Raises:
            :py:class:`SetLabelException`.
        """

        assert self.__class__.__name__ in self._CONTAINER_OBJECTS.keys(), \
            'object {} is not supported for label assignments.'
        name, value = str(name), str(value)
        assert self._LABEL_NAMEVAL_PATTERN.match(name), \
            'name part ({}) must match the regex pattern {}'.format(
                name, self._LABEL_NAMEVAL_PATTERN.pattern)
        assert self._LABEL_NAMEVAL_PATTERN.match(value), \
            'value part ({}) must match the regex pattern {}'.format(
                value, self._LABEL_NAMEVAL_PATTERN.pattern)

        if hasattr(self, 'project_name'):
            results = self.provider.cli.run_command('oc project {}'.format(self.project_name))
            assert results.success, 'Could not set project {}. SSH Results: {}'.format(
                self.project_name, results)

        payload = {'metadata': {'labels': {name: value}}}

        results = self.provider.cli.run_command(
            'oc patch {} {} -p \'{}\''.format(self._cli_resource_type, self._cli_resource_name,
                json.dumps(payload)
            )
        )

        if results.failed:
            raise exceptions.SetLabelException(
                'Failed to set label "{} = {}" to {} {}. SSH Results: {}'
                .format(name, value, self.__class__.__name__, self.name, results))
        return results

    def remove_label(self, name, silent_failure=False):
        """Remove label by name.
        :var: name: name of label
        :var: silent_failure: whether to raise an error or not in case of failure.

        Returns:
            :py:type:`bool` pass or fail
        Raises:
            :py:class:`LabelNotFoundException`.
        """
        json_content = self._get_json()
        if name not in json_content['metadata'].get('labels', {}).keys():
            failure_signature = 'Could not find label "{}", labels: {}' \
                .format(name, json_content['metadata']['labels'])
            if silent_failure:
                logger.warning(failure_signature)
                return False
            else:
                raise exceptions.LabelNotFoundException(failure_signature)
        self.provider.cli.run_command(
            'oc label {} {} {}-'.format(
                self._cli_resource_type,
                ('sha256:{}'.format(self.sha256)
                 if (self.__class__.__name__ == 'Image') else self.name),
                name
            )
        )
        return True


def navigate_and_get_rows(provider, obj, count, table_class=CheckboxTable,
                          silent_failure=False):
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

    navigate_to(obj, 'All')
    tb.select('List View')
    if sel.is_displayed_text("No Records Found.") and silent_failure:
        return []
    paginator.results_per_page(1000)
    table = table_class(table_locator="//div[@id='list_grid']//table")
    rows = table.rows_as_list()
    if not rows:
        return []

    return sample(rows, min(count, len(rows)))
