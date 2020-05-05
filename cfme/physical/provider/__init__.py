import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from varmeth import variable
from widgetastic.exceptions import NoSuchElementException
from widgetastic.utils import Fillable

from cfme.base.ui import Server
from cfme.common import BaseLoggedInPage
from cfme.common.provider import BaseProvider
from cfme.common.provider import provider_types
from cfme.common.provider_views import PhysicalProviderAddView
from cfme.common.provider_views import PhysicalProviderDetailsView
from cfme.common.provider_views import PhysicalProvidersView
from cfme.common.provider_views import ProviderEditView
from cfme.modeling.base import BaseCollection
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.net import resolve_hostname
from cfme.utils.pretty import Pretty
from widgetastic_manageiq import StatusBox


@attr.s(eq=False)
class PhysicalProvider(Pretty, BaseProvider, Fillable):
    """
    Abstract model of an infrastructure provider in cfme. See VMwareProvider or RHEVMProvider.
    """
    provider_types = {}
    category = "physical"
    pretty_attrs = ['name']
    STATS_TO_MATCH = ['num_server']
    string_name = "Physical Infrastructure"
    page_name = "infrastructure"
    db_types = ["PhysicalInfraManager"]

    name = attr.ib(default=None)
    key = attr.ib(default=None)

    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        self.parent = self.appliance.collections.physical_providers

    @property
    def hostname(self):
        return getattr(self.default_endpoint, "hostname", None)

    @property
    def ip_address(self):
        return getattr(self.default_endpoint, "ipaddress", resolve_hostname(str(self.hostname)))

    @variable(alias='ui')
    def num_server(self):
        view = navigate_to(self, 'Details')
        try:
            num = view.entities.summary('Relationships').get_text_of('Physical Servers')
        except NoSuchElementException:
            logger.error("Couldn't find number of servers")
        return int(num)

    def delete(self, cancel=False):
        """
        Deletes a provider from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """
        view = navigate_to(self, 'Details')
        item_title = 'Remove this {} Provider from Inventory'
        view.toolbar.configuration.item_select(item_title.format("Infrastructure"),
                                               handle_alert=not cancel)
        if not cancel:
            view.flash.assert_no_error()


@attr.s
class PhysicalProviderCollection(BaseCollection):
    """Collection object for PhysicalProvider object
    """

    ENTITY = PhysicalProvider

    def all(self):
        view = navigate_to(self, 'All')
        provs = view.entities.get_all(surf_pages=True)

        # trying to figure out provider type and class
        # todo: move to all providers collection later
        def _get_class(pid):
            prov_type = self.appliance.rest_api.collections.providers.get(id=pid)['type']
            for prov_class in provider_types('infra').values():
                if prov_class.db_types[0] in prov_type:
                    return prov_class

        return [self.instantiate(prov_class=_get_class(p.data['id']), name=p.name) for p in provs]

    def instantiate(self, prov_class, *args, **kwargs):
        return prov_class.from_collection(self, *args, **kwargs)

    def create(self, prov_class, *args, **kwargs):
        # ugly workaround until I move everything to main class
        class_attrs = [at.name for at in attr.fields(prov_class)]
        init_kwargs = {}
        create_kwargs = {}
        for name, value in kwargs.items():
            if name not in class_attrs:
                create_kwargs[name] = value
            else:
                init_kwargs[name] = value

        obj = self.instantiate(prov_class, *args, **init_kwargs)
        obj.create(**create_kwargs)
        return obj


@navigator.register(PhysicalProviderCollection, 'All')
@navigator.register(Server, 'PhysicalProviders')
@navigator.register(PhysicalProvider, 'All')
class All(CFMENavigateStep):
    # This view will need to be created
    VIEW = PhysicalProvidersView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Physical Infrastructure', 'Providers')

    def resetter(self, *args, **kwargs):
        # Reset view and selection
        pass


@navigator.register(PhysicalProvider, 'Details')
class Details(CFMENavigateStep):
    VIEW = PhysicalProviderDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()

    def resetter(self, *args, **kwargs):
        """Reset view and selection"""
        self.view.toolbar.view_selector.select('Summary View')


@navigator.register(PhysicalProvider, 'Edit')
class Edit(CFMENavigateStep):
    VIEW = ProviderEditView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select(
            'Edit this Infrastructure Provider')


@navigator.register(PhysicalProviderCollection, 'Add')
@navigator.register(PhysicalProvider, 'Add')
class Add(CFMENavigateStep):
    VIEW = PhysicalProviderAddView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select(
            'Add a New Physical Infrastructure Provider'
        )


class PhysicalOverviewView(BaseLoggedInPage):
    providers = StatusBox('Providers')
    chassis = StatusBox('Chassis')
    racks = StatusBox('Racks')
    servers = StatusBox('Servers')
    storages = StatusBox('Storages')
    switches = StatusBox('Switches')

    @property
    def is_displayed(self):
        return self.navigation.currently_selected == ["Compute",
            "Physical Infrastructure", "Overview"]


@navigator.register(PhysicalProviderCollection, 'Overview')
class Overview(CFMENavigateStep):
    VIEW = PhysicalOverviewView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select("Compute", "Physical Infrastructure", "Overview")
