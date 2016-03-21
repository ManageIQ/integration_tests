#!/usr/bin/env bash

echo "setting up the needed system level tools"
pkcon install -y \
    python-pip gcc postgresql-devel \
    libxml2-devel libxslt-devel \
    zeromq3-devel libcurl-devel \
    redhat-rpm-config

echo "user install of the latest pip/virtualenv to avoid old distro packages"
pip install -U --user pip virtualenv

echo "Creating Virtualenv"
virtualenv .cfme_tests

# make our virtualenv setup a bit nicer, bash only
echo "export PYTHONPATH='`pwd`'" | tee -a ./.cfme_tests/bin/activate
echo "export PYTHONDONTWRITEBYTECODE=yes" | tee -a ./.cfme_tests/bin/activate

. ./.cfme_tests/bin/activate
PYCURL_SSL_LIBRARY=nss pip install -Ur ./requirements.txt
echo "Run '. ./.cfme_tests/bin/activate' to load the virtualenv"
