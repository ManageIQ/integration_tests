from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic_manageiq import Table, BootstrapSelect, BreadCrumb, Text
from widgetastic_patternfly import Dropdown, FlashMessages, BootstrapSwitch,\
    Input, Button, ViewChangeButton, CheckableBootstrapTreeview
from widgetastic.utils import VersionPick, Version
from widgetastic.widget import View
from cfme.base.ui import MySettingsView
from utils.pretty import Pretty
from utils.update import Updateable
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


class SettingToolBar(View):
    configuration = Dropdown('Configuration')


class TimeProfileAddForm(MySettingsView):
    description = Input(id='description')
    scope = BootstrapSelect('profile_type')
    timezone = BootstrapSelect('profile_tz')
    days = BootstrapSwitch(name='all_days')
    hours = BootstrapSwitch(name='all_hours')
    save_button = Button(VersionPick({Version.lowest(): 'Add',
                                      '5.8': 'Save'}))
    save_edit_button = Button(VersionPick({Version.lowest(): 'Save changes',
                                           '5.8': 'Save'}))
    cancel_button = Button('Cancel')
    table = Table("//div[@id='main_div']//table")


class TimeprofileAddEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h3')


class TimeProfileAddFormView(MySettingsView):
    timeprofile_form = View.nested(TimeProfileAddForm)
    entities = View.nested(TimeprofileAddEntities)


