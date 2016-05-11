#!/usr/bin/env bash

# pass the cfme qe yamls repo as first argument
QE_YAML_REPO=${1:-../cfme-qe-yamls}

setup_redhat_based_system() {

  echo "setting up the needed system level tools"
  pkcon install -y \
      python-pip gcc postgresql-devel \
      libxml2-devel libxslt-devel \
      zeromq3-devel libcurl-devel \
      redhat-rpm-config  gcc-c++

  echo "user install of the latest pip/virtualenv to avoid old distro packages"
  pip install -U -q --user pip virtualenv
}


append() {
  grep -q "$2" "$1" || (echo "$2" >> $1)
}

setup_virtualenv() {

  echo "Creating Virtualenv"
  virtualenv .cfme_tests

  # make our virtualenv setup a bit nicer, bash only
  echo "Patching ./.cfme_tests/bin/activate"
  append ./.cfme_tests/bin/activate "export PYTHONPATH='`pwd`'"
  append ./.cfme_tests/bin/activate "export PYTHONDONTWRITEBYTECODE=yes"

  . ./.cfme_tests/bin/activate
  PYCURL_SSL_LIBRARY=nss pip install -Uqr ./requirements.txt
  echo "Run '. ./.cfme_tests/bin/activate' to load the virtualenv"
}

link_yamls() {
  ln -s -t "$2" "$1"/*.yaml
  ln -s -t "$2" "$1"/*.eyaml
}

setup_yaml_symlinks() {
  if   [ -d "$QE_YAML_REPO" ]
  then
    echo "Linkin qe repo yaml files"
    link_yamls "$QE_YAML_REPO/complete" conf
  else
    echo "No qe yamls found"
  fi
}




[ -f /etc/redhat-release ] && setup_redhat_based_system
setup_virtualenv
setup_yaml_symlinks
