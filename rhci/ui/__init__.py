'Compatibility tools to let us use pieces of the robottelo framework in cfme_tests'
from cfme.web_ui import Region
from robottelo.ui.locators import locators as robottelo_locators


class RobotelloRegion(Region):
    """A CFME Tests Region with knowledge of locators defined in robottelo

    For use in testing RHCI, adds a new kwarg: ``robo_locators``. This is a list
    of locator names from ``robottelo.ui.locators.locators``, which will be added
    to this instance's locators dict at instantiation based on the values in
    robottelo.

    This class may not be needed at all; check to see if the page in question is
    already implemented in robottelo. If so, you can use the robottelo class instead.
    If the robottelo class is an instance of ``robottelo.ui.base.Base``, you can
    instantiate it with cfme_tests's ``utils.broweser.ensure_browser_open()`` as the
    first argument, which will start a browser with cfme_tests settings that can be
    used by the robottelo class.
    """

    def __init__(self, *args, **kwargs):
        if args:
            locators = args[0]
        else:
            locators = kwargs.pop('locators', {})

        for robo_locator in kwargs.pop('robo_locators', []):
            locators[robo_locator] = robottelo_locators[robo_locator]

        super(RobotelloRegion, self).__init__(locators, *args[1:], **kwargs)
