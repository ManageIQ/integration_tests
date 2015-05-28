# -*- coding: utf-8 -*-
import fauxfactory


def generate_lowercase_random_string(size=8):
    return fauxfactory.gen_alphanumeric(size).lower()
