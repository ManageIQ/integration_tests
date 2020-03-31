import attr

from cfme.common import Taggable
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.pretty import Pretty


@attr.s
class ConfigSystem(BaseEntity, Pretty, Taggable):
    """The tags pages of the config system"""
    pretty_attrs = ['name', 'manager_key']

    name = attr.ib()
    profile = attr.ib(default=None)

    def get_tags(self, tenant="My Company Tags"):
        """Overridden get_tags method to deal with the fact that configured systems don't have a
        details view."""
        view = navigate_to(self, 'EditTags')
        return [
            self.appliance.collections.categories.instantiate(
                display_name=r.category.text.replace('*', '').strip()).collections.tags.instantiate(
                display_name=r.assigned_value.text.strip())
            for r in view.form.tags
        ]


@attr.s
class ConfigSystemsCollection(BaseCollection):
    """ Collection of ConfigSystem objects """
    ENTITY = ConfigSystem

    def all(self):
        """Returns 'ConfigSystem' objects that are active under the system's profile"""
        if self.filters:
            view = navigate_to(self.parent, 'Details')
            profile = self.parent
        else:
            view = navigate_to(self, "All")
            profile = None

        view.toolbar.view_selector.select('List View')
        # make sure all entities are displayed
        view.entities.paginator.set_items_per_page(view.entities.paginator.items_amount)

        if view.entities.elements.is_displayed:
            return [
                self.instantiate(row.hostname.text, profile)
                for row in view.entities.elements
            ]
        else:
            return []
