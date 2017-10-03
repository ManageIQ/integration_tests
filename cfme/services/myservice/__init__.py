import sentaku

from cfme.utils.appliance import Navigatable
from cfme.common import WidgetasticTaggable
from cfme.utils.update import Updateable


class MyService(Updateable, Navigatable, WidgetasticTaggable, sentaku.modeling.ElementMixin):
    """
        My Service main class to context switch between ui
        and ssui. All the below methods are implemented in both ui
        and ssui side .
    """

    update = sentaku.ContextualMethod()
    retire = sentaku.ContextualMethod()
    retire_on_date = sentaku.ContextualMethod()
    exists = sentaku.ContextualMethod()
    delete = sentaku.ContextualMethod()
    set_ownership = sentaku.ContextualMethod()
    edit_tags = sentaku.ContextualMethod()
    check_vm_add = sentaku.ContextualMethod()
    download_file = sentaku.ContextualMethod()
    reconfigure_service = sentaku.ContextualMethod()
    launch_vm_console = sentaku.ContextualMethod()

    def __init__(self, appliance, name=None, description=None, vm_name=None):
        self.appliance = appliance
        self.name = name
        self.description = description
        self.vm_name = vm_name
        self.parent = self.appliance.context


from . import ui, ssui  # NOQA last for import cycles
sentaku.register_external_implementations_in(ui, ssui)
