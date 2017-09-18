import sentaku

from cfme.utils.appliance import Navigatable


class Dashboard(Navigatable, sentaku.modeling.ElementMixin):
    """ Dashboard main class for SSUI."""

    total_service = sentaku.ContextualMethod()
    total_request = sentaku.ContextualMethod()
    retiring_soon = sentaku.ContextualMethod()
    current_services = sentaku.ContextualMethod()
    retired_services = sentaku.ContextualMethod()
    monthly_charges = sentaku.ContextualMethod()

    def __init__(self, appliance):
        self.appliance = appliance
        self.parent = self.appliance.context


from . import ssui  # NOQA last for import cycles
sentaku.register_external_implementations_in(ssui)
