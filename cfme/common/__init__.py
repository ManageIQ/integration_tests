# -*- coding: utf-8 -*-
from cached_property import cached_property
from contextlib import contextmanager
from functools import partial

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import CheckboxTree, InfoBlock, Table, flash, form_buttons, mixins, toolbar
from utils import attributize_string, version
from urlparse import urlparse
from utils.wait import wait_for

pol_btn = partial(toolbar.select, "Policy")


class PolicyProfileAssignable(object):
    """This class can be inherited by anything that provider load_details method.

    It provides functionality to assign and unassign Policy Profiles"""
    manage_policies_tree = CheckboxTree("//div[@id='protect_treebox']/ul")

    @property
    def assigned_policy_profiles(self):
        try:
            return self._assigned_policy_profiles
        except AttributeError:
            self._assigned_policy_profiles = set([])
            return self._assigned_policy_profiles

    def assign_policy_profiles(self, *policy_profile_names):
        """ Assign Policy Profiles to this object.

        Args:
            policy_profile_names: :py:class:`str` with Policy Profile names. After Control/Explorer
                coverage goes in, PolicyProfile objects will be also passable.
        """
        map(self.assigned_policy_profiles.add, policy_profile_names)
        self._assign_unassign_policy_profiles(True, *policy_profile_names)

    def unassign_policy_profiles(self, *policy_profile_names):
        """ Unssign Policy Profiles to this object.

        Args:
            policy_profile_names: :py:class:`str` with Policy Profile names. After Control/Explorer
                coverage goes in, PolicyProfile objects will be also passable.
        """
        for pp_name in policy_profile_names:
            try:
                self.assigned_policy_profiles.remove(pp_name)
            except KeyError:
                pass
        self._assign_unassign_policy_profiles(False, *policy_profile_names)

    def _assign_unassign_policy_profiles(self, assign, *policy_profile_names):
        """DRY function for managing policy profiles.

        See :py:func:`assign_policy_profiles` and :py:func:`assign_policy_profiles`

        Args:
            assign: Wheter to assign or unassign.
            policy_profile_names: :py:class:`str` with Policy Profile names.
        """
        self.load_details(refresh=True)
        pol_btn("Manage Policies")
        for policy_profile in policy_profile_names:
            if assign:
                self.manage_policies_tree.check_node(policy_profile)
            else:
                self.manage_policies_tree.uncheck_node(policy_profile)
        sel.move_to_element({
            version.LOWEST: '#tP',
            "5.5": "//h3[1]"})
        form_buttons.save()
        flash.assert_no_errors()


class Taggable(object):
    """This class can be inherited by anything that provider load_details method.

    It provides functionality to assign and unassign tags."""
    def add_tag(self, tag, single_value=False):
        self.load_details(refresh=True)
        mixins.add_tag(tag, single_value=single_value, navigate=True)

    def remove_tag(self, tag):
        self.load_details(refresh=True)
        mixins.remove_tag(tag)

    def get_tags(self, tag="My Company Tags"):
        self.load_details(refresh=True)
        return mixins.get_tags(tag=tag)


class Validatable(object):
    """
    Class which Middleware provider and other middleware pages must extend
    to be able to validate properties values shown in summary page.

    """

    """
    Tuples which first value is the provider class's attribute name,
    the second value is provider's UI summary page field key.

    Should have values in child classes.

    """
    property_tuples = []

    def properties_ui(self):
        self.load_details(refresh=True)
        property_ui = {}
        for row in Table('//div[@id="main-content"]//table').rows():
            property_ui[row[0].text] = row[1].text
        return property_ui

    def validate_properties(self):
        """
        Validation method which checks whether class attributes,
        which were used during creation of provider,
        is correctly displayed in Properties section of provider UI.
        The maps between class attribute and UI property is done via 'property_tuples' variable.

        Fails if some property does not match.
        """
        properties = self.properties_ui()
        assert len(properties) > 0, 'No property was found in UI'
        for property_tuple in self.property_tuples:
            expected_value = str(getattr(self, property_tuple[0]))
            shown_value = str(properties[property_tuple[1]])
            assert(expected_value == shown_value,
                   'Property {} has wrong value, expected {} but was {}'
                   .format(property_tuple[1], expected_value, shown_value))


class SummaryMixin(object):
    """Use this mixin to have simple access to the Summary informations of an object.

    Requires that the class has ``load_details(refresh)`` method defined.

    All the names from the UI are "attributized".

    Sample usage:

    .. code-block:: python

        # You can retrieve the text value as it is in the UI
        provider.summary.properties.host_name.text_value  # => 'hostname'
        # Or let it guess if it is a number and return float or int
        provider.summary.properties.aggregate_host_cpus.value  # => 12
        # You can get the image address
        provider.summary.foo.bar.img  # => value parsed by urlparse()
        # Or the onclick link
        provider.summary.foo.bar.link  # => 'http://foo/bar'
        # Check if it is clickable
        assert provider.summary.xyz.qwer.clickable

        # You can iterate like it was a dictionary
        for table_name, table in provider.summary:
            # table_name contains title of the table
            for key, value in table:
                # key contains the left cell text, value contains the value holder
                print('{}: {}'.format(key, value.text_value))


    """
    @cached_property
    def summary(self):
        return Summary(self)


