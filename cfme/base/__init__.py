import sentaku

from utils.appliance import Navigatable


class Server(Navigatable, sentaku.Element):
    def __init__(self, appliance=None):
        Navigatable.__init__(self, appliance=appliance)


from . import ui, ssui  # NOQA last for import cycles
sentaku.register_external_implementations_in(ui, ssui)
