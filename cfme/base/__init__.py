import sentaku

from utils.appliance import Navigatable, Parent


class Server(Navigatable, sentaku.Element):
    def __init__(self, appliance=None):
        Navigatable.__init__(self, appliance=appliance)

    parent = Parent()

    address = sentaku.ContextualMethod()
    login = sentaku.ContextualMethod()
    login_admin = sentaku.ContextualMethod()
    logout = sentaku.ContextualMethod()
    update_password = sentaku.ContextualMethod()
    logged_in = sentaku.ContextualMethod()
    current_full_name = sentaku.ContextualMethod()
    current_username = sentaku.ContextualMethod()


from . import ui, ssui  # NOQA last for import cycles
sentaku.register_external_implementations_in(ui, ssui)
