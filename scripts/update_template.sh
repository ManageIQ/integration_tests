#!/usr/bin/env bash
# Script used when a new release comes only in the form of RPMs. Point it to an existing template and
# it will turn it to a template with updated CFME. 
#
# Usage: $SCRIPT_NAME provider_key template_name new_template_name <params-for-update_rhel-script>

D=`dirname $0`
APPLIANCE_SCRIPT="${D}/appliance.py"
IPAPPLIANCE_SCRIPT="${D}/ipappliance.py"
CLONE_TEMPLATE_SCRIPT="${D}/clone_template.py"
UPDATE_SCRIPT="${D}/update_rhel.py"
WAIT_UI_SCRIPT="${D}/wait_for_appliance_ui.py"


if [ $# -lt 2 ];
then
    echo "Usage: ${0} provider_key template_name new_template_name <params for update>"
    exit 1
fi

PROVIDER_KEY=$1
shift
TEMPLATE_NAME=$1
shift
APPLIANCE_NAME=$1  # Also the new template name, but the name stays on ...
shift
UPDATE_PARAMS=$@

echo "Provider key: $PROVIDER_KEY"
echo "Template name: $TEMPLATE_NAME"
echo "Update params: $UPDATE_PARAMS"

echo "Deploying the template $TEMPLATE_NAME in $PROVIDER_KEY as $APPLIANCE_NAME"

APPLIANCE_IP=`$CLONE_TEMPLATE_SCRIPT --provider $PROVIDER_KEY --template $TEMPLATE_NAME --vm_name $APPLIANCE_NAME`
if [ $? -ne 0 ];
then
    echo "An error happened when deploying $TEMPLATE_NAME in $PROVIDER_KEY"
    exit 2
fi

echo "Appliance IP: $APPLIANCE_IP, waiting for SSH"
$IPAPPLIANCE_SCRIPT wait_for_ssh $APPLIANCE_IP
if [ $? -ne 0 ];
then
    echo "Failed to wait for SSH"
    exit 3
fi

echo "Running update ..."
$UPDATE_SCRIPT $UPDATE_PARAMS --reboot $APPLIANCE_IP
if [ $? -ne 0 ];
then
    echo "Failed to update"
    exit 4
fi

echo "Waiting for SSH again"
$IPAPPLIANCE_SCRIPT wait_for_ssh $APPLIANCE_IP
if [ $? -ne 0 ];
then
    echo "Failed to wait for SSH"
    exit 5
fi

echo "Templatizing ..."
$APPLIANCE_SCRIPT $PROVIDER_KEY $APPLIANCE_NAME templatize
if [ $? -ne 0 ];
then
    echo $APPLIANCE_IP
    echo "An error happened when templatizing."
    exit 6
fi
