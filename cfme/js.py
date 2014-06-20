xpath = """
return document.evaluate(path, document, null, 9, null).singleNodeValue;
"""

nothing_in_flight = """
function isHidden(el) {
    if(el === null) return true;
    return el.offsetParent === null;
}
return (jQuery.active +
        Ajax.activeRequestCount +
        window.miqAjaxTimers +
        (document.readyState == "complete" ? 0 : 1) +
        (!(!isHidden(document.getElementById("spinner_div")) &&
            isHidden(document.getElementById("lightbox_div"))) ? 0 : 1)) == 0;
"""
