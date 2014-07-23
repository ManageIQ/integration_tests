dockerbot
=========

DockerBot for CFME
------------------

DockerBot is a completely disposable testing framework for CFME-QE. It uses docker to create
separate "selenium" and "pytest" containers. The "selenium" container is maintained at the
docker hub. Currently the "pytest" container is built locally to help keep it up to date
with pip requirements updates. This will take a few minutes the first time, but then only needs
to be run again occasionally.

Getting Started
---------------

### Log depot

To begin with, you will need to define a **log depot**. This is where DockerBot will store all
of the artifacts from artifactor. To do this, create a folder and then apply the following if
you are using SELinux.

`sudo chcon -Rt svirt_sandbox_file_t /path/to/log_depot/`

### Building the pytestbase image

We then need to build the pytest docker container. To do this we need to change directory to the
pytestbase folder which is contained in this repo and run the following.

`docker build -t py_test_base .`

This can be run multiple times if required to update the pip requirements from master.
You may need to use the `--no-cache=true` to tell the build not to use the cached versions
of the previous steps.

### Obtaining the sel_ff_chrome image

Next we need to grab the sel_ff_chrome docker image.

```
$ docker pull cfmeqe/sel_ff_chrome
Pulling repository cfmeqe/sel_ff_chrome
4c6781db3920: Pulling dependent layers
6f18cdca0c75: Pulling dependent layers
511136ea3c5a: Download complete
fd241224e9cf: Download complete
3f2fed40e4b0: Download complete
94aebbf3b4a5: Download complete
49417c3e890e: Download complete
```

Once this has finished, we can use DockerBot to run tests in totally isolated containers.

### Configuration file

Though not necessary, as DockerBot has a complete set of command line options, you should create
a `docker.yaml` file to hold the most common options. This sits in the usual place for CFME
testing framework config files.

An example is below, notice that you can specify as many appliances as you want, and these will
be referred to by name when invoking DockerBot.

```yaml
appliances:
    Downstream: https://xx.xx.xx.xx
    Upstream: https://yy.yy.yy.yy
cfme_cred_repo: https://credentials/yaml/cfme-qe-yamls.git
cfme_cred_repo_dir: /cfme-qe-yamls
cfme_repo: https://github.com/RedHatQE/cfme_tests
cfme_repo_dir: /cfme_tests_te
pytest: -k test_bad_password
branch: origin/master
browser: firefox
selff: cfmeqe/sel_ff_chrome
pytest_con: py_test_base
artifactor_dir: /log_report
log_depot: /home/user/log_depot/
banner: True
gh_token: my_gh_token_for_api
gh_owner: RedHatQE
gh_repo: cfme_tests
```

Running DockerBot
-----------------

`$ scripts/dockerbot/docker_bot.py --appliance-name Downstream --pytest 'py.test -k test_bad_password' --watch --browser 'firefox'`

This spawns two containers a "selenium" one and a "pytest" one. The `watch` option fires up a
VNC viewer. This would run the test against the current master branch as defined in the
docker.yaml. Read on for more advanced options.

### Specific repo/branch testing

Using the commanline options, DockerBot can be told to go to a different CFME repository, such
as your own fork, and run a branch there, an example of this is below.

`$ scripts/docker_bot.py --watch --output --appliance-name Downstream --cfme-repo https://github.com/psav/cfme_tests --branch disable_tracer --pytest 'py.test -k test_bad_password'`

### PR testing

DockerBot has a **PR** option which allows you to ask it to download a PR instead of a branch.
This option will overide the `--branch` option and checkout the latest master and merge the PR
on top. If this fails, the whole container should fail and the test output will indicate as such.

`$ scripts/docker_bot.py --watch --output --appliance-name Downstream --pr 952 --pytest 'py.test -k test_bad_password'`

### Auto Test Generation

DockerBot is able to make educated guesses about which tests need to be run in order to test the PR.
This will not always work, but can be used as a first case approximation. DockerBot will look for
any files in the PR which are in the cfme/tests folder and include those in the run. When this option
is used, the `--pytest` option does not need to be. At the moment, there is no way to pass other options
to pytest when using the `--auto-gen-test` option.

### Update Pip

Currently DockerBot needs to be told if you want to update the pip. This can be done with the
`--update-pip` option.

Firewalling
-----------

If you run with a firewall and wish to do either event or smtp testing, you will need to open up the
required ports on your local machine. Bear in mind also that your DockerBot container will also try
to access these ports, so it may be that you also need to allow connections from the DockerBot
internal subnet to your device network. 

Full DockerBot example
----------------------

In the example below we make use of the `output` option to get the output of the setup.sh script.
There is also an `--update-pip` option which will update the requirements.txt prior to running
the test. This is not performed by default.

```
$ scripts/dockerbot/dockerbot.py --watch --output --appliance-name Downstream --pytest 'py.test -k test_bad_password'
==================================================================
               ____             __             ____        __
     :        / __ \____  _____/ /_____  _____/ __ )____  / /_
   [* *]     / / / / __ \/ ___/ //_/ _ \/ ___/ __  / __ \/ __/
  -[___]-   / /_/ / /_/ / /__/ ,< /  __/ /  / /_/ / /_/ / /_
           /_____/\____/\___/_/|_|\___/_/  /_____/\____/\__/
==================================================================

  APPLIANCE: https://xx.xx.xx.xx (Downstream)
  PYTEST Command: py.test -k test_bad_password
  VNC_PORT: 46518
  REPO: https://github.com/RedHatQE/cfme_tests
  BROWSER: firefox
  BRANCH: origin/master
  LOG_ID: WE4zeGbJ
  JSON: 35758
  SMTP: 45529

  Waiting for container for 10 seconds...
  Initiating VNC watching...

  Press Ctrl+C to kill tests + containers

======================== \/ OUTPUT \/ ============================

Cloning into '/cfme-qe-yamls'...
Cloning into '/cfme_tests_te'...
base_url: https://xx.xx.xx.xx
browser:
    webdriver_options:
        command_executor: http://zz.zz.zz.zz:4444/wd/hub
        desired_capabilities:
            platform: LINUX
            browserName: 'firefox'

artifactor:
    log_dir: /log_report
    per_run: test #test, run, None
    reuse_dir: True
    squash_exceptions: True
    threaded: True
    server_address: 127.0.0.1
    server_enabled: True
    plugins:
        logger:
            enabled: True
            plugin: logger
            level: DEBUG
        filedump:
            enabled: True
            plugin: filedump
        reporter:
            enabled: True
            plugin: reporter
            only_failed: False

mail_collector:
    ports:
        smtp: 45529
        json: 35758
Checking out branch origin/master
Note: checking out 'origin/master'.

You are in 'detached HEAD' state. You can look around, make experimental
changes and commit them, and you can discard any commits you make in this
state without impacting any branches by performing another checkout.

If you want to create a new branch to retain commits you create, you may
do so (now or later) by using -b with the checkout command again. Example:

  git checkout -b new_branch_name

HEAD is now at a3d93d8... Merge pull request #960 from dajohnso/update_enable_int_db
py.test py.test -k test_bad_password
Instance: [merkyl] does not exist, is your configuration correct?
Instance: [video] does not exist, is your configuration correct?
============================= test session starts ==============================
platform linux2 -- Python 2.7.5 -- py-1.4.20 -- pytest-2.5.2
collected 558 items

cfme/tests/test_login.py .

===== 557 tests deselected by "-ktest_bad_password -m 'not long_running'" ======
================== 1 passed, 557 deselected in 30.32 seconds ===================

```