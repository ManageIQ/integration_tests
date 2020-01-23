import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.exceptions import NoSuchElementException
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input

from cfme.base.ui import ConfigurationView
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from widgetastic_manageiq import Calendar
from widgetastic_manageiq import Checkbox
from widgetastic_manageiq import Dropdown
from widgetastic_manageiq import PaginationPane
from widgetastic_manageiq import SummaryFormItem
from widgetastic_manageiq import Table


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


class AWSS3ProtocolEntities(View):
    """ AWS S3 Protocol fields on the shedule configuration page"""
    aws_region = BootstrapSelect(id='log_aws_region')
    aws_username = Input(id='log_userid')
    aws_password = Input(id='log_password')
    aws_confirm_password = Input(id='log_verify')


class OpenstackSwiftProtocolEntities(View):
    """ Openstack Swift Protocol fields on the shedule configuration page"""
    openstack_keystone_version = BootstrapSelect(id='keystone_api_version')
    openstack_region = Input('openstack_region')
    openstack_security_protocol = BootstrapSelect(id='security_protocol')
    openstack_api_port = Input('swift_api_port')
    openstack_username = Input(id='log_userid')
    openstack_password = Input(id='log_password')
    openstack_confirm_password = Input(id='log_verify')


class DatabaseBackupEntities(View):
    """ Database Backup fields on the shedule configuration page """
    backup_type = BootstrapSelect('log_protocol')
    depot_name = Input(id='depot_name')
    uri = Input(id='uri')

    samba_protocol = View.nested(SambaProtocolEntities)
    aws_s3_protocol = View.nested(AWSS3ProtocolEntities)
    openstack_swift_protocol = View.nested(OpenstackSwiftProtocolEntities)


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
    run_type = BootstrapSelect("timer_typ")
    time_zone = BootstrapSelect("time_zone")
    start_date = Calendar("start_date")
    start_hour = BootstrapSelect("start_hour")
    start_minute = BootstrapSelect("start_min")

    # After selecting action_type == automation tasks
    request = Input(name='object_request')
    object_type = BootstrapSelect('target_class')
    object_selection = BootstrapSelect('target_id')


