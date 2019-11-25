#!/bin/bash

RES=16
# Append messages to setup.txt
log () {
    echo "$@" >> $ARTIFACTOR_DIR/setup.txt
}

# Runs given command and appends the stdout and stderr output to setup.txt
run_n_log () {
    echo "cmd: $1" >> $ARTIFACTOR_DIR/setup.txt
    eval "$1" >> $ARTIFACTOR_DIR/setup.txt 2>&1
}

# Shutdown and destroy everything
on_exit () {
    log "Beginning shutdown proc...#~"
    echo $RES > $ARTIFACTOR_DIR/result.txt
    if [ -z "$MASTER_AVAILABLE" ]; then
        log "cfme_tests master not available - exiting..."
        return
    fi
    log "Checking out master branch..."
    git checkout origin/master
    log "Running pip update..."
    (run_pip_update)  # subshell to avoid exit in failure
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
#   $4 optional failure msg to print for an unsuccessful case
do_or_die () {
    cmd=$1
    max_retry=${2:-5}
    sleep_duration=${3:-0}
    try=0
    ret_val=1
    while [ "$ret_val" -ne "0" ]; do
        if [ "$try" -lt "$max_retry" ]; then
            let try+=1;
            log "$cmd"
            log "Running the command - try $try of $max_retry..."
            eval "$cmd"
            let ret_val="$?";
            sleep "$sleep_duration"
        else
            log "Failed to run the command $try times - exiting now..."
            if [ "$4" ]; then
                log "Failure reason: $4"
            fi
            exit
        fi
    done
}


gate() {
	log "gating $2 to $ARTIFACTOR_DIR/$1"
	eval "$2" >> $ARTIFACTOR_DIR/$1 2>&1
	local RES=$?
	if [ "$RES" -ne "0" ]
	then
		log "failed"
		exit $RES
	fi
}

# Runs pip update - optionally can make use of wheelhouse
run_pip_update () {
        export PYCURL_SSL_LIBRARY=openssl
    if [ -n "$WHEEL_HOST_URL" ]; then
        export PIP_TRUSTED_HOST="$WHEEL_HOST" PIP_FIND_LINKS="$WHEEL_HOST_URL"
    fi
    gate "pip_install.txt" "pip3 install -Ur $CFME_REPO_DIR/requirements/frozen.txt --no-cache-dir"
    # ensures entrypoint updates
    run_n_log "pip3 install -e ."
}

trap on_exit EXIT

log "Cloning repos #~"
log "Downloading the credentials..."
do_or_die "GIT_SSL_NO_VERIFY=true git clone $CFME_CRED_REPO $CFME_CRED_REPO_DIR >> $ARTIFACTOR_DIR/setup.txt 2>&1"
mkdir $CFME_REPO_DIR
cd $CFME_REPO_DIR
log "Downloading the master branch of cfme_tests repo..."
do_or_die "git init >> $ARTIFACTOR_DIR/setup.txt 2>&1"

git remote -v |grep "origin"
if [[ "$?" -eq "0" ]]
then
    do_or_die "git remote remove origin  >> $ARTIFACTOR_DIR/setup.txt 2>&1"
fi

do_or_die "git remote add origin $CFME_REPO >> $ARTIFACTOR_DIR/setup.txt 2>&1"
do_or_die "git fetch >> $ARTIFACTOR_DIR/setup.txt 2>&1"
do_or_die "git checkout origin/master >> $ARTIFACTOR_DIR/setup.txt 2>&1"
MASTER_AVAILABLE=true

# Copy the credentials files into the conf folder instead of bothing to make symlinks
cp $CFME_CRED_REPO_DIR/complete/* $CFME_REPO_DIR/conf/

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
cat > $CFME_REPO_DIR/conf/env.local.yaml <<EOF
appliances:
  - hostname: 0.0.0.0
$BROWSER_SECTION

trackerbot:
  username: admin
  url: $TRACKERBOT
EOF

# Export and get into the right place
cd $CFME_REPO_DIR

# Set some basic git configs so git doesn't complain
git config --global user.email "me@dockerbot"
git config --global user.name "DockerBot"

log "#*"

log "Ensuring scripts can be used"
run_n_log "pip3 install -e ."
log "#*"

log "GPG Checking #~"
# Get the GPG-Keys
gate "get_keys.txt" "do_or_die /get_keys.py 5 1"

# die on errors
set -e

log "#*"
# If we are given a PR number, then checkout and merge the PR, if not then just check out the branch
# note that we DO NOT merge.
if [ -n "$CFME_PR" ]; then
    log "Checking out PR $CFME_PR"
    git fetch origin refs/pull/$CFME_PR/head:refs/remotes/origin/pr/$CFME_PR
    run_n_log "/verify_commit.py origin/pr/$CFME_PR"
    log "merging against $BASE_BRANCH"
    git fetch origin $BASE_BRANCH
    git checkout origin/$BASE_BRANCH
    run_n_log "git merge --no-ff --no-edit origin/pr/$CFME_PR"
else
    log "Checking out branch $BRANCH"
    run_n_log "git checkout -f $BRANCH"
fi

log "Pip Update #~"
run_pip_update
log "#*"

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
export IP_ADDRESS=$IP_ADDRESS
log "ip_address: $IP_ADDRESS"
export USE_SPROUT=${USE_SPROUT-"no"}
log "use_sprout: $USE_SPROUT"

# Now fill out the env yaml with ALL THE THINGS
rm $CFME_REPO_DIR/conf/env.local.yaml

if [ "$USE_SPROUT" == "no" ]
then
    HOSTNAME="$IP_ADDRESS"
else
    HOSTNAME="SPROUT_SHOULD_OVERRIDE_THIS"
fi

cat >> $CFME_REPO_DIR/conf/env.local.yaml <<EOF
appliances:
  - hostname: $HOSTNAME
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

log "Artifactor output #~"
run_n_log "cat $CFME_REPO_DIR/conf/env.local.yaml"
log "#*"

# Remove .pyc files
run_n_log "find $CFME_REPO_DIR -name \"*.pyc\" -exec rm -rf {} \;"

set +e


if [ "$USE_SPROUT" = "yes" ];
then
    log "invoking complete collectonly with dummy instance before test"
    gate "collectonly.txt" "py.test --collectonly --dummy-appliance --app-version $SPROUT_GROUP --use-provider complete"

    run_n_log "miq sprout checkout --populate-yaml --user-key sprout" &
    sleep 5
    do_or_die "python3 /check_provisioned.py >> $ARTIFACTOR_DIR/setup.txt" 5 60 "Sprout failed to provision appliance"
else
    log "no sprout used"
    log "invoking complete collectonly with given appliance instance before test"
    gate "collectonly.txt" "py.test --collectonly --use-provider complete"
fi

if [ "$GATE_RHEV" = "yes" ]
then
	log "smoke testing"
	gate "smoke.txt" "py.test -m smoke"
fi
# Finally, run the py.test
log "$PYTEST"

run_n_log "$PYTEST"
RES=$?
