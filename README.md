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

Running the docker container for development
--------------------------------------------

- Elsewhere, run the ManageIQ application with `bundle exec rails s`
- Checkout the integration_tests source
  - `git clone git@github.com:ManageIQ/integration_tests.git -o upstream`
  - `cd integration_tests`
- Checkout the dockerization PR
  - `git fetch upstream pull/5967/head:dockerize`
  - `git checkout dockerize`
- Configure the integration_tests
  - Create a conf/env.yaml from conf/env.yaml.template
    - Change the appliance section to:
      ```yaml
      appliances:
      - hostname: host.docker.internal
        ui_protocol: http
        ui_port: 3000
        is_dev: True
      ```
    - Change the `browser/webdriver_options/desired_capabilities/browserName` to `firefox`
  - Create a conf/credentials.yaml from conf/credentials.yaml.template
    - Set the `username` and `password` fields for the `default`, `bugzilla`, and `database` sections
- Run the docker container
  - `docker run --rm -it --mount type=bind,source="$(pwd)",target=/projects/cfme_env/cfme_vol -p5999:5999 fryguy9/integration_tests cfme/tests/test_login.py -k test_login -v`
  - If you have a VNC viewer, point it to localhost:5999 to watch the tests run live!

Legal
-----

Copyright 2013 Red Hat, Inc. and/or its affiliates.

License: GPL version 2 or any later version (see COPYING or
http://www.gnu.org/licenses/old-licenses/gpl-2.0-standalone.html for
details).
