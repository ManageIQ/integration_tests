# Shutdown and destroy everything
on_exit () {
    echo "Beginning shutdown proc..." >> $ARTIFACTOR_DIR/setup.txt
    echo $RES > $ARTIFACTOR_DIR/result.txt
    if [ -n "$POST_TASK" ]; then
	if [ $RES -eq 0 ]; then
            OUT_RESULT="passed"
	else
            OUT_RESULT="failed"
	fi
	echo "Posting result..." >> $ARTIFACTOR_DIR/setup.txt
	/post_result.py $POST_TASK $OUT_RESULT >> $ARTIFACTOR_DIR/setup.txt 2>&1
	echo $? >> $ARTIFACTOR_DIR/setup.txt
    fi
    if [ -n "$PROVIDER" ]; then
	echo "Destroying appliance..." >> $ARTIFACTOR_DIR/setup.txt
	scripts/clone_template.py --provider $PROVIDER --vm_name $VM_NAME --destroy >> $ARTIFACTOR_DIR/setup.txt 2>&1
    fi
}

trap on_exit EXIT

# Download the credentials and the master branch of the cfme_tests repo
GIT_SSL_NO_VERIFY=true git clone $CFME_CRED_REPO $CFME_CRED_REPO_DIR >> $ARTIFACTOR_DIR/setup.txt 2>&1
git clone $CFME_REPO $CFME_REPO_DIR >> $ARTIFACTOR_DIR/setup.txt 2>&1

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
# It's not a mistake to run this twice ;)
/get_keys.py >> $ARTIFACTOR_DIR/setup.txt 2>&1

# die on errors
set -e
/get_keys.py >> $ARTIFACTOR_DIR/setup.txt 2>&1

# If we are given a PR number, then checkout and merge the PR, if not then just check out the branch
# note that we DO NOT merge.
if [ -n "$CFME_PR" ]; then
    echo "Checking out PR $CFME_PR" >> $ARTIFACTOR_DIR/setup.txt
    git fetch origin refs/pull/$CFME_PR/head:refs/remotes/origin/pr/$CFME_PR;
    /verify_commit.py origin/pr/$CFME_PR >> $ARTIFACTOR_DIR/setup.txt 2>&1
    git fetch origin master; git checkout origin/master; git merge --no-ff --no-edit origin/pr/$CFME_PR >> $ARTIFACTOR_DIR/setup.txt 2>&1
else
    echo "Checking out branch $BRANCH" >> $ARTIFACTOR_DIR/setup.txt
    git checkout -f $BRANCH >> $ARTIFACTOR_DIR/setup.txt 2>&1
fi

# If specified, update PIP
if [ -n "$UPDATE_PIP" ]; then
    pip install -Ur $CFME_REPO_DIR/requirements.txt >> $ARTIFACTOR_DIR/setup.txt 2>&1
fi

# If asked, provision the appliance, and update the APPLIANCE variable
if [ -n "$PROVIDER" ]; then
    echo "Provisioning appliance..." >> $ARTIFACTOR_DIR/setup.txt
    scripts/clone_template.py --outfile /appliance_ip --provider $PROVIDER --template $TEMPLATE --vm_name $VM_NAME --configure >> $ARTIFACTOR_DIR/setup.txt 2>&1
    cat /appliance_ip >> $ARTIFACTOR_DIR/setup.txt
    IP_ADDRESS=$(cat /appliance_ip | cut -d= -f2)
    APPLIANCE=https://$IP_ADDRESS
fi
echo $APPLIANCE >> $ARTIFACTOR_DIR/setup.txt

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

cat $CFME_REPO_DIR/conf/env.local.yaml >> $ARTIFACTOR_DIR/setup.txt

# Finally, run the py.test
echo "$PYTEST" >> $ARTIFACTOR_DIR/setup.txt
eval $PYTEST >> $ARTIFACTOR_DIR/setup.txt 2>&1
RES=$?


