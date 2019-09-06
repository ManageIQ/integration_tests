# -*- coding: utf-8 -*-
import attr

from cfme.infrastructure.config_management.config_systems import ConfigSystemsCollection
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.pretty import Pretty
from cfme.utils.wait import wait_for


@attr.s
class ConfigProfile(BaseEntity, Pretty):
    """Configuration profile object (foreman-side hostgroup)

    Args:
        name: Name of the profile
        manager: ConfigManager object which this profile is bound to
    """
    pretty_attrs = ['name', 'manager']

    name = attr.ib()
    manager = attr.ib()

    _collections = {"config_systems": ConfigSystemsCollection}

    @property
    def type(self):
        kind = "Configuration Profile"
        if self.manager.type == "Ansible Tower":
            kind = "Inventory Group"
        return kind

    @property
    def config_systems(self):
        """Returns 'ConfigSystem' objects that are active under this profile"""
        return self.collections.config_systems.all()


@attr.s
class ConfigProfilesCollection(BaseCollection):
    """ Collection of ConfigProfiles (nested collection of ConfigManager) """
    ENTITY = ConfigProfile

    def all(self):
        """Returns 'ConfigProfile' configuration profiles (hostgroups) available on this manager"""
        view = navigate_to(self.parent, "Details")
        # TODO - remove it later.Workaround for BZ 1452425
        view.toolbar.view_selector.select('List View')
        view.toolbar.refresh.click()
        wait_for(lambda: view.entities.elements.is_displayed, fail_func=view.toolbar.refresh.click,
                 handle_exception=True, num_sec=60, delay=5)
        config_profiles = []
        for row in view.entities.elements:
            if self.parent.type == 'Ansible Tower':
                name = row.name.text
            else:
                name = row.description.text
            if 'unassigned' in name.lower():
                continue
            config_profiles.append(self.instantiate(name=name, manager=self.parent))
        return config_profiles
