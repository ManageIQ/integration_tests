RES=16
# Append messages to setup.txt
log () {
    echo $@ >> $ARTIFACTOR_DIR/setup.txt
}

# Runs given command and appends the stdout and stderr output to setup.txt
run_n_log () {
    eval "$1" >> $ARTIFACTOR_DIR/setup.txt 2>&1
}

# Shutdown and destroy everything
on_exit () {
    log "Beginning shutdown proc..."
    echo $RES > $ARTIFACTOR_DIR/result.txt
    if [ -z "$MASTER_AVAILABLE" ]; then
        log "cfme_tests master not available - exiting..."
        return
    fi
    log "Checking out master branch..."
    git checkout origin/master
    log "Running pip update..."
    run_pip_update
    if [ -n "$POST_TASK" ]; then
        [ $RES -eq 0 ] && OUT_RESULT="passed" || OUT_RESULT="failed"
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
            eval "$cmd"
            let ret_val="$?";
            sleep "$sleep_duration"
        else
            log "Failed to run the command $try times - exiting now..."
            exit
        fi
    done
}

# Runs pip update - optionally can make use of wheelhouse
run_pip_update () {
    if [ -n "$WHEEL_HOST_URL" ]; then
        run_n_log "PYCURL_SSL_LIBRARY=nss pip install --trusted-host $WHEEL_HOST -f $WHEEL_HOST_URL -Ur $CFME_REPO_DIR/requirements.txt --no-cache-dir"
    else
        run_n_log "PYCURL_SSL_LIBRARY=nss pip install -Ur $CFME_REPO_DIR/requirements.txt --no-cache-dir"
    fi
}

trap on_exit EXIT

log "Downloading the credentials..."
do_or_die "GIT_SSL_NO_VERIFY=true git clone $CFME_CRED_REPO $CFME_CRED_REPO_DIR >> $ARTIFACTOR_DIR/setup.txt 2>&1"
mkdir $CFME_REPO_DIR
cd $CFME_REPO_DIR
log "Downloading the master branch of cfme_tests repo..."
do_or_die "git init >> $ARTIFACTOR_DIR/setup.txt 2>&1"
do_or_die "git remote add origin $CFME_REPO >> $ARTIFACTOR_DIR/setup.txt 2>&1"
do_or_die "git fetch >> $ARTIFACTOR_DIR/setup.txt 2>&1"
do_or_die "git checkout -t origin/master >> $ARTIFACTOR_DIR/setup.txt 2>&1"
MASTER_AVAILABLE=true

# Copy the credentials files into the conf folder instead of bothing to make symlinks
cp $CFME_CRED_REPO_DIR/complete/* $CFME_REPO_DIR/conf/

# If we are using Wharf then setup appropriately, otherwise use the the usual command executor
if [ -n "$WHARF" ]; then
    BROWSER_SECTION="browser:
    webdriver_wharf: $WHARF
    webdriver_options:
        desired_capabilities:
            platform: LINUX
            browserName: '$BROWSER'"
else
    BROWSER_SECTION="browser:
    webdriver_options:
        command_executor: http://$SELFF_PORT_4444_TCP_ADDR:$SELFF_PORT_4444_TCP_PORT/wd/hub
        desired_capabilities:
            platform: LINUX
            browserName: '$BROWSER'"
fi

# Put a basic config file so that the db module doesn't fall over
cat > $CFME_REPO_DIR/conf/env.local.yaml <<EOF
base_url: https://0.0.0.0
$BROWSER_SECTION

trackerbot:
  username: admin
  url: $TRACKERBOT
EOF

# Export and get into the right place
export PYTHONPATH=$CFME_REPO_DIR
cd $CFME_REPO_DIR

# Set some basic git configs so git doesn't complain
git config --global user.email "me@dockerbot"
git config --global user.name "DockerBot"

# Get the GPG-Keys
do_or_die "/get_keys.py >> $ARTIFACTOR_DIR/setup.txt 2>&1" 5 1

# die on errors
set -e

# If we are given a PR number, then checkout and merge the PR, if not then just check out the branch
# note that we DO NOT merge.
if [ -n "$CFME_PR" ]; then
    log "Checking out PR $CFME_PR"
    git fetch origin refs/pull/$CFME_PR/head:refs/remotes/origin/pr/$CFME_PR
    run_n_log "/verify_commit.py origin/pr/$CFME_PR"
    git fetch origin master
    git checkout origin/master
    run_n_log "git merge --no-ff --no-edit origin/pr/$CFME_PR"
else
    log "Checking out branch $BRANCH"
    run_n_log "git checkout -f $BRANCH"
fi

# If specified, update PIP
if [ -n "$UPDATE_PIP" ]; then
    run_pip_update
fi

# If asked, provision the appliance, and update the APPLIANCE variable
if [ -n "$PROVIDER" ]; then
    log "Provisioning appliance..."
    run_n_log "scripts/clone_template.py --outfile /appliance_ip --provider $PROVIDER --template $TEMPLATE --vm_name $VM_NAME --configure"
    run_n_log "cat /appliance_ip"
    IP_ADDRESS=$(cat /appliance_ip | cut -d= -f2)
    APPLIANCE=https://$IP_ADDRESS
fi
export APPLIANCE=${APPLIANCE-"None"}
log $APPLIANCE

# Now fill out the env yaml with ALL THE THINGS
cat > $CFME_REPO_DIR/conf/env.local.yaml <<EOF
base_url: $APPLIANCE
$BROWSER_SECTION

artifactor:
    log_dir: $ARTIFACTOR_DIR
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

run_n_log "cat $CFME_REPO_DIR/conf/env.local.yaml"

set +e

# Finally, run the py.test
log "$PYTEST"
run_n_log "$PYTEST"
RES=$?
