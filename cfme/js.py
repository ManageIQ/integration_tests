xpath = """
return document.evaluate(path, document, null, 9, null).singleNodeValue;
"""

in_flight = """
function isHidden(el) {if(el === null) return true; return el.offsetParent === null;}

return {
    jquery: jQuery.active,
    prototype: (typeof Ajax === "undefined") ? 0 : Ajax.activeRequestCount,
    miq: window.miqAjaxTimers,
    spinner: (!isHidden(document.getElementById("spinner_div")))
        && isHidden(document.getElementById("lightbox_div")),
    document: document.readyState
};
"""

update_retirement_date_function_script = """\
function updateDate(newValue) {
    if(typeof $j == "undefined") {
        var jq = $;
    } else {
        var jq = $j;
    }
    jq("#miq_date_1")[0].value = newValue;
    miqSparkleOn();
    jq.ajax({
        type: 'POST',
        url: '/vm_infra/retire_date_changed?miq_date_1='+newValue
    }).done(
        function(data){
            eval(data);
        }
    )
}

"""
# TODO: Get the url: directly from the attribute in the page?
