# -*- coding: utf-8 -*-
from jsmin import jsmin

xpath = """\
function xpath(root, xpath) {
    if(root == null)
        root = document;
    var nt = XPathResult.ANY_UNORDERED_NODE_TYPE;
    return document.evaluate(xpath, root, null, nt, null).singleNodeValue;
}
"""

in_flight = """
function isHidden(el) {if(el === null) return true; return el.offsetParent === null;}

return {
    jquery: jQuery.active,
    prototype: (typeof Ajax === "undefined") ? 0 : Ajax.activeRequestCount,
    miq: window.miqAjaxTimers,
    spinner: (!isHidden(document.getElementById("spinner_div")))
        && isHidden(document.getElementById("lightbox_div")),
    document: document.readyState,
    autofocus: (typeof checkMiqQE === "undefined") ? 0 : checkMiqQE('autofocus'),
    debounce: (typeof checkMiqQE === "undefined") ? 0 : checkMiqQE('debounce'),
    miqQE: (typeof checkAllMiqQE === "undefined") ? 0 : checkAllMiqQE()
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

# Expects: arguments[0] = element, arguments[1] = value to set
set_angularjs_value_script = """\
(function(elem, value){
    var angular_elem = angular.element(elem);
    var $parse = angular_elem.injector().get('$parse');
    var getter = $parse(elem.getAttribute('ng-model'));
    var setter = getter.assign;
    angular_elem.scope().$apply(function($scope) { setter($scope, value); });
}(arguments[0], arguments[1]));
"""


# The functions below do various JS magic to speed up the tree traversings to a maximum possible
# level.

# This function retrieves the root of the tree. Can wait for the tree to get initialized
_tree_get_root = """\
function get_root(loc) {
    var start_time = new Date();
    var root = null;
    while(root === null && ((new Date()) - start_time) < 10000)
    {
        try {
            root = $(loc).dynatree("getRoot");
        } catch(err) {
            // Nothing ...
        }
    }

    return root;
}
"""

# This function is used to DRY the decision on which text to match
_get_level_name = xpath + """\
function get_level_name(level, by_id) {
    if(by_id){
        return level.li.getAttribute("id");
    } else {
        var e = xpath(level.li, "./span/a");
        if(e === null)
            return null;
        else
            return e.textContent;
    }
}
"""

# needs xpath to work, provided by dependencies of the other functions
_expandable = """\
function expandable(el) {
    return xpath(el.li, "./span/span[contains(@class, 'dynatree-expander')]") !== null;
}
"""

# This function reads whole tree. If it faces an ajax load, it returns false.
# If it does not return false, the result is complete.
read_tree = jsmin(_tree_get_root + _get_level_name + _expandable + """\
function read_tree(root, read_id, _root_tree) {
    if(read_id === undefined)
        read_id = false;
    if(_root_tree === undefined)
        _root_tree = true;
    if(_root_tree) {
        root = get_root(root);
        if(root === null)
            return null;
        if(expandable(root) && (!root.bExpanded)) {
            root.expand();
            if(root.childList === null && root.data.isLazy){
                return false;
            }
        }
        var result = new Array();
        var need_wait = false;
        var children = (root.childList === null) ? [] : root.childList;
        for(var i = 0; i < children.length; i++) {
            var child = children[i];
            var sub = read_tree(child, read_id, false);
            if(sub === false)
                need_wait = true;
            else
                result.push(sub);
        }
        if(need_wait)
            return false;
        else if(children.length == 0)
            return null;
        else
            return result;
    } else {
        if(expandable(root) && (!root.bExpanded)) {
            root.expand();
            if(root.childList === null && root.data.isLazy){
                return false;
            }
        }
        var name = get_level_name(root, read_id);

        var result = new Array();
        var need_wait = false;
        var children = (root.childList === null) ? [] : root.childList;
        for(var i = 0; i < children.length; i++) {
            var child = children[i];
            var sub = read_tree(child, read_id, false);
            if(sub === false)
                need_wait = true;
            else
                result.push(sub);
        }
        if(need_wait)
            return false;
        else if(children.length == 0)
            return name;
        else
            return [name, result]

    }
}
""")

# This function searches for specified node by path. If it faces an ajax load, it returns false.
# If it does not return false, the result is complete.
find_leaf = jsmin(_tree_get_root + _get_level_name + _expandable + """\
function find_leaf(root, path, by_id) {
    if(path.length == 0)
        return null;
    if(by_id === undefined)
        by_id = false;
    var item = get_root(root);
    if(typeof item.childList === "undefined")
        throw "CANNOT FIND TREE /" + root + "/";
    var i;  // The start of matching for path. Important because in one case, we already matched 1st
    var lname = get_level_name(item, by_id);
    if(item.childList.length == 1 && lname === null) {
        item = item.childList[0];
        i = 1;
        if(get_level_name(item, by_id) != path[0])
            throw "TREEITEM /" + path[0] + "/ NOT FOUND IN THE TREE";
    } else if(lname === null) {
        i = 0;
    } else {
        if(lname != path[0])
            throw "TREEITEM /" + path[0] + "/ NOT FOUND IN THE TREE";
        item = item.childList[0];
        i = 1;
    }
    for(; i < path.length; i++) {
        var last = (i + 1) == path.length;
        var step = path[i];
        var found = false;
        if(expandable(item) && (!item.bExpanded)) {
            item.expand();
            if(item.childList === null)
                return false;  //We need to do wait_for_ajax and then repeat.
        }

        for(var j = 0; j < (item.childList || []).length; j++) {
            var nextitem = item.childList[j];
            var nextitem_name = get_level_name(nextitem, by_id);
            if(nextitem_name == step) {
                found = true;
                item = nextitem;
                break;
            }
        }

        if(!found)
            throw "TREEITEM /" + step + "/ NOT FOUND IN THE TREE";
    }

    return xpath(item.li, "./span/a");
}
""")

# TODO: Get the url: directly from the attribute in the page?
