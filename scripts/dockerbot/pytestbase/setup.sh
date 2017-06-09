#!/bin/bash

RES=16
# Append messages to setup.txt
LOGFILE=/integration_tests/log/setup.txt



log () {
    echo "$@" | tee -a $LOGFILE
}

# Runs given command and appends the stdout and stderr output to setup.txt
run_n_log () {
    (set -o pipefail; eval "$1"  2>&1 | tee -a $LOGFILE)
}
# Shutdown and destroy everything
on_exit () {
    log "Beginning shutdown proc...#~"
    echo $RES > /log_depot/result.txt
    log "Checking out master branch..."
    git checkout origin/master
    
    log "#*"
    if [ -n "$POST_TASK" ]; then
        [ $RES -eq 0 ] || [ $RES -eq 5 ] && OUT_RESULT="passed" || OUT_RESULT="failed"
        log "Posting result..."
        run_n_log "/post_result.py $POST_TASK $OUT_RESULT"
        log $?
    fi
    if [ -n "$PROVIDER" ]; then
        log "Destroying appliance..."
        run_n_log "scripts/clone_template.py --provider $PROVIDER --vm_name $VM_NAME --destroy"
    fi
}

# Tries to run the given command n times - exits if not successful
# Args:
#   $1 cmd - Command to run
#   $2 max_retry - Maximum num of attempts to run the command; defaults to 5
#   $3 sleep_duration - duration to sleep between attempts; defaults to 0
do_or_die () {
    cmd=$1
    max_retry=${2:-5}
    sleep_duration=${3:-0}
    try=0
    ret_val=1
    while [ "$ret_val" -ne "0" ]; do
        if [ "$try" -lt "$max_retry" ]; then
            let try+=1;
            log "Running the command - try $try of $max_retry..."
            run_n_log "$cmd"
            let ret_val="$?";   
            sleep "$sleep_duration"
        else
            log "$cmd"
            log "Failed to run the command $try times - exiting now..."
            exit
        fi
    done
}


trap on_exit EXIT

log "Cloning repos #~"
log "Downloading the credentials..."
# TODO: turn this into a volume
do_or_die "GIT_SSL_NO_VERIFY=true git clone $CFME_CRED_REPO /cfme-qe-yamls"

log "Downloading the master branch of cfme_tests repo..."
do_or_die "git remote add repo_under_test $CFME_REPO "
do_or_die "git fetch repo_under_test"

# If we are using Wharf then setup appropriately, otherwise use the the usual command executor
if [ -n "$WHARF" ]; then
    BROWSER_SECTION="browser:
    webdriver_wharf: $WHARF
    webdriver_options:
        keep_alive: True
        desired_capabilities:
            platform: LINUX
            browserName: '$BROWSER'"
else
    BROWSER_SECTION="browser:
    webdriver_options:
        command_executor: http://$SELFF_PORT_4444_TCP_ADDR:$SELFF_PORT_4444_TCP_PORT/wd/hub
        keep_alive: True
        desired_capabilities:
            platform: LINUX
            browserName: '$BROWSER'"
fi

# Put a basic config file so that the db module doesn't fall over
cat > /integration_tests/conf/env.local.yaml <<EOF
base_url: https://0.0.0.0
$BROWSER_SECTION

trackerbot:
  username: admin
  url: $TRACKERBOT
EOF



log "#*"


log "quickstart reexecute #~"
. /cfme_venv/bin/activate
run_n_log "python -m cfme.scripting.quickstart"
log "#*"

log "GPG Checking #~"
# Get the GPG-Keys
do_or_die "/get_keys.py" 5 1

# die on errors
set -e

log "#*"
# If we are given a PR number, then checkout and merge the PR, if not then just check out the branch
# note that we DO NOT merge.
if [ -n "$CFME_PR" ]; then
    log "Checking out PR $CFME_PR"
    git fetch repo_under_test refs/pull/$CFME_PR/head:refs/remotes/repo_under_test/pr/$CFME_PR
    run_n_log "/verify_commit.py origin/pr/$CFME_PR"
    log "merging against $BASE_BRANCH"
    git fetch repo_under_test $BASE_BRANCH
    git checkout -b branch-under-test repo_under_test/$BASE_BRANCH
    run_n_log "git merge --no-ff --no-edit repo_under_test/pr/$CFME_PR"
else
    log "Checking out branch $BRANCH"
    run_n_log "git checkout -f $BRANCH"
fi



# If asked, provision the appliance, and update the APPLIANCE variable
if [ -n "$PROVIDER" ]; then
    log "Provisioning appliance... #~"
    run_n_log "scripts/clone_template.py --outfile /appliance_ip --provider $PROVIDER --template $TEMPLATE --vm_name $VM_NAME --configure"
    run_n_log "cat /appliance_ip"
    IP_ADDRESS=$(cat /appliance_ip | cut -d= -f2)
    APPLIANCE=https://$IP_ADDRESS
    log "#*"
fi
export APPLIANCE=${APPLIANCE-"None"}
log "appliance: $APPLIANCE"

# Now fill out the env yaml with ALL THE THINGS
cat > /integration_tests/conf/env.local.yaml <<EOF
base_url: $APPLIANCE
$BROWSER_SECTION

artifactor:
    log_dir: /log_depot/artifacts
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
            only_failed: True

mail_collector:
    ports:
        smtp: $SMTP
        json: $JSON


trackerbot:
  username: admin
  url: $TRACKERBOT
EOF

log "Artifactor output #~"
run_n_log "cat /integration_tests/conf/env.local.yaml"
log "#*"

# Remove .pyc files
run_n_log "find /integration_tests/ -name \"*.pyc\" -exec rm -rf {} \;"

set +e

# Finally, run the py.test
log "$PYTEST"
run_n_log "$PYTEST"
RES=$?
