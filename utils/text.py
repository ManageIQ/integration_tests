#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import re


def normalize_text(text):
    """ Normalizes text that it can be better compared.

    Turns:
        Un-Tag Virtual Machine
        into
        untag_virtual_machine

    Args:
        text: Text to normalize

    """
    text = re.sub(r"[)(-]", "", text.strip().lower().replace("&", " and "))
    return "_".join([field.strip() for field in re.split(r"\s+", text)])
