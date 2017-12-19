from widgetastic.utils import ParametrizedLocator
from widgetastic.widget import View, Text, Checkbox, ParametrizedView
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_patternfly import Button, Input

from cfme.base.login import BaseLoggedInPage


class TopologySearch(View):
    """ Represents search_text control of TopologyView """
    search_text = Input(id='search')
    search_text_new = Input(id='search_topology')
    search_btn = Text('//*[@id="main-content"]/div[2]/div/div[1]/div/div/form/div[2]/button')
    search_btn_new = Text('//*[@id="miq-toolbar-menu"]/miq-toolbar-menu/'
                          'div/div/ng-repeat/div/form/div[2]/button')
    clear_btn = Text('//*[@id="main-content"]/div[2]/div/div[1]/div/div/form/div[1]/div/button')
    clear_btn_new = Text('//*[@id="miq-toolbar-menu"]/miq-toolbar-menu/div/'
                         'div/ng-repeat/div/form/div[1]/div/button[2]')

    def clear_search(self):
        if self.browser.product_version < '5.9':
            self.clear_btn.click()
        else:
            self.clear_btn_new.click()
        self.search("")

    def search(self, text):
        if self.browser.product_version < '5.9':
            self.search_text.fill(text)
            self.search_btn.click()
        else:
            self.search_text_new.fill(text)
            self.search_btn_new.click()


class TopologyToolbar(View):
    display_names = Checkbox("Display Names")
    search_box = View.nested(TopologySearch)
    search_box.search_text = Input(name="search")
    refresh = Button("Refresh")


class TopologyEntities(BaseEntitiesView):
    pass


class TopologyView(BaseLoggedInPage):
    """ Represents whole All NetworkProviders page """
    ELEMENTS = '//kubernetes-topology-graph//*[name()="g"]'
    LINES = '//kubernetes-topology-graph//*[name()="lines_obj"]'
    DISPLAY_NAME = '|'.join([
        "//*[contains(@class, 'container_topology')]//label[contains(., 'Display Names')]/input",
        '//*[@id="box_display_names"]'])  # [0] is not working on containers topology

    toolbar = View.nested(TopologyToolbar)
    including_entities = View.include(TopologyEntities, use_parent=True)

    @ParametrizedView.nested
    class legend(ParametrizedView):  # noqa
        PARAMETERS = ('name', )
        ALL_LEGENDS = './/div[@id="main-content"]//kubernetes-topology-icon'
        el = Text(
            ParametrizedLocator('{}//label[normalize-space(.)={@name|quote}]'.format(ALL_LEGENDS)))

        @property
        def is_enabled(self):
            return 'active' in self.el.get_attribute('class')

        def enable(self):
            if not self.is_enabled:
                self.el.click()

        def disable(self):
            if self.is_enabled:
                self.el.click()

        @classmethod
        def all(cls, browser):
            return [(browser.text(e), ) for e in browser.elements(cls.ALL_LEGENDS)]
