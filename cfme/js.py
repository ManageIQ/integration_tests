xpath = """
return document.evaluate(path, document, null, 9, null).singleNodeValue;
"""

nothing_in_flight = """
function isHidden(el) {
    if(el === null) return true;
    return el.offsetParent === null;
}

function jqueryActive() { return jQuery.active > 0; }
function prototypeActive() { return Ajax.activeRequestCount > 0; }
function miqActive() { return window.miqAjaxTimers > 0; }
function spinnerDisplayed() { return (!isHidden(document.getElementById("spinner_div")))
 && isHidden(document.getElementById("lightbox_div")); }
function documentComplete() { return document.readyState == "complete"; }
return !(jqueryActive() || prototypeActive() || miqActive() || spinnerDisplayed()
 || !(documentComplete()));
"""
