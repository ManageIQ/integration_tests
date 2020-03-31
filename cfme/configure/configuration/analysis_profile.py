from copy import deepcopy

import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.widget import ConditionalSwitchableView
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown
from widgetastic_patternfly import TextInput

from cfme.base.ui import ConfigurationView
from cfme.common import BaseLoggedInPage
from cfme.exceptions import OptionNotAvailable
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.blockers import BZ
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from widgetastic_manageiq import Checkbox
from widgetastic_manageiq import CheckboxSelect
from widgetastic_manageiq import DynamicTable
from widgetastic_manageiq import PaginationPane
from widgetastic_manageiq import SummaryFormItem
from widgetastic_manageiq import Table
from widgetastic_manageiq import WaitTab


table_button_classes = [Button.DEFAULT, Button.SMALL, Button.BLOCK]


class EventsTable(DynamicTable):
    # there is a bug in Events tables, Action column has th fields instead of td one
    # this is temporary fix for that issue
    @property
    def _is_header_in_body(self):
        """Checks whether the header is erroneously specified in the body of table."""
        bz = BZ(1703141, forced_streams=['5.10'])
        return False if bz.blocks else super()._is_header_in_body


class AnalysisProfileToolbar(View):
    """Toolbar on the analysis profiles configuration page
    Works for both all page and details page
    """
    configuration = Dropdown('Configuration')


class AnalysisProfileEntities(View):
    """Main content on the analysis profiles configuration page, title and table"""
    title = Text('//div[@id="main-content"]//h1[@id="explorer_title"]'
                 '/span[@id="explorer_title_text"]')
    table = Table('//div[@id="records_div"]//table|//div[@class="miq-data-table"]//table')


class AnalysisProfileDetailsEntities(View):
    """Main content on an analysis profile details page"""
    title = Text('//div[@id="main-content"]//h1[@id="explorer_title"]'
                 '/span[@id="explorer_title_text"]')
    info_name = SummaryFormItem(group_title='Info', item_name='Name')
    info_description = SummaryFormItem(group_title='Info', item_name='Description')
    info_type = SummaryFormItem(group_title='Info', item_name='Type')
    table = Table('//h3[normalize-space(.)="File Items"]/following-sibling::table')
    # TODO 'Event Log Items' below the table doesn't have a label, SummaryFormItem doesn't work


class AnalysisProfileAllView(BaseLoggedInPage):
    """View for the Analysis Profile collection page"""
    @property
    def is_displayed(self):
        return (self.logged_in_as_current_user and
                self.sidebar.accordions.settings.tree.selected_item.text == 'Analysis Profiles' and
                self.entities.title.text == 'Settings Analysis Profiles')

    toolbar = View.nested(AnalysisProfileToolbar)
    sidebar = View.nested(ConfigurationView)
    entities = View.nested(AnalysisProfileEntities)
    paginator = PaginationPane()


class AnalysisProfileDetailsView(BaseLoggedInPage):
    """View for an analysis profile details page"""
    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user and
            self.entities.title.text == 'Settings Analysis Profile "{}"'
                                        .format(self.context['object'].name))

    toolbar = View.nested(AnalysisProfileToolbar)
    sidebar = View.nested(ConfigurationView)
    entities = View.nested(AnalysisProfileDetailsEntities)


class AnalysisProfileBaseAddForm(View):
    """View for the common elements of the two AP forms"""
    name = TextInput(id='name')
    description = TextInput(id='description')

    @View.nested
    class files(WaitTab):  # noqa
        TAB_NAME = 'File'
        tab_form = DynamicTable(
            locator='.//h3[normalize-space(.)="File Entry"]/following-sibling::table',
            column_widgets={
                'Name': TextInput(id='entry_fname'),
                'Collect Contents?': Checkbox(id='entry_content'),
                'Actions': Button(title='Add this entry', classes=table_button_classes)},
            assoc_column='Name', rows_ignore_top=1, action_row=0)

    @View.nested
    class events(WaitTab):  # noqa
        TAB_NAME = 'Event Log'
        tab_form = EventsTable(
            locator='.//h3[normalize-space(.)="Event Log Entry"]/following-sibling::table',
            column_widgets={
                'Name': TextInput(id='entry_name'),
                'Filter Message': TextInput(id='entry_message'),
                'Level': TextInput(id='entry_level'),
                'Source': TextInput(id='entry_source'),
                '# of Days': TextInput(id='entry_num_days'),
                'Actions': Button(title='Add this entry', classes=table_button_classes)},
            assoc_column='Name', rows_ignore_top=1, action_row=0)


