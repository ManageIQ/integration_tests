import ui_navigate as nav
import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import Quadicon, Region, SplitTable
from utils.pretty import Pretty

details_page = Region(infoblock_type='detail')
output_table = SplitTable(
    ('//*[@id="list_grid"]//table[contains(@class, "hdr")]/tbody', 1),
    ('//*[@id="list_grid"]//table[contains(@class, "obj")]/tbody', 1)
)

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
