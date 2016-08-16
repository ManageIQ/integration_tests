#!/usr/bin/env python
# -*- coding: utf-8 -*-
######################################################################
#  Written by Kevin L. Sitze on 2006-12-03
#  This code may be used pursuant to the MIT License.
######################################################################
# PEP8 applied and some things tweaked by Milan Falesnik

from __future__ import unicode_literals
import re

__all__ = ('quote',)

_bash_reserved_words = {
    'case',
    'coproc',
    'do',
    'done',
    'elif',
    'else',
    'esac',
    'fi',
    'for',
    'function',
    'if',
    'in',
    'select',
    'then',
    'until',
    'while',
    'time'
}

####
#  _quote_re1 escapes double-quoted special characters.
#  _quote_re2 escapes unquoted special characters.

_quote_re1 = re.compile(r"([\!\"\$\\\`])")
_quote_re2 = re.compile(r"([\t\ \!\"\#\$\&\'\(\)\*\:\;\<\>\?\@\[\\\]\^\`\{\|\}\~])")


def quote(*args):
    """Combine the arguments into a single string and escape any and
    all shell special characters or (reserved) words.  The shortest
    possible string (correctly quoted suited to pass to a bash shell)
    is returned.
    """
    s = "".join(args)
    if s in _bash_reserved_words:
        return "\\" + s
    elif s.find('\'') >= 0:
        s1 = '"' + _quote_re1.sub(r"\\\1", s) + '"'
    else:
        s1 = "'" + s + "'"
    s2 = _quote_re2.sub(r"\\\1", s)
    if len(s1) <= len(s2):
        return s1
    else:
        return s2
