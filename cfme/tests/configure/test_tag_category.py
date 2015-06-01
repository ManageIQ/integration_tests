# -*- coding: utf-8 -*-
import fauxfactory
from cfme.configure.configuration import Category
import pytest
from utils.update import update


@pytest.mark.sauce
def test_category_crud():
    cg = Category(name=fauxfactory.gen_alphanumeric(8).lower(),
                  description=fauxfactory.gen_alphanumeric(32),
                  display_name=fauxfactory.gen_alphanumeric(32))
    cg.create()
    with update(cg):
        cg.description = fauxfactory.gen_alphanumeric(32)
    cg.delete(cancel=False)
