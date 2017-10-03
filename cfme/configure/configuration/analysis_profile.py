# -*- coding: utf-8 -*-
from copy import deepcopy

from navmazing import NavigateToSibling, NavigateToObject, NavigationDestinationNotFound
from widgetastic.widget import View, Text, ConditionalSwitchableView
from widgetastic.utils import Fillable
from widgetastic_patternfly import Dropdown, Button, CandidateNotFound, TextInput, Tab
from widgetastic_manageiq import (
    Table, PaginationPane, SummaryFormItem, Checkbox, CheckboxSelect, DynamicTable)

from cfme.base.login import BaseLoggedInPage
from cfme.base.ui import Server, ConfigurationView
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable


table_button_classes = [Button.DEFAULT, Button.SMALL, Button.BLOCK]


class AnalysisProfileToolbar(View):
    """Toolbar on the analysis profiles configuration page
    Works for both all page and details page
    """
    configuration = Dropdown('Configuration')


class AnalysisProfileEntities(View):
    """Main content on the analysis profiles configuration page, title and table"""
    title = Text('//div[@id="main-content"]//h1[@id="explorer_title"]'
                 '/span[@id="explorer_title_text"]')
    table = Table('//div[@id="records_div"]//table')


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
    paginator = View.nested(PaginationPane)


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
    class files(Tab):  # noqa
        TAB_NAME = 'File'
        tab_form = DynamicTable(
            locator='.//h3[normalize-space(.)="File Entry"]/following-sibling::table',
            column_widgets={
                'Name': TextInput(id='entry_fname'),
                'Collect Contents?': Checkbox(id='entry_content'),
                'Actions': Button(title='Add this entry', classes=table_button_classes)},
            assoc_column='Name', rows_ignore_top=1, action_row=0)

    @View.nested
    class events(Tab):  # noqa
        TAB_NAME = 'Event Log'
        tab_form = DynamicTable(
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
    @property
    def is_displayed(self):
        return (
            self.title.text == 'Adding a new Analysis Profile' and
            self.profile_type.text == self.context['object'].profile_type)

    title = Text('//div[@id="main-content"]//h1[@id="explorer_title"]'
                 '/span[@id="explorer_title_text"]')
    # This is a ALMOST a SummaryFormItem, but there's no div to wrap the items so it doesn't work
    # instead I have this nasty xpath to hack around that
    profile_type = Text(
        locator='.//h3[normalize-space(.)="Basic Information"]'
                '/following-sibling::div[@class="form-group"]'
                '/label[normalize-space(.)="Type"]'
                '/following-sibling::div')
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
        class categories(Tab):  # noqa
            TAB_NAME = 'Category'
            tab_form = CheckboxSelect(search_root='form_div')

        @View.nested
        class registry(Tab):  # noqa
            TAB_NAME = 'Registry'
            tab_form = DynamicTable(
                locator='.//h3[normalize-space(.)="Registry Entry"]/following-sibling::table',
                column_widgets={
                    'Registry Hive': Text('.//tr[@id="new_tr"]/td[normalize-space(.)="HKLM"]'),
                    'Registry Key': TextInput(id='entry_kname'),
                    'Registry Value': TextInput(id='entry_value'),
                    'Actions': Button(title='Add this entry', classes=table_button_classes)},
                assoc_column='Registry Key', rows_ignore_top=1, action_row=0)


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


class AnalysisProfile(Pretty, Updateable, Fillable, Navigatable):
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
    CREATE_LOC = None
    pretty_attrs = "name", "description", "files", "events"
    VM_TYPE = 'Vm'
    HOST_TYPE = 'Host'

    def __init__(self, name, description, profile_type, files=None, events=None, categories=None,
                 registry=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.description = description
        self.files = files if isinstance(files, (list, type(None))) else [files]
        self.events = events if isinstance(events, (list, type(None))) else [events]
        self.categories = categories if isinstance(categories, (list, type(None))) else [categories]
        self.registry = registry if isinstance(registry, (list, type(None))) else [registry]
        if profile_type in (self.VM_TYPE, self.HOST_TYPE):
            self.profile_type = profile_type
        else:
            raise ValueError("Profile Type is incorrect")

    def create(self, cancel=False):
        """Add Analysis Profile to appliance"""
        # The tab form values have to be dictionaries with the root key matching the tab widget name
        form_values = self.form_fill_args()

        view = navigate_to(self, 'Add')
        view.form.fill(form_values)

        if cancel:
            view.cancel.click()
        else:
            view.add.click()

        view.flush_widget_cache()
        view = self.create_view(AnalysisProfileAllView)

        assert view.is_displayed
        view.flash.assert_success_message(
            'Add of new Analysis Profile was cancelled by the user'
            if cancel
            else 'Analysis Profile "{}" was saved'.format(self.name))

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
        form_fill_args = self.form_fill_args(updates=updates)
        view = navigate_to(self, 'Edit')
        changed = view.form.fill(form_fill_args)

        if changed and not cancel:  # save button won't be enabled if nothing was changed
            view.save.click()
        else:
            view.cancel.click()

        # redirects to details if edited from there
        view = self.create_view(AnalysisProfileDetailsView, override=updates)
        assert view.is_displayed

        view.flash.assert_success_message(
            'Edit of Analysis Profile "{}" was cancelled by the user'.format(self.name)
            if cancel or not changed
            else 'Analysis Profile "{}" was saved'.format(updates.get('name', self.name)))

    def delete(self, cancel=False):
        """Delete self via details page"""
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select("Delete this Analysis Profile",
                                               handle_alert=not cancel)
        view = self.create_view(
            AnalysisProfileDetailsView if cancel else AnalysisProfileAllView)
        view.flush_widget_cache()
        assert view.is_displayed
        if not cancel:
            view.flash.assert_success_message('Analysis Profile "{}": Delete successful'
                                              .format(self.description))
        else:
            assert view.flash.messages == []

    def copy(self, new_name=None, cancel=False):
        """Copy the Analysis Profile"""
        # Create a new object to return in addition to running copy in the UI
        # TODO revisit this method when BZ is fixed:
        # https://bugzilla.redhat.com/show_bug.cgi?id=1485953
        profile_args = self.__dict__.copy()
        profile_args['name'] = new_name or self.name + "-copy"
        new_profile = AnalysisProfile(**profile_args)

        # actually run copy in the UI, fill the form
        view = navigate_to(self, 'Copy')
        form_args = self.form_fill_args(updates={'name': new_profile.name})
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
        view.flash.assert_success_message(
            'Add of new Analysis Profile was cancelled by the user'  # yep, not copy specific
            if cancel
            else 'Analysis Profile "{}" was saved'.format(new_profile.name))

        return new_profile

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
        except (NavigationDestinationNotFound, CandidateNotFound):
            return False
        else:
            return True

    def as_fill_value(self):
        """String representation of an Analysis Profile in CFME UI"""
        return self.name

    def form_fill_args(self, updates=None):
        """Build a dictionary of nested tab_forms for assoc_fill from a flat object dictionary
        If updates dictionary is passed, it is used instead of `self`
        This should work for create or update form fill args
        """
        fill_args = {'profile_type': None}  # this can't be set when adding or editing
        for key in ['name', 'description']:
            arg = updates[key] if updates and key in updates else getattr(self, key)
            fill_args[key] = arg

        for key in ['files', 'events', 'registry']:
            data = deepcopy(updates[key] if updates and key in updates else getattr(self, key))
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
            arg = deepcopy(updates[key] if updates and key in updates else getattr(self, key))
            fill_args[key] = {'tab_form': arg}

        return fill_args

    def __str__(self):
        return self.as_fill_value()

    def __enter__(self):
        self.create()

    def __exit__(self, type, value, traceback):
        self.delete()


@navigator.register(AnalysisProfile, 'All')
class AnalysisProfileAll(CFMENavigateStep):
    VIEW = AnalysisProfileAllView
    prerequisite = NavigateToObject(Server, 'Configuration')

    def step(self):
        server_region = self.obj.appliance.server_region_string()
        self.prerequisite_view.accordions.settings.tree.click_path(
            server_region, "Analysis Profiles")


@navigator.register(AnalysisProfile, 'Add')
class AnalysisProfileAdd(CFMENavigateStep):
    VIEW = AnalysisProfileAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        # stupid capitalization inconsistencies, just wait until there's a 3rd option...
        profile_type = self.obj.profile_type if self.obj.profile_type == 'Host' else 'VM'
        self.prerequisite_view.toolbar.configuration.item_select(
            "Add {} Analysis Profile".format(profile_type))


@navigator.register(AnalysisProfile, 'Details')
class AnalysisProfileDetails(CFMENavigateStep):
    VIEW = AnalysisProfileDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        server_region = self.obj.appliance.server_region_string()
        self.prerequisite_view.sidebar.accordions.settings.tree.click_path(
            server_region, "Analysis Profiles", str(self.obj))


@navigator.register(AnalysisProfile, 'Edit')
class AnalysisProfileEdit(CFMENavigateStep):
    VIEW = AnalysisProfileEditView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select("Edit this Analysis Profile")


@navigator.register(AnalysisProfile, 'Copy')
class AnalysisProfileCopy(CFMENavigateStep):
    VIEW = AnalysisProfileCopyView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select(
            'Copy this selected Analysis Profile')
