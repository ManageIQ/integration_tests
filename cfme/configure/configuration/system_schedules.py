import attr

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic_manageiq import (SummaryFormItem, Table, Dropdown, PaginationPane, Checkbox,
                                  Calendar)
from widgetastic_patternfly import Input, BootstrapSelect, Button
from widgetastic.widget import View

from cfme.base.ui import ConfigurationView
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable


# =========================== System Schedule ==================================


class ScheduleToolbar(View):
    """ Toolbar on the shedule configuration page """
    configuration = Dropdown('Configuration')


class ItemsAnalysisEntities(View):
    """ Analysis fields on the shedule configuration page """
    filter_level1 = BootstrapSelect("filter_typ")
    filter_level2 = BootstrapSelect("filter_value")


class SambaProtocolEntities(View):
    """ Samba Protocol fields on the shedule configuration page """
    samba_username = Input(id='log_userid')
    samba_password = Input(id='log_password')
    samba_confirm_password = Input(id='log_verify')


class DatabaseBackupEntities(View):
    """ Database Backup fields on the shedule configuration page """
    backup_type = BootstrapSelect('log_protocol')
    depot_name = Input(id='depot_name')
    uri = Input(id='uri')

    samba_protocol = View.nested(SambaProtocolEntities)


class ScheduleAddEditEntities(View):
    """ Schedule configuration fields on the shedule configuration page """
    # Basic Information
    name = Input(name="name")
    description = Input(name="description")
    active = Checkbox("enabled")
    # Action type
    action_type = BootstrapSelect('action_typ')
    items_analysis = View.nested(ItemsAnalysisEntities)
    database_backup = View.nested(DatabaseBackupEntities)
    # Timer
    run_timer = BootstrapSelect("timer_typ")
    time_zone = BootstrapSelect("time_zone")
    starting_date = Calendar("start_date")
    hour = BootstrapSelect("start_hour")
    minute = BootstrapSelect("start_min")
    # Buttons
    cancel_button = Button("Cancel")


class ScheduleAllView(ConfigurationView):
    """ Shedule All view on the shedule configuration page"""
    toolbar = View.nested(ScheduleToolbar)
    table = Table(locator="//div[@id='records_div']/table")
    paginator = PaginationPane()

    @property
    def is_displayed(self):
        return (
            self.in_configuration and
            self.accordions.settings.tree.currently_selected == [
                self.context['object'].zone.region.settings_string,
                'Schedules'] and
            self.title == 'Settings Schedules'
        )


class ScheduleDetailsView(ConfigurationView):
    """ Schedule details page view """
    toolbar = View.nested(ScheduleToolbar)

    description = SummaryFormItem('', 'Description')
    active = SummaryFormItem('', 'Active')
    action = SummaryFormItem('', 'Action')
    filter = SummaryFormItem('', 'Filter')

    run_at = SummaryFormItem('', 'Run At')
    last_run_time = SummaryFormItem('', 'Last Run Time')
    next_run_time = SummaryFormItem('', 'Next Run Time')
    zone = SummaryFormItem('', 'Zone')

    @property
    def is_displayed(self):
        return (
            self.in_configuration and
            self.accordions.settings.tree.currently_selected == [
                self.context['object'].zone.region.settings_string,
                'Schedules',
                self.context['object'].name] and
            self.title == 'Settings Schedule "{}"'.format(self.context['object'].name)
        )


class ScheduleAddView(ScheduleAddEditEntities):
    """ Schedule Add item view """
    add_button = Button('Add')

    @property
    def is_displayed(self):
        return (
            self.in_configuration and
            self.accordions.settings.tree.currently_selected == [
                self.context['object'].zone.region.settings_string,
                'Schedules'] and
            self.title == 'Adding a new Schedule'
        )


class ScheduleEditView(ScheduleAddEditEntities):
    """ Schedule edit item view """
    save_button = Button('Save')
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.in_configuration and
            self.accordions.settings.tree.currently_selected == [
                self.context['object'].zone.region.settings_string,
                'Schedules',
                self.context['object'].name] and
            self.title == 'Edit Schedule "{}"'.format(self.context['object'].name)
        )


