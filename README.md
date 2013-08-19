cfme_tests
==============

CloudForms: Management Engine Tests

Setup:

1. Copy credentials.yaml.template, mozwebqa.cfg.template, pytest.ini.template from cfme_pages project, and remove the .template extension.
2. Edit to reflect your environment (these should NOT be checked in to source control)
        *In credentials.yaml:
                *username: Your username, used to log into cfme.
                *password: Your password, used to log into cfme.
        *In mozwebqa.cfg:
                *baseurl: URL, where to find running version of cfme
3. Create a virtualenv to run pytest from
   * easy_install virtualenv (yum install python-virtualenv also works for those preferring rpm)
   * virtualenv <name>
   * source <name>/bin/activate
4. sudo yum install gcc postgresql-devel libxml2-devel libxslt-devel
5. pip install -Ur /path/to/cfme_tests/requirements.txt
6. When tests are run in cfme_tests, the system will look for the cfme_pages repo in 4 locations. If they are not there, PYTHONPATH must be set.
    1. $(cwd)/cfme_pages
    2. $(cwd)/../cfme_pages
    3. ${HOME}/workspace/cfme_pages
    4. ${HOME}/cfme_pages
7. py.test --driver=firefox --credentials=credentials.yaml --untrusted
8. Some of the items in the previous step can be put into your environment, and into pytest.ini so you can then just run py.test. That exercise is left for the reader.

To setup up for chrome:

1. Download from http://code.google.com/p/chromedriver/downloads/list. Use the latest available for your arch. 
2. Unzip that file to somewhere on your path.
3. Substitue --driver=firefox with --driver=chrome

To use the Database fixture:

1. Add --cfmedburl=postgres://[username]:[password]@[appliance ip]:5432/vmdb_production to your command line.
