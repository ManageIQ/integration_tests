from functools import partial
from cfme import web_ui as ui
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import accordion, menu, flash, Quadicon, Region, Form, fill, form_buttons
from cfme.web_ui import toolbar as tb
from utils.update import Updateable
from utils.wait import wait_for
from utils import version

lifecycle_btn = partial(tb.select, "Lifecycle")
reload_func = partial(tb.select, "Reload current display")
my_service_tree = partial(accordion.tree, "Services")
details_page = Region(infoblock_type='detail')
cfg_btn = partial(tb.select, "Configuration")
policy_btn = partial(tb.select, "Policy")
download_btn = partial(tb.select, "download_choice")


retirement_form = Form(
    fields=[
        ('retirement_date', {
            version.LOWEST: ui.Calendar('miq_date_1'),
            '5.5': ui.Calendar('retirementDate')}),
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

menu.nav.add_branch(
    'my_services',
    {
        'all_service':
        [
            lambda _: my_service_tree('All Services'),
            {
                'service':
                [lambda ctx: my_service_tree('All Services', ctx['service_name']),
                {'retire_service_on_date': menu.nav.partial(lifecycle_btn, "Set Retirement Date"),
                 'edit_service': menu.nav.partial(cfg_btn, "Edit this Service"),
                 'service_set_ownership': menu.nav.partial(cfg_btn, "Set Ownership"),
                 'service_edit_tags': menu.nav.partial(policy_btn, "Edit Tags"),
                 'reconfigure_service': menu.nav.partial(cfg_btn, "Reconfigure this Service")}]
            }
        ]
    }
)


class MyService(Updateable):
    """Create,Edit and Delete Button Groups

    Args:
        service_name: The name of service to retire.
        vm_name: Name of vm in the service.
        retirement_date: Date to retire service.
    """

    def __init__(self, service_name, vm_name=None):
        self.service_name = service_name
        self.vm_name = vm_name

    def get_detail(self, properties=None):
        """ Gets details from the details infoblock

        Args:
            *ident: An InfoBlock title, followed by the Key name
             e.g. "Relationships", "Images"
        Returns: A string representing the contents of the InfoBlock's value.
        """
        return details_page.infoblock.text(*properties)

    def retire(self):
        sel.force_navigate('service',
                           context={'service_name': self.service_name})
        lifecycle_btn("Retire this Service", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Retirement initiated for 1 Service from the CFME Database')
        wait_time_min = 1
        quadicon = Quadicon(self.vm_name, "vm")
        sel.click(quadicon)
        detail_t = ("Power Management", "Power State")
        wait_for(
            lambda: self.get_detail(properties=detail_t) == "off",
            fail_func=reload_func,
            num_sec=wait_time_min * 120,
            message="wait for service to retire"
        )
        assert(self.get_detail(properties=detail_t) == "off")

    def retire_on_date(self, retirement_date):
        sel.force_navigate('retire_service_on_date',
                           context={'service_name': self.service_name})
        fill(retirement_form, {'retirement_date': retirement_date},
             action=form_buttons.save)
        wait_time_min = 1
        quadicon = Quadicon(self.vm_name, "vm")
        sel.click(quadicon)
        detail_t = ("Power Management", "Power State")
        wait_for(
            lambda: self.get_detail(properties=detail_t) == "off",
            fail_func=reload_func,
            num_sec=wait_time_min * 120,
            message="wait for service to retire"
        )
        assert(self.get_detail(properties=detail_t) == "off")

    def update(self, name, description):
        sel.force_navigate('edit_service',
                           context={'service_name': self.service_name})
        edited_name = self.service_name + "_" + name
        fill(edit_service_form, {'name': edited_name,
                                 'description': description},
             action=form_buttons.save)
        flash.assert_success_message('Service "{}" was saved'.format(edited_name))

    def delete(self, name):
        sel.force_navigate('service',
                           context={'service_name': name})
        cfg_btn("Remove Service from the VMDB", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Service "{}": Delete successful'.format(name))

    def set_ownership(self, owner, group):
        sel.force_navigate('service_set_ownership',
                           context={'service_name': self.service_name})
        fill(set_ownership_form, {'select_owner': owner,
                                  'select_group': group},
             action=form_buttons.save)
        flash.assert_success_message('Ownership saved for selected Service')

    def edit_tags(self, tag, value):
        sel.force_navigate('service_edit_tags',
                           context={'service_name': self.service_name})
        fill(edit_tags_form, {'select_tag': tag,
                              'select_value': value},
             action=form_buttons.save)
        flash.assert_success_message('Tag edits were successfully saved')

    def check_vm_add(self, add_vm_name):
        sel.force_navigate('service',
                           context={'service_name': self.service_name})

        quadicon = Quadicon(add_vm_name, "vm")
        sel.click(quadicon)
        flash.assert_no_errors()

    def reconfigure_service(self):
        sel.force_navigate('reconfigure_service',
                           context={'service_name': self.service_name})

    def download_file(self, extension):
        sel.force_navigate('all_service')
        download_btn("Download as " + extension)
