# -*- coding: utf-8 -*-
import command
import os
import pytest
import re

from utils import diaper

pytestmark = [pytest.mark.ignore_stream("5.2", "5.3")]


def test_i18n(request, random_string, ssh_client, soft_assert):
    lang_dirs = filter(
        lambda d: re.search(r"/[a-z]{2}$", d),
        ssh_client.run_command("ls -d /var/www/miq/vmdb/config/locales/*")[-1].split("\n"))
    lang_codes = map(lambda directory: re.sub(r"^.*?/([a-z]{2})$", r"\1", directory), lang_dirs)
    tmpfilename = "/tmp/{}.po".format(random_string)
    request.addfinalizer(lambda: diaper(lambda: os.unlink(tmpfilename)))
    for lang_code in lang_codes:
        ssh_client.get_file(
            "/var/www/miq/vmdb/config/locales/{}/manageiq.po".format(lang_code), tmpfilename)
        result = command.run(["pofilter", tmpfilename])
        soft_assert(
            len(result.output.strip()) == 0, "{} language test failed!".format(lang_code))
        os.unlink(tmpfilename)
