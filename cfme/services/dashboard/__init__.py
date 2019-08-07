import importscan
import sentaku

from cfme.utils.appliance import Navigatable


class Dashboard(Navigatable, sentaku.modeling.ElementMixin):
    """ Dashboard main class for SSUI."""

    num_of_rows = sentaku.ContextualMethod()
    results = sentaku.ContextualMethod()
    total_services = sentaku.ContextualMethod()
    total_requests = sentaku.ContextualMethod()
    retiring_soon = sentaku.ContextualMethod()
    current_services = sentaku.ContextualMethod()
    retired_services = sentaku.ContextualMethod()
    monthly_charges = sentaku.ContextualMethod()
    pending_requests = sentaku.ContextualMethod()
    approved_requests = sentaku.ContextualMethod()
    denied_requests = sentaku.ContextualMethod()

    def __init__(self, appliance):
        self.appliance = appliance
        self.parent = self.appliance.context


from cfme.services.dashboard import ssui  # NOQA last for import cycles
importscan.scan(ssui)