class AnalysisProfileAddView(BaseLoggedInPage):
    """View for the add form, switches between host/vm based on object type
    Uses a switchable view based on the profile type widget
    """

    title = Text('//div[@id="main-content"]//h1[@id="explorer_title"]'
                 '/span[@id="explorer_title_text"]')
    # This is a ALMOST a SummaryFormItem, but there's no div to wrap the items so it doesn't work
    # instead I have this nasty xpath to hack around that
    profile_type = Text(
        locator='.//h3[normalize-space(.)="Basic Information"]'
                '/following-sibling::div[@class="form-group"]'
                '/label[normalize-space(.)="Type"]'
                '/following-sibling::div/p')
    form = ConditionalSwitchableView(reference='profile_type')
    # to avoid dynamic table buttons use title + alt + classes
    add = Button(title='Add', classes=[Button.PRIMARY], alt='Add')
    cancel = Button(title='Cancel', classes=[Button.DEFAULT], alt='Cancel')

    @form.register('Host')
    class AnalysisProfileAddHost(AnalysisProfileBaseAddForm):
        """View for the host profile add form"""
        pass

    @form.register('Vm')
    class AnalysisProfileAddVm(AnalysisProfileBaseAddForm):
        """View for the vm profile add form"""
        @View.nested
        class categories(WaitTab):  # noqa
            TAB_NAME = 'Category'
            tab_form = CheckboxSelect(search_root='form_div')

        @View.nested
        class registry(WaitTab):  # noqa
            TAB_NAME = 'Registry'
            tab_form = DynamicTable(
                locator='.//h3[normalize-space(.)="Registry Entry"]/following-sibling::table',
                column_widgets={
                    'Registry Hive': Text('.//tr[@id="new_tr"]/td[normalize-space(.)="HKLM"]'),
                    'Registry Key': TextInput(id='entry_kname'),
                    'Registry Value': TextInput(id='entry_value'),
                    'Actions': Button(title='Add this entry', classes=table_button_classes)},
                assoc_column='Registry Key', rows_ignore_top=1, action_row=0)

    @property
    def is_displayed(self):
        return self.title.text == 'Adding a new Analysis Profile'


class AnalysisProfileAddVmView(AnalysisProfileAddView):
    @property
    def is_displayed(self):
        return (
            self.title.text == 'Adding a new Analysis Profile' and
            self.profile_type.text == self.context['object'].VM_TYPE)


class AnalysisProfileAddHostView(AnalysisProfileAddView):
    @property
    def is_displayed(self):
        return (
            self.title.text == 'Adding a new Analysis Profile' and
            self.profile_type.text == self.context['object'].HOST_TYPE)


class AnalysisProfileEditView(AnalysisProfileAddView):
    """View for the edit form, extends add view since all fields are the same and editable"""
    @property
    def is_displayed(self):
        expected_title = 'Editing Analysis Profile "{}"'.format(self.context['object'].name)
        return (
            self.title.text == expected_title and
            self.profile_type.text == self.context['object'].profile_type)

    # to avoid dynamic table buttons use title + alt + classes
    save = Button(title='Save Changes', classes=[Button.PRIMARY])
    reset = Button(title='Reset Changes', classes=[Button.DEFAULT], alt='Save Changes')


class AnalysisProfileCopyView(AnalysisProfileAddView):
    """View for the copy form is the same as an add

    The name field is by default set with 'Copy of [profile name of copy source]
    Don't want to assert against this field to separately verify the view is displayed
    If is_displayed is called after the form is changed it will be false negative"""
    pass


