ManageIQ - Integration tests
============================

[![Code Health](https://landscape.io/github/ManageIQ/integration_tests/master/landscape.svg?style=flat-square)](https://landscape.io/github/ManageIQ/integration_tests/master)
[![Dependency Status](https://gemnasium.com/ManageIQ/integration_tests.svg)](https://gemnasium.com/ManageIQ/integration_tests)
[![Join the public chat at https://gitter.im/ManageIQ/integration_tests](https://badges.gitter.im/ManageIQ/integration_tests.svg)](https://gitter.im/ManageIQ/integration_tests?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
[![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](http://www.gnu.org/licenses/gpl-2.0)

Docs and guides
--------------------
- [Getting Started](http://cfme-tests.readthedocs.org/getting_started.html)
- [Developer Guidelines](http://cfme-tests.readthedocs.org/guides/dev_guide.html)
- [linty freshness](http://cfme-tests.readthedocs.org/guides/lint.html)
- [Selenium over VNC](http://cfme-tests.readthedocs.org/guides/vnc_selenium.html)
- [Setting up Sublime Text Editor](http://cfme-tests.readthedocs.org/guides/editors.html)
- [Setting up Emacs](http://cfme-tests.readthedocs.org/guides/editors.html)
- [PR Review Process](https://github.com/ManageIQ/integration_tests/wiki/PR-Process)

--Ubuntu Evironment Notes:
Missing Dependencies for quick start script
 #python3 -m cfme.scripting.quickstart
Issues encountered after running quickstart on Ubuntu.
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/root/repos/integration_tests/.cfme_venv/lib/python3.6/site-packages/curl/__init__.py", line 7, in <module>
    import sys, pycurl
ImportError: pycurl: libcurl link-time ssl backend (openssl) is different from compile-time ssl backend (gnutls)
Running command failed!
CalledProcessError(1, ['/root/repos/integration_tests/.cfme_venv/bin/python3', '-c', 'import curl'])
#pip uninstall pycurl
#export PYCURL_SSL_LIBRARY=openssl
#pip install pycurl

Legal
-----

Copyright 2013 Red Hat, Inc. and/or its affiliates.

License: GPL version 2 or any later version (see COPYING or
http://www.gnu.org/licenses/old-licenses/gpl-2.0-standalone.html for
details).
