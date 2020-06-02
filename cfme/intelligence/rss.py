from cfme.common import BaseLoggedInPage
from widgetastic_manageiq import Table


class RSSView(BaseLoggedInPage):

    table = Table('//div[@id="tab_div"]/table')

    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user
            and self.navigation.currently_selected == ['Overview', 'RSS']
        )
