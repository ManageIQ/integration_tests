""" Page functions for Flavor pages


:var list_page: A :py:class:`cfme.web_ui.Region` object describing elements on the list page.
:var details_page: A :py:class:`cfme.web_ui.Region` object describing elements on the detail page.
"""

from cfme.web_ui import Region
from cfme.web_ui.tables import Table, Split


# Page specific locators
list_page = Region(
    locators={
        'flavor_table': Table.create(
            Split('//div[@class="xhdr"]/table/tbody', '//div[@class="objbox"]/table/tbody', 1, 1))
    },
    title='Flavors')


details_page = Region(infoblock_type='detail')
