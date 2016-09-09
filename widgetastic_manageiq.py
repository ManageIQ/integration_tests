# -*- coding: utf-8 -*-
import re
from jsmin import jsmin
from selenium.common.exceptions import WebDriverException

from widgetastic.exceptions import NoSuchElementException
from widgetastic.utils import VersionPick, Version
from widgetastic.widget import Widget, do_not_read_this_widget
from widgetastic.xpath import quote
from widgetastic_patternfly import CandidateNotFound, BootstrapTreeview


class DynaTree(Widget):
    """ A class directed at CFME Tree elements

    """

    XPATH = """\
    function xpath(root, xpath) {
        if(root == null)
            root = document;
        var nt = XPathResult.ANY_UNORDERED_NODE_TYPE;
        return document.evaluate(xpath, root, null, nt, null).singleNodeValue;
    }
    """

    # This function retrieves the root of the tree. Can wait for the tree to get initialized
    TREE_GET_ROOT = """\
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
    GET_LEVEL_NAME = XPATH + """\
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
    EXPANDABLE = """\
    function expandable(el) {
        return xpath(el.li, "./span/span[contains(@class, 'dynatree-expander')]") !== null;
    }
    """

    # This function reads whole tree. If it faces an ajax load, it returns false.
    # If it does not return false, the result is complete.
    READ_TREE = jsmin(TREE_GET_ROOT + GET_LEVEL_NAME + EXPANDABLE + """\
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
    FIND_LEAF = jsmin(TREE_GET_ROOT + GET_LEVEL_NAME + EXPANDABLE + """\
    function find_leaf(root, path, by_id) {
        if(path.length == 0)
            return null;
        if(by_id === undefined)
            by_id = false;
        var item = get_root(root);
        if(typeof item.childList === "undefined")
            throw "CANNOT FIND TREE /" + root + "/";
        var i;  // The start of matching for path. Because in one case, we already matched 1st
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

    def __init__(self, parent, tree_id=None, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self._tree_id = tree_id

    @property
    def tree_id(self):
        if self._tree_id is not None:
            return self._tree_id
        else:
            try:
                return self.parent.tree_id
            except AttributeError:
                raise NameError(
                    'You have to specify tree_id to BootstrapTreeview if the parent object does '
                    'not implement .tree_id!')

    def __locator__(self):
        return '#{}'.format(self.tree_id)

    def read(self):
        return self.currently_selected

    def fill(self, value):
        if self.currently_selected == value:
            return False
        self.click_path(*value)
        return True

    @property
    def currently_selected(self):
        items = self.browser.elements(
            './/li[.//span[contains(@class, "dynatree-active")]]/span/a',
            parent=self,
            check_visibility=True)
        return map(self.browser.text, items)

    def root_el(self):
        return self.browser.element(self)

    def _get_tag(self):
        if getattr(self, 'tag', None) is None:
            self.tag = self.browser.tag(self)
        return self.tag

    def read_contents(self, by_id=False):
        result = False
        while result is False:
            self.browser.plugin.ensure_page_safe()
            result = self.browser.execute_script(
                "{} return read_tree(arguments[0], arguments[1]);".format(self.READ_TREE),
                self.__locator__(),
                by_id)
        return result

    def expand_path(self, *path, **kwargs):
        """ Exposes a path.

        Args:
            *path: The path as multiple positional string arguments denoting the course to take.

        Keywords:
            by_id: Whether to match ids instead of text.

        Returns: The leaf web element.

        """
        by_id = kwargs.pop("by_id", False)
        result = False

        # Ensure we pass str to the javascript. This handles objects that represent themselves
        # using __str__ and generally, you should only pass str because that is what makes sense
        path = map(str, path)

        # We sometimes have to wait for ajax. In that case, JS function returns false
        # Then we repeat and wait. It does not seem completely possible to wait for the data in JS
        # as it runs on one thread it appears. So this way it will try to drill multiple times
        # each time deeper and deeper :)
        while result is False:
            self.browser.plugin.ensure_page_safe()
            try:
                result = self.browser.execute_script(
                    "{} return find_leaf(arguments[0],arguments[1],arguments[2]);".format(
                        self.FIND_LEAF),
                    self.__locator__(),
                    path,
                    by_id)
            except WebDriverException as e:
                text = str(e)
                match = re.search(r"TREEITEM /(.*?)/ NOT FOUND IN THE TREE", text)
                if match is not None:
                    item = match.groups()[0]
                    raise CandidateNotFound(
                        {'message': "{}: could not be found in the tree.".format(item),
                         'path': path,
                         'cause': e})
                match = re.search(r"^CANNOT FIND TREE /(.*?)/$", text)
                if match is not None:
                    tree_id = match.groups()[0]
                    raise NoSuchElementException(
                        "Tree {} / {} not found.".format(tree_id, self.locator))
                # Otherwise ...
                raise CandidateNotFound({
                    'message': 'Something else happened!',
                    'path': path,
                    'cause': e})
        return result

    def click_path(self, *path, **kwargs):
        """ Exposes a path and then clicks it.

        Args:
            *path: The path as multiple positional string arguments denoting the course to take.

        Keywords:
            by_id: Whether to match ids instead of text.

        Returns: The leaf web element.

        """
        # Ensure we pass str to the javascript. This handles objects that represent themselves
        # using __str__ and generally, you should only pass str because that is what makes sense
        path = map(str, path)

        leaf = self.expand_path(*path, **kwargs)
        self.logger.info("Path %r yielded menuitem %r", path, self.browser.text(leaf))
        if leaf is not None:
            self.browser.plugin.ensure_page_safe()
            self.browser.click(leaf)
        return leaf


def ManageIQTree(tree_id=None):  # noqa
    return VersionPick({
        Version.lowest(): DynaTree(tree_id),
        '5.7.0.1': BootstrapTreeview(tree_id),
    })


class SummaryFormItem(Widget):
    """The UI item that shows the values for objects that are NOT VMs, Providers and such ones."""
    LOCATOR = (
        './/h3[normalize-space(.)={}]/following-sibling::div[1]/div'
        '/label[normalize-space(.)={}]/following-sibling::div')

    def __init__(self, parent, group_title, item_name, text_filter=None, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self.group_title = group_title
        self.item_name = item_name
        if text_filter is not None and not callable(text_filter):
            raise TypeError('text_filter= must be a callable')
        self.text_filter = text_filter

    def __locator__(self):
        return self.LOCATOR.format(quote(self.group_title), quote(self.item_name))

    @property
    def text(self):
        if not self.is_displayed:
            return None
        ui_text = self.browser.text(self)
        if self.text_filter is not None:
            # Process it
            ui_text = self.text_filter(ui_text)

        return ui_text

    def read(self):
        text = self.text
        if text is None:
            do_not_read_this_widget()
        return text
