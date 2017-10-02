from widgetastic_patternfly import FlashMessages, Button, Input
from widgetastic.widget import View, Text, Checkbox
from widgetastic.log import logged

from widgetastic_manageiq import BaseEntitiesView
from cfme.base.login import BaseLoggedInPage


class TopologySearch(View):
    """ Represents search_text control of TopologyView """
    search_text = Input(id="search")
    search_btn = Text('//*[@id="main-content"]/div[2]/div/div[1]/div/div/form/div[2]/button')
    clear_btn = Text('//*[@id="main-content"]/div[2]/div/div[1]/div/div/form/div[1]/div/button')

    def clear_search(self):
        if not self.is_empty:
            self.clear_btn.click()
            self.search_btn.click()

    def search(self, text):
        self.search_text.fill(text)
        self.search_btn.click()

    @property
    @logged(log_result=True)
    def is_empty(self):
        return not bool(self.search_text.value)


class TopologyToolbar(View):
    display_names = Checkbox("Display Names")
    search_box = View.nested(TopologySearch)
    search_box.search_text = Input(name="search")
    refresh = Button("Refresh")


class TopologyEntities(BaseEntitiesView):
    pass


class TopologyView(BaseLoggedInPage):
    """ Represents whole All NetworkProviders page """
    LEGENDS = '//kubernetes-topology-icon'
    ELEMENTS = '//kubernetes-topology-graph//*[name()="g"]'
    LINES = '//kubernetes-topology-graph//*[name()="lines_obj"]'
    DISPLAY_NAME = '|'.join([
        "//*[contains(@class, 'container_topology')]//label[contains(., 'Display Names')]/input",
        '//*[@id="box_display_names"]'])  # [0] is not working on containers topology
    flash = FlashMessages('.//div[@div="flash_msg_div"]/div[@id="flash_text_div" or '
                          'contains(@class, "flash_text_div")]')

    toolbar = View.nested(TopologyToolbar)
    including_entities = View.include(TopologyEntities, use_parent=True)

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Networks', 'Topology'])
