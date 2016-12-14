from functools import partial

from navmazing import NavigateToAttribute, NavigateToSibling

from cfme import web_ui as ui
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import \
    accordion, flash, Quadicon, InfoBlock, Form, fill, form_buttons, match_location, toolbar as tb
from utils import version
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from utils.log import logger
from utils.update import Updateable
from utils.wait import wait_for

cfg_btn = partial(tb.select, "Configuration")
pol_btn = partial(tb.select, "Policy")
life_btn = partial(tb.select, "Lifecycle")
down_btn = partial(tb.select, "download_choice")

my_service_tree = partial(accordion.tree, "Services")

match_page = partial(match_location, controller='service', title='Services')

retirement_form = Form(
    fields=[
        ('retirement_date', ui.Calendar('retirementDate')),
        ('retirement_warning', ui.Select("select#retirement_warn"))
    ])

edit_service_form = Form(
    fields=[
        ("name", ui.Input("name")),
        ("description", ui.Input("description"))
    ])

set_ownership_form = Form(
    fields=[
        ("select_owner", ui.Select("select#user_name")),
        ("select_group", ui.Select("select#group_name"))
    ])

edit_tags_form = Form(
    fields=[
        ("select_tag", ui.Select("select#tag_cat")),
        ("select_value", ui.Select("select#tag_add"))
    ])


class MyService(Updateable, Navigatable):
    """Create,Edit and Delete Button Groups

    Args:
        service_name: The name of service to retire.
        vm_name: Name of vm in the service.
        retirement_date: Date to retire service.
    """

    def __init__(self, service_name, vm_name=None, appliance=None):
        self.service_name = service_name
        self.vm_name = vm_name
        Navigatable.__init__(self, appliance=appliance)

    def get_detail(self, properties=None, icon_href=False):
        """ Gets details from the details infoblock

        Args:
            *properties: An InfoBlock title, followed by the Key name e.g. "Relationships", "Images"
            icon_href: Boolean indicating to return icon_href instead of text
        Returns: A string representing the contents of the InfoBlock's value.
        """
        navigate_to(self, 'Details')
        if icon_href:
            return InfoBlock.icon_href(*properties)
        else:
            return InfoBlock.text(*properties)

    def wait_for_vm_retire(self):
        """ Waits for self.vm_name to go to the off state and returns state

        Args:
        Returns: A string representing the VM state
        """
        def get_vm_details():
            power_state = InfoBlock.text('Power Management', 'Power State')
            logger.debug('Service VM power state: {}'.format(power_state))
            if power_state == 'unknown':
                # The VM power state is unknown, check lifecycle instead of power
                retire_state = InfoBlock.text('Lifecycle', 'Retirement state')
                return retire_state == 'Retired'
            else:
                # VM power is a known state, use it
                return power_state == 'off'

        quadicon = Quadicon(self.vm_name, "vm")
        sel.click(quadicon)

        wait_for(
            get_vm_details,
            fail_func=tb.refresh,
            num_sec=120 * 60,
            delay=10,
            message="Service VM power off wait"
        )
        return InfoBlock.text('Power Management', 'Power State')

    def retire(self):
        navigate_to(self, 'Details')
        life_btn("Retire this Service", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Retirement initiated for 1 Service from the CFME Database')
        # wait for service to retire
        wait_for(
            lambda: self.get_detail(properties=('Lifecycle', 'Retirement State')) == 'Retiring',
            fail_func=tb.refresh,
            num_sec=5 * 60,
            delay=3,
            message='Service Retirement wait'
        )
        # wait for any vms to shutdown, this method leaves the page on the VM details
        vm_state = self.wait_for_vm_retire()
        assert vm_state in ['off', 'unknown']

    def retire_on_date(self, retirement_date):
        navigate_to(self, 'SetRetirement')
        fill(retirement_form, {'retirement_date': retirement_date},
             action=form_buttons.save)
        navigate_to(self, 'Details')
        wait_for(
            lambda: InfoBlock.text('Lifecycle', 'Retirement State') == 'Retiring',
            fail_func=tb.refresh,
            num_sec=5 * 60,
            delay=5,
            message='Service Retirement'
        )
        # wait for any vms to shutdown, this method leaves the page on the VM details
        vm_state = self.wait_for_vm_retire()
        assert vm_state in ['off', 'unknown']

    def update(self, updates):
        navigate_to(self, 'Edit')
        updated_name = updates.get('service_name', self.service_name + '_edited')
        updated_description = updates.get('description', 'Updated description')
        fill(edit_service_form, {'name': updated_name,
                                 'description': updated_description},
             action=form_buttons.angular_save)
        if flash.assert_success_message('Service "{}" was saved'.format(updated_name)):
            self.service_name = updated_name

    def delete(self):
        navigate_to(self, 'Details')
        cfg_btn(
            version.pick({
                version.LOWEST: 'Remove Service from the VMDB',
                '5.7': 'Remove Service'}),
            invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Service "{}": Delete successful'.format(self.service_name))

    def set_ownership(self, owner, group):
        navigate_to(self, 'SetOwnership')
        fill(set_ownership_form, {'select_owner': owner,
                                  'select_group': group},
             action=form_buttons.save)
        flash.assert_success_message('Ownership saved for selected Service')

    def edit_tags(self, tag, value):
        navigate_to(self, 'EditTags')
        fill(edit_tags_form, {'select_tag': tag,
                              'select_value': value},
             action=form_buttons.save)
        flash.assert_success_message('Tag edits were successfully saved')

    def check_vm_add(self, add_vm_name):
        navigate_to(self, 'Details')
        quadicon = Quadicon(add_vm_name, "vm")
        sel.click(quadicon)
        flash.assert_no_errors()

    def reconfigure_service(self):
        navigate_to(self, 'Reconfigure')

    def download_file(self, extension):
        navigate_to(self, 'All')
        down_btn("Download as " + extension)


@navigator.register(MyService, 'All')
class MyServiceAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def am_i_here(self):
        return match_page(summary='All Services')

    def step(self, *args, **kwargs):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Services', 'My Services')(None)

    def resetter(self, *args, **kwargs):
        my_service_tree().click_path('All Services')
        tb.refresh()


@navigator.register(MyService, 'Details')
class MyServiceDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return match_page(summary='Service "{}"'.format(self.obj.service_name))

    def step(self, *args, **kwargs):
        logger.debug('Clicking tree for service: {}'.format(self.obj.service_name))
        my_service_tree().click_path('All Services', self.obj.service_name)

    def resetter(self, *args, **kwargs):
        tb.refresh()


@navigator.register(MyService, 'Edit')
class MyServiceEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        cfg_btn('Edit this Service')


@navigator.register(MyService, 'SetOwnership')
class MyServiceSetOwnership(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        cfg_btn('Set Ownership')


@navigator.register(MyService, 'EditTags')
class MyServiceEditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        pol_btn('Edit Tags')


@navigator.register(MyService, 'SetRetirement')
class MyServiceSetRetirement(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        life_btn('Set Retirement Date')


@navigator.register(MyService, 'Reconfigure')
class MyServiceReconfigure(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        cfg_btn('Reconfigure this Service')
