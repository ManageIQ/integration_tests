import ui_navigate as nav
import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import Quadicon, Region, SplitTable, flash, Form, fill, form_buttons
from utils.pretty import Pretty
from functools import partial
from cfme.web_ui import toolbar as tb
from cfme import web_ui as ui
from xml.sax.saxutils import quoteattr


details_page = Region(infoblock_type='detail')
cfg_btn = partial(tb.select, "Configuration")
pol_btn = partial(tb.select, 'Policy')
output_table = SplitTable(
    ('//*[@id="list_grid"]//table[contains(@class, "hdr")]/tbody', 1),
    ('//*[@id="list_grid"]//table[contains(@class, "obj")]/tbody', 1)
)

edit_tags_form = Form(
    fields=[
        ("select_tag", ui.Select("select#tag_cat")),
        ("select_value", ui.Select("select#tag_add"))
    ])

nav.add_branch(
    'clouds_stacks', {
        'clouds_stack':
        lambda ctx: sel.click(Quadicon(ctx['stack'].name, 'stack'))
    }
)


class Stack(Pretty):
    pretty_attrs = ['name']

    def __init__(self, name=None):
        self.name = name

    def delete(self):
        sel.force_navigate('clouds_stack', context={'stack': self})
        cfg_btn("Remove this Stack from the VMDB", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('The selected Orchestration Stack was deleted')

    def edit_tags(self, tag, value):
        sel.force_navigate('clouds_stack', context={'stack': self})
        pol_btn('Edit Tags', invokes_alert=True)
        fill(edit_tags_form, {'select_tag': tag,
                              'select_value': value},
             action=form_buttons.save)
        flash.assert_success_message('Tag edits were successfully saved')
        sel.force_navigate('clouds_stack', context={'stack': self})
        row = sel.elements("//*[(self::th or self::td) and normalize-space(.)={}]/../.."
                     "//td[img[contains(@src, 'smarttag')]]".format(quoteattr("My Company Tags")))
        tag = sel.text(row).strip()
        assert tag == "Cost Center: Cost Center 001"

    def nav_to_security_group_link(self):
        sel.force_navigate('clouds_stack', context={'stack': self})
        sel.click(details_page.infoblock.element("Relationships", "Security Groups"))

    def nav_to_parameters_link(self):
        sel.force_navigate('clouds_stack', context={'stack': self})
        sel.click(details_page.infoblock.element("Relationships", "Parameters"))

    def nav_to_output_link(self):
        sel.force_navigate('clouds_stack', context={'stack': self})
        sel.click(details_page.infoblock.element("Relationships", "Outputs"))
        cells = {'Key': "WebsiteURL"}
        output_table.click_rows_by_cells(cells, "Key", True)

    def nav_to_resources_link(self):
        sel.force_navigate('clouds_stack', context={'stack': self})
        sel.click(details_page.infoblock.element("Relationships", "Resources"))