@attr.s
class AnalysisProfile(Pretty, Updateable, BaseEntity):
    """Analysis profiles, Vm and Host type

    Example: Note the keys for files, events, registry should match UI columns

        .. code-block:: python

            p = AnalysisProfile(name, description, profile_type='VM')
            p.files = [
                {"Name": "/some/anotherfile", "Collect Contents?": True},
            ]
            p.events = [
                {"Name": name, "Filter Message": msg, "Level": lvl, "Source": src, "# of Days": 1},
            ]
            p.registry = [
                {"Registry Key": key, "Registry Value": value},
            ]
            p.categories = ["System", "Software"]  # Use the checkbox text name
            p.create()
            p2 = p.copy(new_name="updated AP")
            with update(p):
                p.files = [{"Name": "/changed". "Collect Contents?": False}]
            p.delete()

    """
    pretty_attrs = "name", "description", "files", "events"

    name = attr.ib()
    description = attr.ib()
    profile_type = attr.ib()
    files = attr.ib(default=None)
    events = attr.ib(default=None)
    categories = attr.ib(default=None)
    registry = attr.ib(default=None)

    def update(self, updates, cancel=False):
        """Update the existing Analysis Profile with given updates dict
        Make use of Updateable and use `with` to update object as well
        Note the updates dict should take the structure below if called directly

            .. code-block:: python

                updates = {
                    'name': self.name,
                    'description': self.description,
                    'files': {
                        'tab_form': ['/example/file']},
                    'events': {
                        'tab_form': ['example_event']},
                    'categories': {
                        'tab_form': ['Example']},
                    'registry': {
                        'tab_form': ['example_registry']}
                }

            Args:
                updates (dict): Dictionary of values to change in the object.
                cancel (boolean): whether to cancel the update
        """
        # hack to work around how updates are passed when used in context mgr
        # TODO revisit this method when BZ is fixed:
        # https://bugzilla.redhat.com/show_bug.cgi?id=1485953
        form_fill_args = self.parent.form_fill_args(updates=updates)
        view = navigate_to(self, 'Edit')
        changed = view.form.fill(form_fill_args)

        if changed and not cancel:  # save button won't be enabled if nothing was changed
            view.save.click()
        else:
            view.cancel.click()

        # redirects to details if edited from there
        view = self.create_view(AnalysisProfileDetailsView, override=updates)
        assert view.is_displayed

    def delete(self, cancel=False):
        """Delete self via details page"""
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select("Delete this Analysis Profile",
                                               handle_alert=not cancel)
        view = self.create_view(
            AnalysisProfileDetailsView if cancel else AnalysisProfileAllView)
        view.flush_widget_cache()
        assert view.is_displayed

    def copy(self, new_name=None, cancel=False):
        """Copy the Analysis Profile"""
        # Create a new object to return in addition to running copy in the UI
        # TODO revisit this method when BZ is fixed:
        # https://bugzilla.redhat.com/show_bug.cgi?id=1485953
        if not new_name:
            new_name = f'{self.name}-copy'
        new_profile = self.parent.instantiate(
            name=new_name,
            description=self.description,
            profile_type=self.profile_type,
            files=self.files,
            events=self.events,
            categories=self.categories,
            registry=self.registry
        )

        # actually run copy in the UI, fill the form
        view = navigate_to(self, 'Copy')
        form_args = self.parent.form_fill_args(updates={'name': new_profile.name})
        view.form.fill(form_args)
        if cancel:
            view.cancel.click()
        else:
            view.add.click()

        # check the result
        view = self.create_view(
            AnalysisProfileDetailsView if cancel else AnalysisProfileAllView)
        view.flush_widget_cache()
        assert view.is_displayed
        return new_profile


