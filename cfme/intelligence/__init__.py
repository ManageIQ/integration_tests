import cfme.web_ui.accordion as accordion
import cfme.web_ui.menu # to load menu nav
from functools import partial
import ui_navigate as nav

rates_page = __name__ + ".rates"
assignments_page = __name__ + ".assignments"

nav.add_branch('chargeback',
               {rates_page: partial(accordion.click, "Rates"),
                assignments_page: partial(accordion.click, "Assignments")})


