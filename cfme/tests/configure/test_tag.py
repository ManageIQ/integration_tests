# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.configure.configuration import Category, Tag
from utils.update import update
from utils.randomness import generate_lowercase_random_string


@pytest.yield_fixture
def category():
    cg = Category(name=generate_lowercase_random_string(size=8),
                  description=fauxfactory.gen_alphanumeric(32),
                  display_name=fauxfactory.gen_alphanumeric(32))
    cg.create()
    yield cg
    cg.delete()


def test_tag_crud(category):
    tag = Tag(name=generate_lowercase_random_string(size=8),
              display_name=fauxfactory.gen_alphanumeric(32),
              category=category)
    tag.create()
    with update(tag):
        tag.display_name = fauxfactory.gen_alphanumeric(32)
    tag.delete(cancel=False)
