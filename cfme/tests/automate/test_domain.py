# -*- coding: utf-8 -*-
import pytest

pytestmark = [pytest.mark.skip(reason='Currently unimplemented'), pytest.mark.tier(2)]


def test_domain_crud():
    """Domain CRUD test:

    Steps:
        * Creating a new domain with a unique name must not fail.
        * Given an already existing domain it must be possible to edit its name.
        * Given an already existing domain it must be possible to delete it.
    """
    pass


def test_domain_create_duplicate_name():
    """Creating a new domain that has the same name as any of already existing domains must fail."""
    pass


def test_domain_create_disabled():
    """Creating a disabled domain must indicate its disabled status in the UI."""
    pass


def test_domain_lock_unlock():
    """Given an already created domain, locking it must indicate the locked status in the UI and it
    must become uneditable at all levels. Given a locked custom domain, it must be possible to
    unlock it and restore the edit functionality."""
    pass


def test_domain_lock_disabled():
    """Given an already created domain that is disabled, locking it must indicate the locked and
    disabled status in the UI and it must become uneditable at all levels."""
    pass


def test_domain_edit_description():
    """Given an already existing domain it must be possible to edit its description."""
    pass


def test_domain_edit_enabled():
    """Given an already existing domain it must be possible to edit its enabled status."""
    pass


def test_domain_cannot_edit_builtin():
    """Editing of a builtin domain like ManageIQ or RedHat must not be possible at any level."""
    pass


def test_domain_cannot_delete_builtin():
    """Deleting of a builtin domain like ManageIQ or RedHat must not be possible."""
    pass
