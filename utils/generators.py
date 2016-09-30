# -*- coding: utf-8 -*-
import fauxfactory
import re


def random_vm_name(context=None):
    """Generates a valid VM name that should be valid for any provider we use.

    Constraints:
        * Maximum string length 39 characters
        * Only [a-z0-9-]

    Args:
        context: If you want to provide some custom string after ``test-`` instead of ``vm``

    Returns:
        A valid randomized VM name.
    """
    context = re.sub(r'[^a-z0-9-]', '', (context or 'vm').lower())[:27]
    return 'test-{}-{}'.format(context, fauxfactory.gen_alphanumeric(length=6).lower())