@attr.s
class SystemSchedule(BaseEntity, Updateable, Pretty):
    """ Configure/Configuration/Region/Schedules functionality

        Update, Delete functionality.

        Args:
            name: Schedule's name.
            description: Schedule description.
            active: Whether the schedule should be active (default `True`)
            action: Action type
            run_type: Once, Hourly, Daily, ...
            run_every: If `run_type` is not Once, then you can specify how often it should be run.
            time_zone: Time zone selection.
            start_date: Specify start date (mm/dd/yyyy or datetime.datetime()).
            start_hour: Starting hour
            start_min: Starting minute.
            # Analysis params
            filter_level1: first filter value
            filter_level2: second filter value
            # Database backup params
            backup_type: backup type
            depot_name: depot name
            uri: depot uri
            # Samba backup config
            samba_username: samba username
            samba_password: samba password
    """
    # Basic
    name = attr.ib()
    description = attr.ib()
    active = attr.ib(default=True)
    action_type = attr.ib(default=None)
    run_type = attr.ib(default='Once')
    run_every = attr.ib(default=None)
    time_zone = attr.ib(default=None)
    start_date = attr.ib(default=None)
    start_hour = attr.ib(default=None)
    start_min = attr.ib(default=None)
    # Analysis
    filter_level1 = attr.ib(default=None)
    filter_level2 = attr.ib(default=None)
    # Database backup
    backup_type = attr.ib(default=None)
    depot_name = attr.ib(default=None)
    uri = attr.ib(default=None)
    # Samba backup config
    samba_username = attr.ib(default=None)
    samba_password = attr.ib(default=None)

    def update(self, updates, reset=False, cancel=False):
        """ Modify an existing schedule with informations from this instance.

        Args:
            updates: Dict with fields to be updated
            reset: Reset changes, True if reset should be done
            cancel: Whether to click on the cancel button to interrupt the editation.

        """
        view = navigate_to(self, 'Edit')
        updated = view.fill(updates)
        if reset:
            view.reset_button.click()
            flash_message = 'All changes have been reset'
        if cancel:
            view.cancel_button.click()
            flash_message = 'Edit of Schedule "{}" was cancelled by the user'.format(self.name)
        elif updated:
            view.save_button.click()
            view = self.create_view(ScheduleDetailsView, override=updates)
            name = updates.get('name') if updates.get('name') else self.name
            flash_message = 'Schedule "{}" was saved'.format(name)
        view.flash.assert_message(flash_message)

    def delete(self, cancel=False):
        """ Delete the schedule represented by this object.

        Calls the class method with the name of the schedule taken out from the object.

        Args:
            cancel: Whether to click on the cancel button in the pop-up.
        """
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Delete this Schedule from the Database',
                                               handle_alert=(not cancel))
        view = self.create_view(ScheduleAllView)
        view.flash.assert_message('Schedule "{}": Delete successful'.format(self.description))

    def enable(self):
        """ Enable the schedule via table checkbox and Configuration menu. """
        view = self.select()
        view.toolbar.configuration.item_select("Enable the selected Schedules")

    def disable(self):
        """ Enable the schedule via table checkbox and Configuration menu. """
        view = self.select()
        view.toolbar.configuration.item_select("Disable the selected Schedules")

    def select(self):
        """ Select the checkbox for current schedule """
        view = navigate_to(self.parent, 'All')
        row = view.find_row_on_pages(view.table, name=self.name)
        row.check()
        return view

    @property
    def last_run_date(self):
        view = navigate_to(self.parent, 'All')
        row = view.table.row(name=self.name)
        return row['Last Run Time'].read()


@attr.s
class SystemSchedulesCollection(BaseCollection):
    """ Configure/Configuration/Region/Schedules collection functionality """
    ENTITY = SystemSchedule

    def create(self, name, description, active=True, action_type=None, run_type=None,
               run_every=None, time_zone=None, start_date=None, start_hour=None, start_min=None,
               filter_level1=None, filter_level2=None, backup_type=None, depot_name=None, uri=None,
               samba_username=None, samba_password=None, cancel=False):
        """ Create a new schedule from the informations stored in the object.

        Args:
            cancel: Whether to click on the cancel button to interrupt the creation.
        """
        details = {
            'name': name,
            'description': description,
            'active': active,
            'action_type': action_type,
            'run_type': run_type,
            'run_every': run_every,
            'time_zone': time_zone,
            'start_date': start_date,
            'start_hour': start_hour,
            'start_min': start_min
        }
        if action_type == 'Database Backup':
            details.update({
                'database_backup': {
                    'depot_name': depot_name,
                    'backup_type': backup_type,
                    'uri': uri
                }
            })
            if backup_type == 'Samba':
                details['database_backup'].update({
                    'samba_protocol': {
                        'samba_username': samba_username,
                        'samba_password': samba_password,
                        'samba_password_verify': samba_password
                    }
                })
        else:
            details.update({
                'items_analysis': {
                    'filter_level1': filter_level1,
                    'filter_level2': filter_level2
                }
            })
        view = navigate_to(self, 'Add')
        updated = view.fill(details)
        if cancel:
            view.cancel_button.click()
        elif updated:
            view.add_button.click()
        view = self.create_view(ScheduleAllView)
        view.flash.assert_message('Schedule "{}" was saved'.format(name))
        shedule = self.instantiate(name, description, active=active, action_type=action_type,
                                   run_type=run_type, run_every=run_type, time_zone=time_zone,
                                   start_date=start_date, start_hour=start_hour,
                                   start_min=start_min, filter_level1=filter_level1,
                                   filter_level2=filter_level2, backup_type=backup_type,
                                   depot_name=depot_name, uri=uri, samba_username=samba_username,
                                   samba_password=samba_password)
        return shedule


@navigator.register(SystemSchedulesCollection, 'All')
class ScheduleAll(CFMENavigateStep):
    VIEW = ScheduleAllView
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self):
        server_region = self.appliance.server.zone.region.settings_string
        self.prerequisite_view.accordions.settings.tree.click_path(server_region, "Schedules")


@navigator.register(SystemSchedulesCollection, 'Add')
class ScheduleAdd(CFMENavigateStep):
    VIEW = ScheduleAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select("Add a new Schedule")


@navigator.register(SystemSchedule, 'Details')
class ScheduleDetails(CFMENavigateStep):
    VIEW = ScheduleDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self):
        row = self.prerequisite_view.paginator.find_row_on_pages(
            self.prerequisite_view.table, name=self.obj.name)
        row.click()


@navigator.register(SystemSchedule, 'Edit')
class ScheduleEdit(CFMENavigateStep):
    VIEW = ScheduleEditView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select("Edit this Schedule")
