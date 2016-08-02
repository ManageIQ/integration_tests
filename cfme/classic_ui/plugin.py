# -*- coding: utf-8 -*-
from pomoc.plugin import BasePlugin


CHECK_PAGE_JS = '''\
function isHidden(el) {if(el === null) return true; return el.offsetParent === null;}

return {
    miq: window.miqAjaxTimers === undefined || window.miqAjaxTimers < 1,
    spinner: !((!isHidden(document.getElementById("spinner_div")))
        && isHidden(document.getElementById("lightbox_div"))),
    jquery: (typeof jQuery === "undefined") ? true : jQuery.active < 1,
    prototype: (typeof Ajax === "undefined") ? true : Ajax.activeRequestCount < 1,
    document: document.readyState == "complete"
}
'''


class ClassicUIPlugin(BasePlugin):
    def check_page_ready(self):
        result = self.browser.execute_script(CHECK_PAGE_JS)
        # TODO: Logging
        return all(result.values())