@attr.s
class AnalysisProfileCollection(BaseCollection):

    VM_TYPE = 'Vm'
    HOST_TYPE = 'Host'

    ENTITY = AnalysisProfile

    def create(self, name, description, profile_type, files=None, events=None, categories=None,
               registry=None, cancel=False):
        """Add Analysis Profile to appliance"""
        # The tab form values have to be dictionaries with the root key matching the tab widget name
        form_values = self.form_fill_args({
            'name': name,
            'description': description,
            'categories': categories,
            'files': files,
            'registry': registry,
            'events': events
        })

        if profile_type.lower() == 'vm':
            view = navigate_to(self, 'AddVmProfile')
        elif profile_type.lower() == 'host':
            view = navigate_to(self, 'AddHostProfile')
        else:
            raise OptionNotAvailable('Not such profile available')

        view.form.fill(form_values)

        if cancel:
            view.cancel.click()
        else:
            view.add.click()

        view.flush_widget_cache()
        view = self.create_view(AnalysisProfileAllView)

        assert view.is_displayed

        return self.instantiate(
            name=name,
            description=description,
            profile_type=profile_type,
            files=files,
            events=events,
            categories=categories,
            registry=registry
        )

    def form_fill_args(self, updates=None):
        """Build a dictionary of nested tab_forms for assoc_fill from a flat object dictionary
        If updates dictionary is passed, it is used instead of `self`
        This should work for create or update form fill args
        """
        fill_args = {'profile_type': None}  # this can't be set when adding or editing
        for key in ['name', 'description']:
            if updates and key in updates:
                arg = updates[key]
                fill_args[key] = arg

        for key in ['files', 'events', 'registry']:
            if updates and key in updates:
                data = deepcopy(updates[key])
                if isinstance(data, list):
                    # It would be much better to not have these hardcoded, but I can't get them
                    # statically from the form (ConditionalSwitchWidget)
                    assoc_column = 'Name' if key in ['files', 'events'] else 'Registry Key'
                    values_dict = {}
                    for item in data:
                        name = item.pop(assoc_column)
                        values_dict[name] = item

                    fill_args[key] = {'tab_form': values_dict}

        for key in ['categories']:
            # No assoc_fill for checkbox select, just tab_form mapping here
            if updates and key in updates:
                arg = deepcopy(updates[key])
                fill_args[key] = {'tab_form': arg}

        return fill_args

    def all(self):
        profiles = []
        view = navigate_to(self, 'All')
        view.paginator.set_items_per_page(1000)
        all_profiles_rows = view.entities.table
        if all_profiles_rows:
            for profile in all_profiles_rows:
                profiles.append(self.instantiate(
                    name=profile.name.text,
                    description=profile.description.text,
                    profile_type=profile.type.text))
        return profiles


@navigator.register(AnalysisProfileCollection, 'All')
class AnalysisProfileAll(CFMENavigateStep):
    VIEW = AnalysisProfileAllView
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self, *args, **kwargs):
        server_region = self.obj.appliance.server_region_string()
        self.prerequisite_view.accordions.settings.tree.click_path(
            server_region, "Analysis Profiles")

    def resetter(self, *args, **kwargs):
        self.view.browser.refresh()


@navigator.register(AnalysisProfileCollection, 'AddVmProfile')
class AnalysisProfileVmAdd(CFMENavigateStep):
    VIEW = AnalysisProfileAddVmView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select("Add VM Analysis Profile")


@navigator.register(AnalysisProfileCollection, 'AddHostProfile')
class AnalysisProfileHostAdd(CFMENavigateStep):
    VIEW = AnalysisProfileAddHostView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select("Add Host Analysis Profile")


@navigator.register(AnalysisProfile, 'Details')
class AnalysisProfileDetails(CFMENavigateStep):
    VIEW = AnalysisProfileDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        server_region = self.obj.appliance.server_region_string()
        self.prerequisite_view.sidebar.accordions.settings.tree.click_path(
            server_region, "Analysis Profiles", self.obj.name)


@navigator.register(AnalysisProfile, 'Edit')
class AnalysisProfileEdit(CFMENavigateStep):
    VIEW = AnalysisProfileEditView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select("Edit this Analysis Profile")


@navigator.register(AnalysisProfile, 'Copy')
class AnalysisProfileCopy(CFMENavigateStep):
    VIEW = AnalysisProfileCopyView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select(
            'Copy this selected Analysis Profile')
