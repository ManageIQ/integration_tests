import importscan
import sentaku

from cfme.common import Taggable
from cfme.utils.appliance import Navigatable
from cfme.utils.update import Updateable


class MyService(Updateable, Navigatable, Taggable, sentaku.modeling.ElementMixin):
    """
        My Service main class to context switch between ui
        and ssui. All the below methods are implemented in both ui
        and ssui side .
    """

    update = sentaku.ContextualMethod()
    retire = sentaku.ContextualMethod()
    retire_on_date = sentaku.ContextualMethod()
    exists = sentaku.ContextualProperty()
    delete = sentaku.ContextualMethod()
    set_ownership = sentaku.ContextualMethod()
    get_ownership = sentaku.ContextualMethod()
    edit_tags = sentaku.ContextualMethod()
    check_vm_add = sentaku.ContextualMethod()
    download_file = sentaku.ContextualMethod()
    reconfigure_service = sentaku.ContextualMethod()
    launch_vm_console = sentaku.ContextualMethod()
    service_power = sentaku.ContextualMethod()
    add_resource_generic_object = sentaku.ContextualMethod()

    def __init__(self, appliance, name=None, description=None, vm_name=None):
        self.appliance = appliance
        self.name = name
        self.description = description
        self.vm_name = vm_name
        self.parent = self.appliance.context

    @property
    def rest_api_entity(self):
        return self.appliance.rest_api.collections.services.find_by(name=self.name)[0]


from cfme.services.myservice import ui, ssui, rest  # NOQA last for import cycles
importscan.scan(ui)
importscan.scan(ssui)
importscan.scan(rest)