class ScheduleAllView(ConfigurationView):
    """ Shedule All view on the shedule configuration page"""
    toolbar = View.nested(ScheduleToolbar)
    table = Table('//div[@id="main_div"]//table')
    paginator = PaginationPane()

    @property
    def is_displayed(self):
        expected_tree = [
            self.context['object'].appliance.server.zone.region.settings_string,
            'Schedules'
        ]
        return (
            self.in_configuration and
            self.accordions.settings.tree.currently_selected == expected_tree and
            self.title.text == 'Settings Schedules'
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
        expected_tree = [
            self.context['object'].appliance.server.zone.region.settings_string,
            'Schedules',
            self.context['object'].name
        ]
        return (
            self.accordions.settings.tree.currently_selected == expected_tree and
            self.title.text == 'Settings Schedule "{}"'.format(self.context['object'].name)
        )


class ScheduleAddView(ConfigurationView):
    """ Schedule Add item view """
    form = View.nested(ScheduleAddEditEntities)
    add_button = Button('Add')
    cancel_button = Button("Cancel")

    @property
    def is_displayed(self):
        expected_tree = [
            self.context['object'].appliance.server.zone.region.settings_string,
            'Schedules'
        ]
        return (
            self.in_configuration and
            self.accordions.settings.tree.currently_selected == expected_tree and
            self.title.text == 'Adding a new Schedule'
        )


class ScheduleEditView(ConfigurationView):
    """ Schedule edit item view """
    form = View.nested(ScheduleAddEditEntities)
    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel_button = Button("Cancel")

    @property
    def is_displayed(self):
        expected_tree = [
            self.context['object'].appliance.server.zone.region.settings_string,
            'Schedules',
            self.context['object'].name
        ]
        return (
            self.in_configuration and
            self.accordions.settings.tree.currently_selected == expected_tree and
            self.title.text == 'Editing Schedule "{}"'.format(self.context['object'].name)
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
    start_minute = attr.ib(default=None)
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
        form_mapping = {
            'name': updates.get('name'),
            'description': updates.get('description'),
            'active': updates.get('active'),
            'action_type': updates.get('action_type'),
            'run_type': updates.get('run_type'),
            'run_every': updates.get('run_every'),
            'time_zone': updates.get('time_zone'),
            'start_date': updates.get('start_date'),
            'start_hour': updates.get('start_hour'),
            'start_minute': updates.get('start_minute'),
            'database_backup': {
                'depot_name': updates.get('depot_name'),
                'backup_type': updates.get('backup_type'),
                'uri': updates.get('uri'),
            },
            'samba_protocol': {
                'samba_username': updates.get('samba_username'),
                'samba_password': updates.get('samba_password'),
                'samba_password_verify': updates.get('samba_password'),
            },
            'items_analysis': {
                'filter_level1': updates.get('filter_level1'),
                'filter_level2': updates.get('filter_level2'),
            }
        }
        view = navigate_to(self, 'Edit')
        updated = view.form.fill(form_mapping)
        if reset:
            view.reset_button.click()
        if cancel:
            view.cancel_button.click()
        elif updated and not cancel and not reset:
            view.save_button.click()
            view = self.create_view(ScheduleDetailsView, override=updates)
            view.flash.assert_no_error()

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
        view.flash.assert_no_error()

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
        row = view.paginator.find_row_on_pages(view.table, name=self.name)
        row[0].check()
        return view

    @property
    def last_run_date(self):
        view = navigate_to(self.parent, 'All')
        row = view.table.row(name=self.name)
        return row['Last Run Time'].read()

    @property
    def next_run_date(self):
        view = navigate_to(self.parent, 'All')
        row = view.table.row(name=self.name)
        return row['Next Run Time'].read()

    @property
    def exists(self):
        view = navigate_to(self.parent, 'All')
        try:
            view.paginator.find_row_on_pages(view.table, name=self.name)
            return True
        except NoSuchElementException:
            return False


@attr.s
class SystemSchedulesCollection(BaseCollection):
    """ Configure/Configuration/Region/Schedules collection functionality """
    ENTITY = SystemSchedule

    def create(self, name, description, active=True, action_type=None, run_type=None,
               run_every=None, time_zone=None, start_date=None, start_hour=None, start_minute=None,
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
            'start_minute': start_minute
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
        updated = view.form.fill(details)
        if cancel:
            view.cancel_button.click()
        elif updated:
            view.add_button.click()
        view = self.create_view(ScheduleAllView)
        view.flash.assert_message('Schedule "{}" was saved'.format(name))
        schedule = self.instantiate(name, description, active=active, action_type=action_type,
                                   run_type=run_type, run_every=run_type, time_zone=time_zone,
                                   start_date=start_date, start_hour=start_hour,
                                    start_minute=start_minute, filter_level1=filter_level1,
                                   filter_level2=filter_level2, backup_type=backup_type,
                                   depot_name=depot_name, uri=uri, samba_username=samba_username,
                                   samba_password=samba_password)
        return schedule


@navigator.register(SystemSchedulesCollection, 'All')
class ScheduleAll(CFMENavigateStep):
    VIEW = ScheduleAllView
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self, *args, **kwargs):
        server_region = self.appliance.server.zone.region.settings_string
        self.prerequisite_view.accordions.settings.tree.click_path(server_region, "Schedules")


@navigator.register(SystemSchedulesCollection, 'Add')
class ScheduleAdd(CFMENavigateStep):
    VIEW = ScheduleAddView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select("Add a new Schedule")


@navigator.register(SystemSchedule, 'Details')
class ScheduleDetails(CFMENavigateStep):
    VIEW = ScheduleDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        row = self.prerequisite_view.paginator.find_row_on_pages(
            self.prerequisite_view.table, name=self.obj.name)
        row.click()


@navigator.register(SystemSchedule, 'Edit')
class ScheduleEdit(CFMENavigateStep):
    VIEW = ScheduleEditView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select("Edit this Schedule")
