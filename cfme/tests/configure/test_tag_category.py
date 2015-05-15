# -*- coding: utf-8 -*-
import fauxfactory
from cfme.configure.configuration import Category
from utils.update import update
from utils.randomness import generate_lowercase_random_string


def test_category_crud():
    cg = Category(name=generate_lowercase_random_string(size=8),
                  description=fauxfactory.gen_alphanumeric(32),
                  display_name=fauxfactory.gen_alphanumeric(32))
    cg.create()
    with update(cg):
        cg.description = fauxfactory.gen_alphanumeric(32)
    cg.delete(cancel=False)
