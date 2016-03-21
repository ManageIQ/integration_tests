#!/bin/bash

# Exit on error
set -e

# Load from YAML
PYTHON_ENV_PATH=\
$(eval readlink -f $(cat ./conf/env.local.yaml | shyaml get-value tmux.PYTHON_ENV_PATH))

CFME_TEST_PATH=\
$(eval readlink -f $(cat ./conf/env.local.yaml | shyaml get-value tmux.CFME_TEST_PATH))

if [ ! -z "$PYTHON_ENV_PATH" ] && [ -d "$PYTHON_ENV_PATH" ] \
  && [ ! -z "$CFME_TEST_PATH" ] && [ -d "$CFME_TEST_PATH" ]
  then
  echo "cfme_test: $CFME_TEST_PATH"
  echo "virtualenv: $PYTHON_ENV_PATH"
else
  echo "Missing or invalid YAML data!"
  echo "Please ensure the 'tmux' section exist and is properly configured."
  exit
fi

# More information on DockerBot can be found
# https://github.com/RedHatQE/cfme_tests/blob/master/scripts/dockerbot/README.md
if [ `systemctl is-active docker` != "active" ]
  then
  echo "Starting Docker..."
  systemctl start docker
  Exit_Code=`echo $?`
else
  echo "Docker already running"
fi

source "$PYTHON_ENV_PATH/activate"

# check for latest
BASE_IMAGE="cfmeqe/sel_ff_chrome"
REGISTRY="docker.io"
IMAGE="$REGISTRY/$BASE_IMAGE"

CID=$(docker ps | grep $BASE_IMAGE | awk '{print $1}')
docker pull $IMAGE > /dev/null

if [ -z "$CID" ]
  then
    echo "Starting CFME container..."
    cd $CFME_TEST_PATH
    python scripts/dockerbot/sel_container.py --watch --webdriver 4444 &
    sleep 20s
fi


# tmux the rest of the things
# setup tmux session
tmux new -s cfme_tests -d
tmux select-layout -t cfme_tests even-vertical
tmux split-window -v -t cfme_tests
tmux select-layout -t cfme_tests even-vertical
tmux split-window -v -t cfme_tests

# tail CFME log
tmux send-keys -t cfme_tests:0.0 "tail -f $CFME_TEST_PATH/log/cfme.log" C-m

# setup test run, does not execute the last command
# tmux send-keys -t cfme_tests:0.1 "source $PYTHON_ENV_PATH/activate" C-m
tmux send-keys -t cfme_tests:0.1 "cd $CFME_TEST_PATH" C-m

# you'll need to change to the test pane and hit enter to execute test
tmux send-keys -t cfme_tests:0.1 'py.test -k test_bad_password cfme/test/test_login.py'

# attach to tmux cfme_tests window
tmux attach -t cfme_tests