class Summary(object):
    """Summary container class. An entry point to the summary listing"""
    HEADERS = '//th[@align="left"]'

    def __init__(self, o):
        self._object = o
        self._keys = []
        self.reload()

    def __repr__(self):
        return "<Summary {}>".format(" ".join(self._keys))

    def reload(self):
        for key in self._keys:
            try:
                delattr(self, key)
            except AttributeError:
                pass
        self._keys = []
        self._object.load_details(refresh=True)
        for header in sel.elements(self.HEADERS):
            header_text = sel.text_sane(header)
            header_id = attributize_string(header_text)
            table_object = SummaryTable(self._object, header_text, header)
            setattr(self, header_id, table_object)
            self._keys.append(header_id)

    def __iter__(self):
        """This enables you to iterate through like it was a dictionary, just without .iteritems"""
        for key in self._keys:
            yield (key, getattr(self, key))

    def groups(self):
        """Returns a dictionary of keys (table titles) and table objects."""
        return dict(iter(self))

    @property
    def group_names(self):
        """Returns names of the tables."""
        return self._keys


class SummaryTable(object):
    ROWS = '../../../tbody/tr'

    def __init__(self, o, text, entry):
        self._object = o
        self._text = text
        self._entry = entry
        self._keys = []
        self.load()

    def __repr__(self):
        return "<SummaryTable {} {}>".format(
            repr(self._text),
            " ".join("{}={}".format(key, repr(getattr(self, key))) for key in self._keys))

    def load(self):
        self._keys = []
        key_values = []
        for row in sel.elements(self.ROWS, root=self._entry):
            tds = sel.elements('./td', root=row)
            key = tds[0]
            klass = sel.get_attribute(key, 'class')
            if klass and 'label' in klass:
                # Ordinary field
                key_id = attributize_string(sel.text_sane(key))
                value = tuple(tds[1:])
                try:
                    rowspan = int(sel.get_attribute(key, 'rowspan'))
                except (ValueError, TypeError):
                    rowspan = None
                if rowspan:
                    key_values.append((key, key_id, [value]))
                else:
                    key_values.append((key, key_id, value))
            else:
                # value of last key_values should be extended
                key_values[-1][2].append(tuple(tds))
        for key, key_id, value in key_values:
            value_object = process_field(value)
            setattr(self, key_id, value_object)
            self._keys.append(key_id)

    def reload(self):
        self._object.load_details(refresh=True)
        for key in self._keys:
            try:
                delattr(self, key)
            except AttributeError:
                pass
        return self.load()

    @property
    def keys(self):
        return self._keys

    def __iter__(self):
        for key in self._keys:
            yield (key, getattr(self, key))

    def items(self):
        return dict(iter(self))


class SummaryValue(object):
    def __init__(self, el):
        self._el = el

    def __repr__(self):
        return repr(self.text_value)

    @cached_property
    def img(self):
        try:
            img_o = sel.element('./img', root=self._el)
            return urlparse(sel.get_attribute(img_o, 'src').strip())
        except sel.NoSuchElementException:
            return None

    @cached_property
    def text_value(self):
        return sel.text_sane(self._el)

    @cached_property
    def value(self):
        # Try parsing a number
        try:
            return int(self.text_value)
        except (ValueError, TypeError):
            try:
                return float(self.text_value)
            except (ValueError, TypeError):
                return self.text_value

    @cached_property
    def link(self):
        if sel.get_attribute(sel.element('..', root=self._el), 'onclick'):
            return self._el
        else:
            return None

    @property
    def clickable(self):
        return self.link is not None

    def click(self):
        """A convenience function to click the summary item."""
        return sel.click(self)

    def _custom_click_handler(self, wait_ajax):
        if not self.clickable:
            raise ValueError("Cannot click on {} because it is not clickable".format(repr(self)))
        try:
            return sel.click(self.link, wait_ajax, no_custom_handler=True)
        except self.sel.StaleElementReferenceException:
            raise RuntimeError('Couldnt click on {} because the page was left.'.format(repr(self)))


def process_field(values):
    if isinstance(values, list):
        return map(process_field, values)
    else:
        if len(values) == 1:
            return SummaryValue(values[0])
        else:
            return map(SummaryValue, values)


class Compliance(object):
    """This class can be inherited by anything that provider load_details method.

    It provides functionality to invoke compliance check and get its result.
    """
    def check_compliance(self):
        """Clicks the Check compliance button."""
        self.load_details(refresh=True)
        pol_btn("Check Compliance of Last Known Configuration", invokes_alert=True)
        sel.handle_alert()
        flash.assert_no_errors()

    @contextmanager
    def check_compliance_wrapper(self, timeout=240):
        """This wrapper takes care of waiting for the compliance status to change

        Args:
            timeout: Wait timeout in seconds.
        """
        self.load_details(refresh=True)
        original_state = self.compliance_status
        yield
        wait_for(
            lambda: self.compliance_status != original_state,
            num_sec=timeout, delay=5, message="compliance of {} checked".format(self.name),
            fail_func=lambda: toolbar.select("Reload"))

    def check_compliance_and_wait(self, timeout=240):
        """Initiates compliance check and waits for it to finish."""
        with self.check_compliance_wrapper(timeout=timeout):
            self.check_compliance()
        return self.compliant

    @property
    def compliance_status(self):
        """Returns the title of the compliance infoblock. The title contains datetime so it can be
        compared.

        Returns:
            :py:class:`NoneType` if no title is present (no compliance checks before), otherwise str
        """
        self.load_details(refresh=True)
        return InfoBlock("Compliance", "Status").title

    @property
    def compliant(self):
        """Check if the VM is compliant

        Returns:
            :py:class:`NoneType` if the VM was never verified, otherwise :py:class:`bool`
        """
        text = self.get_detail(properties=("Compliance", "Status")).strip().lower()
        if text == "never verified":
            return None
        elif text.startswith("non-compliant"):
            return False
        elif text.startswith("compliant"):
            return True
        else:
            raise ValueError("{} is not a known state for compliance".format(text))
