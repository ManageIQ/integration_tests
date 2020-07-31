from lxml.html import document_fromstring
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import Accordion
from widgetastic_patternfly import Dropdown

from cfme.common import BaseLoggedInPage
from cfme.common.vm_views import VMEntities
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import CompareToolBarActionsView
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import JSBaseEntity
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import Search
from widgetastic_manageiq import SummaryTable
from widgetastic_manageiq import Table


class DatastoreEntity(JSBaseEntity):
    @property
    def data(self):
        data_dict = super().data
        try:
            if 'quadicon' in data_dict and data_dict['quadicon']:
                quad_data = document_fromstring(data_dict['quadicon'])
                data_dict['type'] = quad_data.xpath(self.QUADRANT.format(pos="a"))[0].get('alt')
                data_dict['no_vm'] = quad_data.xpath(self.QUADRANT.format(pos="b"))[0].text
                data_dict['no_host'] = quad_data.xpath(self.QUADRANT.format(pos="c"))[0].text
            return data_dict
        except IndexError:
            return {}


class DatastoreEntities(BaseEntitiesView):
    """
    represents central view where all QuadIcons, etc are displayed
    """
    @property
    def entity_class(self):
        return DatastoreEntity


class DatastoreToolBar(View):
    """
    represents datastore toolbar and its controls
    """
    configuration = Dropdown(text='Configuration')
    policy = Dropdown(text='Policy')
    monitoring = Dropdown("Monitoring")
    download = Dropdown(text='Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class DatastoreSideBar(View):
    """
    represents left side bar. it usually contains navigation, filters, etc
    """
    @View.nested
    class datastores(Accordion):  # noqa
        ACCORDION_NAME = "Datastores"
        tree = ManageIQTree()

    @View.nested
    class clusters(Accordion):  # noqa
        ACCORDION_NAME = "Datastore Clusters"
        tree = ManageIQTree()


class DatastoresView(BaseLoggedInPage):
    """
    represents whole All Datastores page
    """
    toolbar = View.nested(DatastoreToolBar)
    sidebar = View.nested(DatastoreSideBar)
    search = View.nested(Search)
    including_entities = View.include(DatastoreEntities, use_parent=True)

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Compute', 'Infrastructure',
                                                       'Datastores'] and
                self.entities.title.text == 'All Datastores')


class HostAllDatastoresView(DatastoresView):

    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["Compute", "Infrastructure", "Hosts"] and
            self.entities.title.text == "{} (All Datastores)".format(self.context["object"].name)
        )


class ProviderAllDatastoresView(DatastoresView):
    """
    This view is used in test_provider_relationships
    """

    @property
    def is_displayed(self):
        msg = "{} (All Datastores)".format(self.context["object"].name)
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["Compute", "Infrastructure", "Providers"] and
            self.entities.title.text == msg
        )


class DatastoreManagedVMsView(BaseLoggedInPage):
    """
    This view represents All VMs and Templates page for datastores
    """
    toolbar = View.nested(DatastoreToolBar)
    including_entities = View.include(VMEntities, use_parent=True)

    @property
    def is_displayed(self):
        return (
            super(BaseLoggedInPage, self).is_displayed
            and self.navigation.currently_selected == ["Compute", "Infrastructure", "Datastores"]
            and self.entities.title.text == f'{self.context["object"].name} (All VMs and Instances)'
            and self.context["object"].name in self.breadcrumb.active_location
        )


class DatastoreDetailsView(BaseLoggedInPage):
    """
    represents Datastore Details page
    """
    title = Text('//div[@id="main-content"]//h1')
    toolbar = View.nested(DatastoreToolBar)
    sidebar = View.nested(DatastoreSideBar)

    @View.nested
    class entities(View):  # noqa
        """
        represents Details page when it is switched to Summary aka Tables view
        """
        properties = SummaryTable(title="Properties")
        registered_vms = SummaryTable(title="Information for Registered VMs")
        relationships = SummaryTable(title="Relationships")
        content = SummaryTable(title="Content")
        smart_management = SummaryTable(title="Smart Management")

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Compute', 'Infrastructure',
                                                       'Datastores'] and
                self.title.text == 'Datastore "{name}"'.format(name=self.context['object'].name))


class DatastoresCompareView(BaseLoggedInPage):
    """Compare VM / Template page."""
    # TODO: This table doesn't read properly, fix it.
    table = Table('//*[@id="compare-grid"]/table')
    title = Text('//*[@id="main-content"]//h1')

    @View.nested
    class toolbar(View):
        actions = View.nested(CompareToolBarActionsView)
        download = Dropdown(text="Download")

    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user
            and self.title.text == "Compare VM or Template"
            and self.navigation.currently_selected == ["Compute", "Infrastructure", "Datastores"]
        )
