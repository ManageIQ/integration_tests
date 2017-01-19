#!/bin/sh

# URL shortener
# https://github.com/blog/985-git-io-github-url-shortener

if [ -z ${PROJECTS} ];then
  echo -e "PROJECTS variable not set.\n
This variable sets path to where integration_tests will be installed. Export this variable and re-run this script again."

else

  export CFME_TESTS="${PROJECTS}/integration_tests_files"
  mkdir -p ${CFME_TESTS}; cd ${CFME_TESTS}

  echo -e "Cloning integration_tests repo...\n
-------------------------"
  git clone git://github.com/ManageIQ/integration_tests.git

  echo -e "Fething unmerged PR...[TESTING]\n
-------------------------"
  cd integration_tests; git fetch origin pull/3254/head:integration_tests_container

  echo -e "Switching to branch from PR...[TESTING]\n
-------------------------"
  git checkout integration_tests_container

  echo -e "Creating symbolic link for wrapper script\n
-------------------------"
  cd ..; ln -s integration_tests/integration_tests_install/integration_tests_init.sh .

  echo  -e "integration_tests have been successfully cloned.\n
If you have any custom YAML files you want to use, create new directory in ${CFME_TESTS} andcopy them here, e.g.:

  mkdir ${CFME_TESTS}/my_custom_yaml_files
  cp -r /<path to custom yamls>/*.*y*ml ${CFME_TESTS}/my_custom_yaml_files

  You can configure your environment now by executing:

  cd ${CFME_TESTS}/integration_tests
  ./integration_tests_init.sh init
  "

  cd ${CFME_TESTS}
fi
