# -*- coding: utf-8 -*-


# Returns true if ready
BASE_CHECK_SCRIPT = '''\
return {
    jquery: (typeof jQuery === "undefined") ? true : jQuery.active < 1,
    prototype: (typeof Ajax === "undefined") ? true : Ajax.activeRequestCount < 1,
    document: document.readyState == "complete"
}
'''


class BasePlugin(object):
    def __init__(self, navigator):
        self.navigator = navigator

    @property
    def browser(self):
        return self.navigator.browser

    @property
    def selenium(self):
        return self.navigator.selenium

    def check_page_ready(self):
        """Basic readiness check. Extend if you need."""
        result = self.browser.execute_script(BASE_CHECK_SCRIPT)
        # TODO: Logging
        return all(result.values())
