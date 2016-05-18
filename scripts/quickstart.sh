#!/usr/bin/env bash


setup_redhat_based_system() {

  echo "setting up the needed system level tools"
  pkcon install -y \
      python-pip gcc postgresql-devel \
      libxml2-devel libxslt-devel \
      zeromq3-devel libcurl-devel \
      redhat-rpm-config gcc-c++

  echo "user install of the latest pip/virtualenv to avoid old distro packages"
  pip install -U -q --user pip virtualenv
}


patch_activate() {
  if grep -q  PYTHONDONTWRITEBYTECODE ./.cfme_tests/bin/activate
  then
    echo "Activate Script already patched"
  else
    echo "Patching Activate Script"
    cat >> ./.cfme_tests/bin/activate <<EOF;

    export PYTHONDONTWRITEBYTECODE=yes
    if [[ $PYTHONPATH ]]
    then
      PYTHONPATH+=":`pwd`"
    else
      PYTHONPATH="`pwd`"
    fi
EOF
  fi
}


setup_virtualenv() {

  local PIP_ARGS=""
  if [ ! -d .cfme_tests ]
  then
    echo "Creating Virtualenv"
    virtualenv .cfme_tests
  else
    echo "Reusing Virtualenv"
    # we think update is fast
    PIP_ARGS=-q
  fi

  patch_activate

  . ./.cfme_tests/bin/activate
  PYCURL_SSL_LIBRARY=nss pip install -r ./requirements.txt $PIP_ARGS

  echo "Run '. ./.cfme_tests/bin/activate' to load the virtualenv"
}


setup_yaml_symlinks() {

  if  [ -d "$1" ]
  then
    echo "Linkin qe repo yaml files"
    find conf/ -type l -delete
    ln -s -t conf "$1"/complete/*.yaml
    ln -s -t conf "$1"/complete/*.eyaml
  else
    echo "No qe yamls found in $1"
  fi
}


[ -f /etc/redhat-release ] && setup_redhat_based_system
setup_virtualenv
setup_yaml_symlinks $(realpath ${1:-../cfme-qe-yamls})
