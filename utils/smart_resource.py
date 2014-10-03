# -*- coding: utf-8 -*-
import re

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import form_buttons, flash


class Unknown(object):
    pass


class Impossible(Unknown):
    def __repr__(self):
        return "Impossible"


def _create_getter_for(key):
    def getter(self):
        if key in self.__updates__:
            return self.__updates__.get(key, None)
        else:
            if self.__data__[key] is Unknown:
                self._pull()
            return self.__data__[key]
    return getter


def _create_setter_for(key):
    def setter(self, value):
        self.__updates__[key] = value
    return setter


class _smart_resource_meta(type):
    def __new__(cls, name, bases, attrs):
        super_new = super(_smart_resource_meta, cls).__new__
        # Also ensure initialization is only performed for subclasses of Model
        # (excluding Model class itself).
        parents = [b for b in bases if isinstance(b, _smart_resource_meta)]
        if not parents:
            return super_new(cls, name, bases, attrs)

        new_attrs = {"__fields__": {}}
        # Retrieve all of the fields inherited (properties are generated but dict not)
        for base in bases:
            if issubclass(base, SmartResource) and base is not SmartResource:
                for field_name, field in base.__fields__.iteritems():
                    new_attrs["__fields__"][field_name] = field
        # And generate new fields
        for key, value in attrs.iteritems():
            if not isinstance(value, Field):
                new_attrs[key] = value
                continue
            # Store fields in this hidden key
            new_attrs["__fields__"][key] = value
            new_attrs[key] = property(
                fget=_create_getter_for(key),
                fset=_create_setter_for(key) if value.can_be_set else None)

        # Auto-generated docstring, using original __doc__ as header if present.
        new_attrs["__doc__"] = "{}\n\nKeywords:\n{}".format(
            attrs.get("__doc__", "A {} Resource".format(name)),
            "\n".join(
                "    {}: A :py:class:`{}`, {}".format(
                    field_name,
                    field.__class__.__name__,
                    getattr(field, "description", None) or "no description provided")
                for field_name, field
                in new_attrs["__fields__"].iteritems()
            )
        )
        return super_new(cls, name, bases, new_attrs)


class Field(object):
    GET_FROM_DETAIL = False

    @property
    def can_be_set(self):
        return hasattr(self, "set_value")


class Couple(Field):
    GET_FROM_DETAIL = True

    def __init__(self, detail_field, edit_field):
        self.detail = detail_field
        self.edit = edit_field

    @property
    def can_be_set(self):
        return True

    def get_value(self):
        return self.detail.get_value()

    def set_value(self, value):
        self.edit.set_value(value)


class InputField(Field):
    def __init__(self, id=None, xpath=None, description=None):
        self.id = id
        self.xpath = xpath
        self.description = description
        assert (id or xpath) and not (id and xpath), "You have to specify either id or xpath"

    def locate(self):
        if self.id:
            return "input#{}".format(self.id)
        else:
            return self.xpath

    def get_value(self):
        return sel.value(sel.element(self))

    def set_value(self, value):
        sel.set_text(self, value)


class PasswordField(Field):
    def __init__(self, password_id, verify_id, description=None):
        self.password_id = password_id
        self.verify_id = verify_id
        self.description = description

    def set_value(self, value):
        sel.set_text("#{}".format(self.password_id), value)
        sel.set_text("#{}".format(self.verify_id), value)


class SelectField(Field, sel.Select):
    def __init__(self, id=None, xpath=None, description=None, multi=False):
        self.description = description
        assert not (id and xpath), "You have to specify either id or xpath but not both"
        if id is not None:
            super(SelectField, self).__init__("select#{}".format(id), multi)
        elif xpath is not None:
            super(SelectField, self).__init__(xpath, multi)
        else:
            raise Exception("You have to specify at least id or xpath")

    def get_value(self):
        if self.is_multiple:
            return map(sel.text, self.all_selected_options)
        else:
            return sel.text(self.first_selected_option)

    def set_value(self, value):
        sel.select(self, value)


class InfoBlockField(Field):
    GET_FROM_DETAIL = True

    def __init__(self, block_name, field_name):
        self.name = block_name
        self.field = field_name

    def get_value(self):
        value_element = sel.element(
            '//table//th[contains(., "{}")]/../../../..|'
            '//p[@class="legend"][contains(., "{}")]/..'
            '/table/tbody/tr/td[1][@class="key" or @class="label"][.="{}"]/../td[2]'
            .format(self.name, self.name, self.field))
        return sel.text_sane(value_element)


