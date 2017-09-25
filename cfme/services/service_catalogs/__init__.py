import sentaku


from cfme.common import WidgetasticTaggable
from cfme.utils.appliance import Navigatable
from cfme.utils.update import Updateable


class ServiceCatalogs(Navigatable, WidgetasticTaggable, Updateable, sentaku.modeling.ElementMixin):
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


from . import ui, ssui  # NOQA last for import cycles
sentaku.register_external_implementations_in(ui, ssui)
