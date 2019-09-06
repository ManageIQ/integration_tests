import importscan
import sentaku
from widgetastic.utils import deflatten_dict
from widgetastic.utils import Parameter
from widgetastic.utils import ParametrizedLocator
from widgetastic.utils import ParametrizedString
from widgetastic.widget import ParametrizedView
from widgetastic.widget import Select
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Input

from cfme.common import Taggable
from cfme.exceptions import ItemNotFound
from cfme.utils.appliance import Navigatable
from cfme.utils.update import Updateable
from cfme.utils.wait import TimedOutError


class ServiceCatalogs(Navigatable, Taggable, Updateable, sentaku.modeling.ElementMixin):
    """
        Service Catalogs main class to context switch between ui
        and ssui. All the below methods are implemented in both ui
        and ssui side .
    """

    order = sentaku.ContextualMethod()
    add_to_shopping_cart = sentaku.ContextualMethod()

    def __init__(self, appliance, catalog=None, name=None, stack_data=None,
                 dialog_values=None, ansible_dialog_values=None):
        Navigatable.__init__(self, appliance=appliance)
        self.catalog = catalog
        self.name = name
        self.stack_data = stack_data
        self.dialog_values = dialog_values
        self.ansible_dialog_values = ansible_dialog_values
        self.parent = self.appliance.context


class BaseOrderForm(View):
    """Represents the order form of a service.
    This form doesn't have a static set of elements apart from titles and buttons. In the most cases
    the fields can be either regular inputs or dropdowns. Their locators depend on field names. In
    order to find and fill required fields a parametrized view is used here. The keys of a fill
    dictionary should match ids of the fields. For instance there is a field with such html
    <input id="some_key"></input>, so a fill dictionary should look like that:
    {"some_key": "some_value"}
    """
    title = Text('#explorer_title_text')
    dialog_title = Text(".//div[@id='main_div']//h2")

    @ParametrizedView.nested
    class fields(ParametrizedView):  # noqa
        PARAMETERS = ("key",)
        input = Input(id=Parameter("key"))
        select = Select(id=Parameter("key"))
        param_input = Input(id=ParametrizedString("param_{key}"))
        dropdown = BootstrapSelect(locator=ParametrizedLocator(
            ".//div[contains(@class, 'bootstrap-select')]/select[@id={key|quote}]/.."))
        param_dropdown = BootstrapSelect(locator=ParametrizedLocator(
            ".//div[contains(@class, 'bootstrap-select')]/select[@id='param_{key}']/.."))

        @property
        def visible_widget(self):
            for widget in (self.input, self.dropdown, self.param_input,
                           self.param_dropdown, self.select):
                try:
                    widget.wait_displayed('15s')
                    return widget
                except TimedOutError:
                    pass
            else:
                raise ItemNotFound("Visible widget is not found")

        def read(self):
            return self.visible_widget.read()

        def fill(self, value):
            return self.visible_widget.fill(value)

    def fill(self, fill_data):
        values = deflatten_dict(fill_data)
        was_change = False
        self.before_fill(values)
        for key, value in values.items():
            widget = self.fields(key)
            if value is None:
                self.logger.debug('Skipping fill of %r because value was None', key)
                continue
            try:
                if widget.fill(value):
                    was_change = True
            except NotImplementedError:
                continue

        self.after_fill(was_change)
        return was_change


from cfme.services.service_catalogs import ui, ssui  # NOQA last for import cycles
importscan.scan(ui)
importscan.scan(ssui)
