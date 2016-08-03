from cfme.common.provider import BaseProvider, import_all_modules_of
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import (
    Quadicon, Form, AngularSelect, form_buttons, Input, toolbar as tb, InfoBlock, Region
)
from cfme.web_ui.menu import nav
from cfme.web_ui.tabstrip import TabStripForm
from utils import deferred_verpick, version
from utils.browser import ensure_browser_open
from utils.db import cfmedb
from utils.pretty import Pretty
from utils.varmeth import variable


from .. import cfg_btn, mon_btn, pol_btn, details_page

nav.add_branch(
    'containers_providers',
    {
        'containers_provider_new':
            lambda _: cfg_btn('Add a New Containers Provider'),
        'containers_provider':
        [
            lambda ctx: sel.check(Quadicon(ctx['provider'].name, None).checkbox),
            {
                'containers_provider_edit':
                lambda _: cfg_btn('Edit Selected Containers Provider'),
                'containers_provider_edit_tags':
                lambda _: pol_btn('Edit Tags')
            }],
        'containers_provider_detail':
        [
            lambda ctx: sel.click(Quadicon(ctx['provider'].name, None)),
            {
                'containers_provider_edit_detail':
                lambda _: cfg_btn('Edit this Containers Provider'),
                'containers_provider_timelines_detail':
                lambda _: mon_btn('Timelines'),
                'containers_provider_edit_tags_detail':
                lambda _: pol_btn('Edit Tags'),
                'containers_provider_topology_detail':
                lambda _: sel.click(InfoBlock('Overview', 'Topology'))
            }]
    }
)


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
            ('sec_protocol', AngularSelect("default_security_protocol")),
        ],
        "Hawkular": [
            ('hawkular_hostname', Input("hawkular_hostname")),
            ('hawkular_api_port', Input("hawkular_api_port"))
        ],
    })


prop_region = Region(
    locators={
        'properties_form': {
            version.LOWEST: properties_form,
            '5.6': properties_form_56,
        }
    }
)


class Provider(BaseProvider, Pretty):
    type_tclass = "container"
    pretty_attrs = ['name', 'key', 'zone']
    STATS_TO_MATCH = [
        'num_project', 'num_service', 'num_replication_controller', 'num_pod', 'num_node',
        'num_container', 'num_image']
    # TODO add 'num_image_registry' and 'num_volume'
    string_name = "Containers"
    page_name = "containers"
    detail_page_suffix = 'provider_detail'
    edit_page_suffix = 'provider_edit_detail'
    refresh_text = "Refresh items and relationships"
    quad_name = None
    _properties_region = prop_region  # This will get resolved in common to a real form
    add_provider_button = deferred_verpick(
        {version.LOWEST: form_buttons.FormButton("Add this Containers Provider"),
         '5.6': form_buttons.add})
    save_button = deferred_verpick(
        {version.LOWEST: form_buttons.save,
         '5.6': form_buttons.angular_save})

    def __init__(self, name=None, credentials=None, key=None,
                 zone=None, hostname=None, port=None, provider_data=None):
        if not credentials:
            credentials = {}
        self.name = name
        self.credentials = credentials
        self.key = key
        self.zone = zone
        self.hostname = hostname
        self.port = port
        self.provider_data = provider_data

    def _on_detail_page(self):
        """ Returns ``True`` if on the providers detail page, ``False`` if not."""
        ensure_browser_open()
        return sel.is_displayed('//div//h1[contains(., "{} (Summary)")]'.format(self.name))

    def load_details(self, refresh=False):
        if not self._on_detail_page():
            self.navigate(detail=True)
        elif refresh:
            tb.refresh()

    def navigate(self, detail=True):
        if detail is True:
            if not self._on_detail_page():
                sel.force_navigate('containers_provider_detail', context={'provider': self})
        else:
            sel.force_navigate('containers_provider', context={'provider': self})

    def get_detail(self, *ident):
        """ Gets details from the details infoblock

        Args:
            *ident: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the InfoBlock's value.
        """
        self.navigate(detail=True)
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
        return int(self.get_detail("Relationships", "Services"))

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
        res = cfmedb().engine.execute(
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
        return int(self.get_detail("Relationships", "Images"))

    @variable(alias='db')
    def num_image_registry(self):
        return self._num_db_generic('container_image_registries')

    @num_image_registry.variant('ui')
    def num_image_registry_ui(self):
        return int(self.get_detail("Relationships", "Image Registries"))

import_all_modules_of('cfme.containers.provider')
