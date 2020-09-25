import importscan
import sentaku

from cfme.common import Taggable
from cfme.exceptions import RestLookupError
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
    is_retired = sentaku.ContextualProperty()
    retire_on_date = sentaku.ContextualMethod()
    exists = sentaku.ContextualProperty()
    delete = sentaku.ContextualMethod()
    status = sentaku.ContextualProperty()
    set_ownership = sentaku.ContextualMethod()
    get_ownership = sentaku.ContextualMethod()
    edit_tags = sentaku.ContextualMethod()
    check_vm_add = sentaku.ContextualMethod()
    download_file = sentaku.ContextualMethod()
    reconfigure_service = sentaku.ContextualMethod()
    launch_vm_console = sentaku.ContextualMethod()
    service_power = sentaku.ContextualMethod()
    add_resource_generic_object = sentaku.ContextualMethod()

    def __init__(self, appliance, name=None, name_base=None, description=None, vm_name=None):
        self.appliance = appliance
        self.name = name
        self.description = description
        self.vm_name = vm_name
        self.parent = self.appliance.context

    @property
    def rest_api_entity(self):
        try:
            return self.appliance.rest_api.collections.services.get(name=self.name, display=True)
        except ValueError:
            raise RestLookupError(f'No service rest entity found matching name {self.name}')


from cfme.services.myservice import ui, ssui, rest  # NOQA last for import cycles
importscan.scan(ui)
importscan.scan(ssui)
importscan.scan(rest)
