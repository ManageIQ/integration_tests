"""A model of an Openstack Infrastructure Node in CFME."""
import attr

from cfme.infrastructure.host import Host
from cfme.infrastructure.host import HostsCollection
from cfme.utils.appliance.implementations.ui import navigate_to


class OpenstackNode(Host):
    """
    Model of Openstack Infrastructure node.
    Extends the behavior of Infrastructure Host with Openstack-only functions.
    For usage and __init__ args check the doc to Host class
    """

    def toggle_maintenance_mode(self):
        """Initiate maintenance mode"""
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Toggle Maintenance Mode', handle_alert=True)
        exp_msg = f'"{self.name}": Toggle Maintenance successfully initiated'
        view.flash.assert_success_message(exp_msg)

    def provide_node(self):
        """Provide node - make it available"""
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Provide Node', handle_alert=True)
        exp_msg = f'"{self.name}": Provide successfully initiated'
        view.flash.assert_success_message(exp_msg)

    def run_introspection(self):
        """Run introspection"""
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Introspect Node', handle_alert=True)
        exp_msg = f'"{self.name}": Introspect successfully initiated'
        view.flash.assert_success_message(exp_msg)


@attr.s
class OpenstackNodeCollection(HostsCollection):
    """Collection object for the :py:class:`cfme.infrastructure.openstack_node.OpenstackNode`."""

    ENTITY = OpenstackNode
