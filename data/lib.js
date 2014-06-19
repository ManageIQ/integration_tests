// Library of JS calls
// USE THE SYNTAX AS IT IS SHOWN! OTHERWISE IT WONT WORK!

xpath = function(path)
{
    return document.evaluate(path, document, null, 9, null).singleNodeValue;
}

isHidden = function(el)
{
    if(el === null) return true;
    return el.offsetParent === null;
}

nothing_in_flight = function()
{
    return (jQuery.active +
            Ajax.activeRequestCount +
            window.miqAjaxTimers +
            (document.readyState == "complete" ? 0 : 1) +
            (!(!isHidden(document.getElementById("spinner_div"))
                && isHidden(document.getElementById("lightbox_div"))) ? 0 : 1)) == 0;
}