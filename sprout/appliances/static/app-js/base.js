// This is the first custom javascript that gets included in every HTML page.

function getMethods(callback)
{
    $.ajax({
        url: "api",
        success: function(data, s, xhr) { return callback(data["result"]); },
    });
}

function callMethod(method, args, kwargs, callback_success, callback_error)
{
    $.ajax({
        type: "POST",
        url: "api",
        data: JSON.stringify({
            method: method,
            args: args,
            kwargs: kwargs,
        }),
        success: function(data, s, xhr) {
            if(data["status"] == "success")
            {
                return callback_success(data["result"]);
            }
            else if(callback_error !== undefined)
            {
                return callback_error(data["result"]);
            }
        },
    });
}

function keys(obj)
{
    var keys = [];
    for(var key in obj)
    {
        if(obj.hasOwnProperty(key))
        {
            keys.push(key);
        }
    }
    return keys;
}

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

var csrftoken = getCookie('csrftoken');

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

function sameOrigin(url) {
    // test that a given url is a same-origin URL
    // url could be relative or scheme relative or absolute
    var host = document.location.host; // host + port
    var protocol = document.location.protocol;
    var sr_origin = '//' + host;
    var origin = protocol + sr_origin;
    // Allow absolute or scheme relative URLs to same origin
    return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
        (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
        // or any other URL that isn't scheme relative or absolute i.e relative.
        !(/^(\/\/|http:|https:).*/.test(url));
}

function addAlert(type, text) {
    var icon = "";
    if(type == "success"){
        icon = "<span class='pficon pficon-ok'></span>";
    } else if(type == "danger" || type == "warning"){
        icon = "<span class='pficon-layered'><span class='pficon pficon-warning-triangle'></span><span class='pficon pficon-warning-exclamation'></span></span>";
    }
    return $("#alerts").append("<div class='alert alert-" + type + " alert-dismissible fade in' role='alert'><button class='close' data-dismiss='alert'>×</button> " + text + " " + icon + "</div>");
}

$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type) && sameOrigin(settings.url)) {
            // Send the token to same-origin, relative URLs only.
            // Send the token only if the method warrants CSRF protection
            // Using the CSRFToken value acquired earlier
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});