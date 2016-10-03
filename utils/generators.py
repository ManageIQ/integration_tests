# -*- coding: utf-8 -*-
import fauxfactory
import re


def random_vm_name(context=None, max_length=15):
    """Generates a valid VM name that should be valid for any provider we use.

    Constraints:
        * Maximum string length 15 characters (by default)
        * Only [a-z0-9-]

    Args:
        context: If you want to provide some custom string after ``test-`` instead of ``vm``.
            It is recommended to use a maximum of 5 characters with the default 15 character limit.
            Longer strings will be truncated

    Returns:
        A valid randomized VM name.
    """
    template_str_length = 6
    random_chars = 4
    context_length = max_length - random_chars - template_str_length
    context = re.sub(r'[^a-z0-9-]', '', (context or 'vm').lower())[:context_length]
    return 'test-{}-{}'.format(context, fauxfactory.gen_alphanumeric(length=random_chars).lower())
