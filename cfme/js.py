xpath = """
return document.evaluate(path, document, null, 9, null).singleNodeValue;
"""

in_flight = """
function isHidden(el) {if(el === null) return true; return el.offsetParent === null;}

return {
    jquery: jQuery.active,
    prototype: Ajax.activeRequestCount,
    miq: window.miqAjaxTimers,
    spinner: (!isHidden(document.getElementById("spinner_div")))
        && isHidden(document.getElementById("lightbox_div")),
    document: document.readyState
};
"""
