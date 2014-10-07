GIT_SSL_NO_VERIFY=true git clone $CFME_CRED_REPO $CFME_CRED_REPO_DIR >> $ARTIFACTOR_DIR/setup.txt 2>&1
git clone $CFME_REPO $CFME_REPO_DIR >> $ARTIFACTOR_DIR/setup.txt 2>&1
cp $CFME_CRED_REPO_DIR/complete/* $CFME_REPO_DIR/conf/
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

cat > $CFME_REPO_DIR/conf/env.local.yaml <<EOF
base_url: https://0.0.0.0
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

export PYTHONPATH=$CFME_REPO_DIR
cd $CFME_REPO_DIR

if [ -n "$PROVIDER" ]; then
    echo "Provisioning appliance..." >> $ARTIFACTOR_DIR/setup.txt
    scripts/clone_template.py --outfile /appliance_ip --provider $PROVIDER --template $TEMPLATE --vm_name $VM_NAME --configure >> $ARTIFACTOR_DIR/setup.txt 2>&1
    cat /appliance_ip >> $ARTIFACTOR_DIR/setup.txt
    IP_ADDRESS=$(cat /appliance_ip | cut -d= -f2)
    APPLIANCE=https://$IP_ADDRESS
fi
echo $APPLIANCE >> $ARTIFACTOR_DIR/setup.txt

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

git config --global user.email "me@dockerbot"
git config --global user.name "DockerBot"
if [ -n "$CFME_PR" ]; then
    echo "Checking out PR $CFME_PR" >> $ARTIFACTOR_DIR/setup.txt
    git fetch origin refs/pull/$CFME_PR/head:refs/remotes/origin/pr/$CFME_PR; git fetch origin master; git checkout origin/master; git merge --no-ff --no-edit origin/pr/$CFME_PR >> $ARTIFACTOR_DIR/setup.txt 2>&1
else
    echo "Checking out branch $BRANCH" >> $ARTIFACTOR_DIR/setup.txt
    git checkout -f $BRANCH >> $ARTIFACTOR_DIR/setup.txt 2>&1
fi

if [ -n "$UPDATE_PIP" ]; then
    pip install -Ur $CFME_REPO_DIR/requirements.txt >> $ARTIFACTOR_DIR/setup.txt 2>&1
fi
echo py.test "$PYTEST" >> $ARTIFACTOR_DIR/setup.txt
eval $PYTEST >> $ARTIFACTOR_DIR/setup.txt 2>&1
RES=$?

on_exit () {
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
