#!/usr/bin/env bash
# Script used when a new release comes only in the form of RPMs. Point it to a fresh appliance and
# it will turn it to a template with updated CFME. The name keeps the same so you should name
# the appliance as you want the template to be named.
#
# Usage: $SCRIPT_NAME provider_key appliance_name <params-for-update_rhel-script>

readonly D=`dirname $0`
readonly APPLIANCE_SCRIPT="${D}/appliance.py"
readonly UPDATE_SCRIPT="${D}/update_rhel.py"
readonly WAIT_UI_SCRIPT="${D}/wait_for_appliance_ui.py"

if [ $# -lt 2 ];
then
    echo "Usage: ${0} provider_key appliance_name <params for update>"
    exit 1
fi

readonly PROVIDER_KEY=$1
shift
readonly APPLIANCE_NAME=$1
shift
readonly UPDATE_PARAMS=$@

echo "Provider key: $PROVIDER_KEY"
echo "Appliance name: $APPLIANCE_NAME"
echo "Update params: $UPDATE_PARAMS"

APPLIANCE_IP=`$APPLIANCE_SCRIPT $PROVIDER_KEY $APPLIANCE_NAME address`
if [ $? -eq 0 ];
then
    readonly APPLIANCE_IP
else
    echo $APPLIANCE_IP
    echo "An error happened when getting appliance IP"
    exit 2
fi

echo "Appliance IP: $APPLIANCE_IP"
echo "Waiting for UI ..."
$WAIT_UI_SCRIPT "https://$APPLIANCE_IP/"
if [ $? -ne 0 ];
then
    echo "Failed to wait for web UI"
    exit 3
fi

echo "Running update ..."
$UPDATE_SCRIPT $UPDATE_PARAMS --reboot $APPLIANCE_IP
if [ $? -ne 0 ];
then
    echo "Failed to update"
    exit 4
fi

echo "Waiting for UI ..."
$WAIT_UI_SCRIPT "https://$APPLIANCE_IP/"
if [ $? -ne 0 ];
then
    echo "Failed to wait for web UI"
    exit 5
fi

echo "Resetting automate model"
$APPLIANCE_SCRIPT $PROVIDER_KEY $APPLIANCE_NAME reset_automate_model
if [ $? -ne 0 ];
then
    echo $APPLIANCE_IP
    echo "An error happened when resetting the automate model"
    exit 6
fi

echo "Templatizing ..."
$APPLIANCE_SCRIPT $PROVIDER_KEY $APPLIANCE_NAME templatize
if [ $? -ne 0 ];
then
    echo $APPLIANCE_IP
    echo "An error happened when templatizing."
    exit 7
fi

exit 0