class Timeprofile(Updateable, Navigatable):
    def __init__(self, description=None, scope=None, days=None, hours=None, timezone=None,
                 appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.description = description
        self.scope = scope
        self.days = days
        self.hours = hours
        self.timezone = timezone

    def create(self, cancel=False):
        view = navigate_to(self, 'Add')
        new_timeprofile = view.timeprofile_form.fill({
            'description': self.description,
            'scope': self.scope,
            'days': self.days,
            'hours': self.hours,
            'timezone': self.timezone,
        })

        if not cancel:
            view.timeprofile_form.save_button.click()
            end = "saved" if self.appliance.version > '5.7' else "added"
            FlashMessages('Time Profile "{}" was {}'.format(self.description, end))
        return new_timeprofile

    def update(self, updates):
        view = navigate_to(self, 'Edit')
        row = view.timeprofile_form.table.row()
        row[1].click()
        changed = view.timeprofile_form.fill({
            'scope': updates.get('scope'),
        })
        if changed:
            view.timeprofile_form.save_edit_button.click()
            view.flash.assert_message(
                'Time Profile "{}" was saved'.format(updates.get('description', self.description)))

    def copy(self):
        view = navigate_to(self, 'Copy')
        new_timeprofile = Timeprofile(description=self.description + "copy",
                                      scope=self.scope)
        changed = view.timeprofile_form.fill({
            'description': self.description + "copy",
            'scope': self.scope,
        })

        if changed:
            view.timeprofile_form.save_button.click()
            end = "saved" if self.appliance.version > '5.7' else "added"
            FlashMessages('Time Profile "{}" was {}'.format(self.description, end))
        return new_timeprofile

    def delete(self):
        view = navigate_to(self, 'Delete')
        rows = view.tables
        for row in rows:
            if row.Description.text == self.description:
                row[0].check()
        view.configuration.item_select("Delete selected Time Profiles", handle_alert=True)


@navigator.register(Timeprofile, 'All')
class TimeprofileAll(CFMENavigateStep):
    VIEW = MySettingsView
    prerequisite = NavigateToAttribute('appliance.server', 'MySettings')

    def step(self):
        self.view.tabs.time_profile.select()


@navigator.register(Timeprofile, 'Add')
class TimeprofileNew(CFMENavigateStep):
    VIEW = TimeProfileAddFormView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.configuration.item_select("Add a new Time Profile")


@navigator.register(Timeprofile, 'Edit')
class TimeprofileEdit(CFMENavigateStep):
    VIEW = TimeProfileAddFormView
    prerequisite = NavigateToSibling('All')


@navigator.register(Timeprofile, 'Copy')
class TimeprofileCopy(CFMENavigateStep):
    VIEW = TimeProfileAddFormView
    prerequisite = NavigateToSibling('All')

    def step(self):
        rows = self.prerequisite_view.tables
        rows[0][0].check()
        self.prerequisite_view.configuration.item_select("Copy selected Time Profile")


@navigator.register(Timeprofile, 'Delete')
class TimeprofileDelete(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')
    VIEW = MySettingsView
    prerequisite = NavigateToAttribute('appliance.server', 'MySettings')

    def step(self):
        self.view.tabs.time_profile.select()


class Visual(Updateable, Navigatable):
    @property
    def grid_view_limit(self):
        view = navigate_to(self, 'Items')
        return view.grid_view.read()

    @grid_view_limit.setter
    def grid_view_limit(self, value):
        view = navigate_to(self, 'Items')
        if view.grid_view.fill(value):
            view.save.click()

    @property
    def tile_view_limit(self):
        view = navigate_to(self, 'Items')
        return view.title_view.read()

    @tile_view_limit.setter
    def tile_view_limit(self, value):
        view = navigate_to(self, 'Items')
        if view.title_view.fill(value):
            view.save.click()

    @property
    def list_view_limit(self):
        view = navigate_to(self, 'Items')
        return view.list_view.read()

    @list_view_limit.setter
    def list_view_limit(self, value):
        view = navigate_to(self, 'Items')
        if view.list_view.fill(value):
            view.save.click()

    @property
    def report_view_limit(self):
        view = navigate_to(self, 'Items')
        return view.reports.read()

    @report_view_limit.setter
    def report_view_limit(self, value):
        view = navigate_to(self, 'Items')
        if view.reports.fill(value):
            view.save.click()

    @property
    def login_page(self):
        view = navigate_to(self, 'Start')
        return view.show_at_login.read()

    @login_page.setter
    def login_page(self, value):
        view = navigate_to(self, 'Start')
        if view.show_at_login.fill(value):
            view.save.click()

    @property
    def infra_provider_quad(self):
        view = navigate_to(self, 'Quadicons')
        return view.infra_provider_quad.read()

    @infra_provider_quad.setter
    def infra_provider_quad(self, value):
        view = navigate_to(self, 'Quadicons')
        if view.infra_provider_quad.fill(value):
            view.save.click()

    @property
    def host_quad(self):
        view = navigate_to(self, 'Quadicons')
        return view.host_quad.read()

    @host_quad.setter
    def host_quad(self, value):
        view = navigate_to(self, 'Quadicons')
        if view.host_quad.fill(value):
            view.save.click()

    @property
    def datastore_quad(self):
        view = navigate_to(self, 'Quadicons')
        return view.datastore_quad.read()

    @datastore_quad.setter
    def datastore_quad(self, value):
        view = navigate_to(self, 'Quadicons')
        if view.datastore_quad.fill(value):
            view.save.click()

    @property
    def vm_quad(self):
        view = navigate_to(self, 'Quadicons')
        return view.vm_quad.read()

    @vm_quad.setter
    def vm_quad(self, value):
        view = navigate_to(self, 'Quadicons')
        if view.vm_quad.fill(value):
            view.save.click()

    @property
    def template_quad(self):
        view = navigate_to(self, 'Quadicons')
        return view.template_quad.read()

    @template_quad.setter
    def template_quad(self, value):
        view = navigate_to(self, 'Quadicons')
        if view.template_quad.fill(value):
            view.save.click()

    @property
    def cloud_provider_quad(self):
        view = navigate_to(self, 'Quadicons')
        return view.cloud_provider_quad.read()

    @cloud_provider_quad.setter
    def cloud_provider_quad(self, value):
        view = navigate_to(self, 'Quadicons')
        if view.cloud_provider_quad.fill(value):
            view.save.click()

    @property
    def timezone(self):
        view = navigate_to(self, 'Display')
        return view.time_zone.read()

    @timezone.setter
    def timezone(self, value):
        view = navigate_to(self, 'Display')
        if view.time_zone.fill(value):
            view.save.click()


visual = Visual()


class VisualItemForm(MySettingsView):
    grid_view = BootstrapSelect("perpage_grid")
    title_view = BootstrapSelect("perpage_title")
    list_view = BootstrapSelect("perpage_list")
    reports = BootstrapSelect("perpage_reports")
    save = Button("Save")
    reset = Button("Reset")


class VisualStartPageForm(MySettingsView):
    show_at_login = BootstrapSelect("start_page")
    save = Button("Save")
    reset = Button("Reset")


class VisualQuadiconsForm(MySettingsView):
    infra_provider = BootstrapSwitch("quadicons_ems")
    cloud_provider_quad = BootstrapSwitch("quadicons_ems_cloud")
    host_quad = BootstrapSwitch("quadicons_host")
    datastore_quad = BootstrapSwitch("quadicons_storage")
    vm_quad = BootstrapSwitch("quadicons_vm")
    template_quad = BootstrapSwitch("quadicons_miq_template")
    long_text = BootstrapSelect("quad_truncate")
    save = Button("Save")
    reset = Button("Reset")


class VisualDisplayForm(MySettingsView):
    chart_theme = BootstrapSelect("display_reporttheme")
    time_zone = BootstrapSelect("display_timezone")
    save = Button("Save")
    reset = Button("Reset")


@navigator.register(Visual, 'All')
class VisualAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'MySettings')
    VIEW = MySettingsView

    def step(self):
        self.view.tabs.visual_all.select()


@navigator.register(Visual, 'Items')
class VisualItems(CFMENavigateStep):
    prerequisite = NavigateToSibling("All")
    VIEW = VisualItemForm


@navigator.register(Visual, 'Start')
class VisualStart(CFMENavigateStep):
    prerequisite = NavigateToSibling("All")
    VIEW = VisualStartPageForm

    def step(self):
        self.prerequisite_view.tabs.visual_all.select()


@navigator.register(Visual, 'Quadicons')
class VisualQuadicons(CFMENavigateStep):
    prerequisite = NavigateToSibling("All")
    VIEW = VisualQuadiconsForm

    def step(self):
        self.prerequisite_view.tabs.visual_all.select()


@navigator.register(Visual, 'Display')
class VisualDisplay(CFMENavigateStep):
    prerequisite = NavigateToSibling("All")
    VIEW = VisualDisplayForm

    def step(self):
        self.prerequisite_view.tabs.visual_all.select()


class DefaultFilterForm(View):
    tree = CheckableBootstrapTreeview('df_treebox')
    save = Button('Save')
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')


class DefaultFilter(Updateable, Pretty, Navigatable):

    pretty_attrs = ['name', 'filters']

    def __init__(self, name=None, filters=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.filters = filters or []

    def update(self, updates, expect_success=True):
        navigate_to(self, 'All')
        view = navigate_to(self, 'Edit')
        view.tree.fill(updates.get('filters'))
        view.save.click()
        if expect_success:
            view.flash.assert_message('Default Filters saved successfully')


@navigator.register(DefaultFilter, 'All')
class DefaultFilterAll(CFMENavigateStep):
    VIEW = MySettingsView
    prerequisite = NavigateToAttribute('appliance.server', 'MySettings')

    def step(self):
        self.view.tabs.default_filter.select()


@navigator.register(DefaultFilter, 'Edit')
class DefaultFilterEdit(CFMENavigateStep):
    VIEW = DefaultFilterForm
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.tabs.default_filter.select()


class DefaultViewForm(View):
    save = Button("Save")


class DefaultView(Updateable, Navigatable):
    # Basic class for navigation to default views screen
    def __init__(self, appliance=None):
        Navigatable.__init__(self, appliance=appliance)

    @classmethod
    def set_default_view(cls, button_group_names, defaults, fieldset=None):

        """This function sets default views for the objects.
        Args:
            * button_group_names: either the name of the button_group_name
                                  or list of the button groups to set the
                                  default view for.
            * default: the default view to set. in case that button_group_names
                       is a list, you can either set 1 view and it'll be set
                       for all the button_group_names or you can use a list
                       (default view per button_group_name).
        Examples:
            * set_default_view('Containers Providers, 'List View') --> set
              'List View' default view to 'Containers Providers'
            * set_default_view(['Images', 'Projects', 'Routes'], 'Tile View')
              --> set 'Tile View' default view to 'Images', 'Projects' and 'Routes'
            * set_default_view(['Images', 'Projects', 'Routes'],
                               ['Tile View', 'Tile View', 'Grid View']) -->
              set 'Tile View' default view to 'Images' and 'Projects' and 'Grid View'
              default view to 'Routes'
        """

        if not isinstance(button_group_names, (list, tuple)):
            button_group_names = [button_group_names]
        if not isinstance(defaults, (list, tuple)):
            defaults = [defaults] * len(button_group_names)
        assert len(button_group_names) == len(defaults)

        is_something_changed = False
        for button_group_name, default in zip(button_group_names, defaults):
            bg = ViewChangeButton(button_group_name, title=fieldset)
            view = navigate_to(cls, 'Edit')
            if bg.active != default:
                bg.choose(default)
                is_something_changed = True

        if is_something_changed:
            view.save.click()

    @classmethod
    def get_default_view(cls, button_group_name, fieldset=None):
        bg = ViewChangeButton(button_group_name, title=fieldset)
        navigate_to(cls, 'All')
        return bg.active


@navigator.register(DefaultView, 'All')
class DefaultViewAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'MySettings')
    VIEW = MySettingsView

    def step(self):
        self.view.tabs.default_views.select()


@navigator.register(DefaultView, 'Edit')
class DefaultViewEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling("All")
    VIEW = DefaultViewForm

    def step(self):
        self.view.tabs.default_views.select()