class SmartResource(object):
    __metaclass__ = _smart_resource_meta
    CREATE_LOCATION = None
    EDIT_LOCATION = None
    DETAIL_LOCATION = None
    DELETE_FUNCTION = None

    CREATE_BUTTON = form_buttons.add
    UPDATE_BUTTON = form_buttons.save

    def __init__(self, **data):
        self.__data__ = {}
        self.__updates__ = {}
        for key in self.__fields__:
            self.__data__[key] = data.pop(key, Unknown)
        if hasattr(self, "post_initialize"):
            self.post_initialize(**data)  # Use what is rest

    def __repr__(self):
        return "<#{}.{} ({}): {}, dirty: {}>".format(
            self.__module__, self.__class__.__name__, self._underscore_object_name,
            " ".join(
                "@{}={}".format(
                    key,
                    repr(getattr(self, key)) if getattr(self, key) is not Unknown else "?")
                for key in self.__fields__.iterkeys()
            ),
            str([key for key in self.__fields__.iterkeys() if key in self.__updates__])
        )

    @property
    def needs_update(self):
        return len(self.__updates__.keys()) > 0

    @property
    def needs_pull(self):
        return any(value is Unknown for value in self.__data__.itervalues())

    @property
    def _underscore_object_name(self):
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', self.__class__.__name__)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    @property
    def _nav_context(self):
        return {self._underscore_object_name: self}

    def _pull(self):
        detail_fields = {}
        edit_fields = {}
        for field_name, field in self.__fields__.iteritems():
            if field.GET_FROM_DETAIL:
                detail_fields[field_name] = field
            else:
                edit_fields[field_name] = field
        if detail_fields:
            sel.force_navigate(self.DETAIL_LOCATION, context=self._nav_context)
            for field_name, field in detail_fields.iteritems():
                try:
                    self.__data__[field_name] = field.get_value()
                except AttributeError:
                    self.__data__[field_name] = Impossible
        if edit_fields:
            sel.force_navigate(self.EDIT_LOCATION, context=self._nav_context)
            for field_name, field in edit_fields.iteritems():
                try:
                    self.__data__[field_name] = field.get_value()
                except AttributeError:
                    self.__data__[field_name] = Impossible

    def _fill(self, only_updates):
        for field_name, field in self.__fields__.iteritems():
            if not field.can_be_set:
                continue
            value = self.__updates__.get(
                field_name,
                None if only_updates else self.__data__.get(field_name)
            )
            if value is not None:
                field.set_value(value)
                if field_name in self.__updates__:
                    self.__data__[field_name] = value
                    self.__updates__.pop(field_name)

    def go_to_create(self):
        if self.CREATE_LOCATION is None:
            raise Exception("Cannot create such type of resource!")
        sel.force_navigate(self.CREATE_LOCATION)

    def go_to_update(self):
        if self.EDIT_LOCATION is None:
            raise Exception("Cannot update such type of resource!")
        sel.force_navigate(self.EDIT_LOCATION, context=self._nav_context)

    def go_to_detail(self):
        sel.force_navigate(self.DETAIL_LOCATION, context=self._nav_context)

    def create(self):
        if hasattr(self, "pre_create"):
            self.pre_create()
        self.go_to_create()
        self._fill(False)
        sel.click(self.CREATE_BUTTON)
        flash.assert_no_errors()
        if hasattr(self, "post_create"):
            self.post_create()

    def update(self, force=False):
        if not self.needs_update and not force:
            return
        self.go_to_update()
        if hasattr(self, "pre_update"):
            self.pre_update()
        self._fill(True)
        sel.click(self.UPDATE_BUTTON)
        flash.assert_no_errors()
        if hasattr(self, "post_update"):
            self.post_update()

    def delete(self):
        if self.DETAIL_LOCATION is None or self.DELETE_FUNCTION is None:
            raise Exception("Cannot delete such type of resource!")
        if hasattr(self, "pre_delete"):
            self.pre_delete()
        if hasattr(self, "post_delete"):
            # It might address stuff so be sure it is preloaded
            if self.needs_pull:
                self._pull
        self.go_to_detail()
        self.DELETE_FUNCTION()
        flash.assert_no_errors()
        if hasattr(self, "post_delete"):
            self.post_delete()
