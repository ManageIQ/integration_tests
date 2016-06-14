#!/bin/bash

# Exit on error
set -e

# Load from YAML
PYTHON_ENV_PATH=\
$(readlink -f "$(shyaml get-value tmux.PYTHON_ENV_PATH < ./conf/env.local.yaml)")

CFME_TEST_PATH=\
$(readlink -f "$(shyaml get-value tmux.CFME_TEST_PATH < ./conf/env.local.yaml)")

if [ -n "$PYTHON_ENV_PATH" ] && [ -d "$PYTHON_ENV_PATH" ] \
  && [ -n "$CFME_TEST_PATH" ] && [ -d "$CFME_TEST_PATH" ]
  then
  echo "cfme_test: $CFME_TEST_PATH"
  echo "virtualenv: $PYTHON_ENV_PATH"
else
  echo "Missing or invalid YAML data!" >&2
  echo "Please ensure the 'tmux' section exist and is properly configured." >&2
  exit 1
fi

# More information on DockerBot can be found
# https://github.com/RedHatQE/cfme_tests/blob/master/scripts/dockerbot/README.md
if [ "$(systemctl is-active docker)" != "active" ]
  then
  echo "Starting Docker..."
  systemctl start docker
else
  echo "Docker already running"
fi

# check for latest
BASE_IMAGE="cfmeqe/sel_ff_chrome"
REGISTRY="docker.io"
IMAGE="$REGISTRY/$BASE_IMAGE"

CID="$(docker ps | grep "$BASE_IMAGE" | { read id _; echo "$id"; })"
docker pull $IMAGE > /dev/null

# tmux the rest of the things
VEN_ACTIVATE="source $PYTHON_ENV_PATH/activate"
USER_SHELL="$(getent passwd "$(id -u)")"
USER_SHELL="${USER_SHELL##*:}"

if [ -z "$CID" ]
  then
    echo "Starting CFME container..."
    tmux new-session -s cfme_tests -n container -d \
      "$VEN_ACTIVATE; \
      cd $CFME_TEST_PATH; \
      python scripts/dockerbot/sel_container.py --watch --webdriver 4444; \
      exec $USER_SHELL"
    sleep 20s
    tmux new-window -t cfme_tests "$VEN_ACTIVATE; exec $USER_SHELL"
    window=1
  else
    tmux new-session -s cfme_tests -d "$VEN_ACTIVATE; exec $USER_SHELL"
    window=0
fi

tmux select-layout -t cfme_tests even-vertical
tmux split-window -v -t cfme_tests -c "$CFME_TEST_PATH" "$VEN_ACTIVATE; exec $USER_SHELL"
tmux select-layout -t cfme_tests even-vertical
tmux split-window -v -t cfme_tests "$VEN_ACTIVATE; exec $USER_SHELL"

# let the shells start before sending any input
sleep 0.5

# tail CFME log
tmux send-keys -t cfme_tests:$window.0 "tail -f $CFME_TEST_PATH/log/cfme.log" C-m

# you'll need to change to the test pane and hit enter to execute test
tmux send-keys -t cfme_tests:$window.1 "py.test -k test_bad_password cfme/tests/test_login.py"

# attach to tmux cfme_tests window
tmux attach-session -t cfme_tests
