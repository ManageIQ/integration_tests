#!/bin/bash

VNC_PORT_DEFAULT="5999"
VNC_SERVER_CMD="vncserver :99 -xstartup /usr/local/bin/xstartup -SecurityTypes None"

#GIT_URL="https://github.com/patchkez/cfme_tests"
GIT_URL="https://github.com/ManageIQ/integration_tests/"
GIT_BRANCH="master"
#GIT_BRANCH="integration_tests_container"


#WORKDIR="~/projects/integration_tests_files"
WORKDIR="${PWD}"
REPO_LOCATION="${WORKDIR}/integration_tests"
PLAY_LOCATION="${WORKDIR}/integration_tests/integration_tests_install/integration_tests_config"
#PLAY_LOCATION="${WORKDIR}/cfme_tests/integration_tests_install/integration_tests_config"

#DOCK_IMG_CFG="redhatqe/integration_tests_config:latest"
#IMG="redhatqe/integration_tests:latest"
DOCK_IMG_CFG="patchkez/cfme_tests_config_test:latest"
IMG="patchkez/cfme_tests_test"
#DOCK_IMG="${IMG}:latest"

USER_ID=`id -u`
GROUP_ID=`id -g`
USERNAME=`whoami`
GROUPNAME=`id -gn`
HOME="/home/${USERNAME}"

# these variables are passed into container and are read by playbook which will create same user/group inside container 
if [[ -n "${INT_TESTS_DEBUG}" && ${INT_TESTS_DEBUG} -eq 1 ]]; then
  ENV_VARS="-e USER_ID=`id -u` -e GROUP_ID=`id -g` -e USERNAME=`whoami` -e GROUPNAME=`id -gn` -e HOME=/home/`whoami` -e DEBUG=true"
  ENV_VARS_CONF="-e USER_ID=`id -u` -e GROUP_ID=`id -g` -e USERNAME=`whoami` -e GROUPNAME=`id -gn` -e DEBUG=true"
else
  ENV_VARS="-e USER_ID=`id -u` -e GROUP_ID=`id -g` -e USERNAME=`whoami` -e GROUPNAME=`id -gn` -e HOME=/home/`whoami` -e DEBUG=false"
  ENV_VARS_CONF="-e USER_ID=`id -u` -e GROUP_ID=`id -g` -e USERNAME=`whoami` -e GROUPNAME=`id -gn` -e DEBUG=false"
fi

HELPER_FILE="./.helper_file"
DO_NOT_CHECK="/var/tmp/.dnc"
STAT="/var/tmp/.docker_registry_check"


function log {
  echo "==============="
  echo -e $1
  echo "==============="
}
function get_version {

cd ${REPO_LOCATION}
#pwd
GIT_STAT=`git status | head -1`

if ( echo ${GIT_STAT} | grep -q "On branch" ); then
  PICK_IMAGE_TAG="latest"
elif ( echo ${GIT_STAT} | grep -q "HEAD detached at" ); then
  PICK_IMAGE_TAG="v$(echo ${GIT_STAT} | sed 's/^HEAD detached at \(.*\)$/\1/g')"
else
  log "unknown"
  PICK_IMAGE_TAG="latest"
fi

echo DOCK_IMG="${IMG}:${PICK_IMAGE_TAG}"
DOCK_IMG="${IMG}:${PICK_IMAGE_TAG}"
}

function check_4_new_img {
  get_version
  AUTH_TOK=`curl --silent "https://auth.docker.io/token?service=registry.docker.io&scope=repository:${IMG}:pull" | awk -F '\"' '{print $4}'`
  # REGISTRY_URL="https://registry.hub.docker.com/v2/${IMG}/manifests/latest"
  REGISTRY_URL="https://registry.hub.docker.com/v2/${IMG}/manifests/${PICK_IMAGE_TAG}"
  AUTH_HEAD="Authorization: Bearer $AUTH_TOK"
  # log "AUTH head is: ${AUTH_HEAD}"
  ACCEPT_HEAD="Accept: application/vnd.docker.distribution.manifest.v2+json"
  GET_REMOTE_DIGEST=`curl -L --silent -k -X GET "${REGISTRY_URL}" -H "${AUTH_HEAD}" -H "${ACCEPT_HEAD}" | awk '/config/,/}/{if ($1 ~ /digest/) {gsub("\"","");print $2}}'`
  GET_LOCAL_DIGEST=`docker inspect ${DOCK_IMG} | sed -n 's/^.*"Id": "\(.[^"]*\).*/\1/gp'`
  log "REMOTE digest is: ${GET_REMOTE_DIGEST}"
  log "LOCAL digest is: ${GET_LOCAL_DIGEST}"

  if [ -z ${GET_REMOTE_DIGEST} ];then
    log "No remote digest found for image!!! Exiting.."
    exit 1
  fi

  # Perform check only if file does not exists, if it exists it means user have been notified about new image,
  # and on next init, new image will be pulled.
  if [ ! -f ${DO_NOT_CHECK} ]; then
    if [ ! -f ${STAT} ];then
      touch ${STAT}
    fi
    # We are performing check against docker registry only If STAT file is older than X seconds
    TIMEOUT=3600
    AGE_STAT=`stat --format=%Y ${STAT}`
    STAT_COMPARE=$(( `date +%s` - ${TIMEOUT} ))
    DIFFERENCE=`expr ${AGE_STAT} - ${STAT_COMPARE}`
    
    log "STAT age is: ${AGE_STAT}"
    log "STAT compare is: ${STAT_COMPARE}"
    log "Difference is ${DIFFERENCE}"
   
    if [ ${AGE_STAT} -le $(( ${STAT_COMPARE} )) ]; then
      # Compare Local and Remote Image IDs, if there is difference -> there is newer image in Docker registry
      if [ "${GET_LOCAL_DIGEST}" != "${GET_REMOTE_DIGEST}" ]; then
        # log "New version of image is available!! Please run this wrapper script with init argument"
        # touch ${DO_NOT_CHECK}
        log "New version of image is available!! Downloading new image..."
        docker pull ${DOCK_IMG} 
      fi
    else
      log "Last check done less than 60 minutes ago..."
    fi
  else
    log "We won't check for new image, user have been informed already!!!"
  fi
}

function check_vnc_port {
  # This function will return 0 if port is opened or any other integer if it is free
  timeout 1 bash -c "cat < /dev/null > /dev/tcp/localhost/${1}" &> /dev/null; echo $?
}

function return_vnc_port {
  # this function will return next free VNC port. This is usefull when we want to start multiple tests in parallel - each test has it's own vncserver running on unique port.
  EXIT=`check_vnc_port ${VNC_PORT_DEFAULT}`
  while [ ${EXIT} -eq 0 ];
  # This while loop will find next opened port on which VNC can be started
  # If port is used, increment and check for opened port again 
  do 
    let "VNC_PORT_DEFAULT++"
    log "VNC port ${VNC_PORT_DEFAULT} occupied, trying next one..."
    EXIT=`check_vnc_port ${VNC_PORT_DEFAULT}`
  done
  VNC_PORT=${VNC_PORT_DEFAULT}
}

function do_ssh {
# Get value from config file 
if [ ! -f ${WORKDIR}/.vars_config.yml ];then
  SSH_VOL=""
else
  if [ "$(sed -n 's/^mount_ssh_keys: \(.*\).*$/\1/gp' ${WORKDIR}/.vars_config.yml)" = "y" ]; then
    SSH_VOL="-v ${HOME}/.ssh:/home/${USERNAME}/.ssh:ro"
  else
    SSH_VOL=""
  fi
fi
}


function run_config {
  # Check if new image is available on Docker registry
  check_4_new_img
  
  do_ssh

  # If this file exists, it means user was notified about new image and image must be pulled when executing script with init argument.
  if [ -f ${DO_NOT_CHECK} ]; then
    rm ${DO_NOT_CHECK}
    log "New image have been detected and therefore pulling its latest version... This may take some time."
    docker pull ${DOCK_IMG}
  fi

  docker run -it --rm \
    -v $(dirname $SSH_AUTH_SOCK):$(dirname $SSH_AUTH_SOCK):rw \
    -v ${PLAY_LOCATION}:/projects/ansible_virtenv/ansible_work \
    -v ${WORKDIR}:/projects/cfme_vol/ \
    ${SSH_VOL} -v /var/tmp/bashrc:${HOME}/.bashrc \
    --security-opt=label=type:spc_t \
    -e SSH_AUTH_SOCK=$SSH_AUTH_SOCK \
    -e PROJECTS=$PROJECTS \
    ${ENV_VARS_CONF} \
    ${DOCK_IMG_CFG} \
    ${1}
}


function run_command {
  # Check if new image is available on Docker registry
  check_4_new_img

  return_vnc_port
  do_ssh

  log "VNC port is $VNC_PORT" 
  # We create temporary file on the host system which is mounted into container later on
  echo "source /etc/bashrc" > /var/tmp/bashrc

  # Check if we need to mount .ssh directory
  if [ ! -f ${WORKDIR}/.vars_config.yml ];then
    echo ".vars_config.yml not found!!! Run ./integration_tests_init.sh init..."
    exit 1
  fi
  

  docker run -it --rm \
    -w /projects/cfme_vol/integration_tests \
    -u ${USER_ID}:${GROUP_ID} \
    -p ${VNC_PORT}:5999 \
    -v $(dirname $SSH_AUTH_SOCK):$(dirname $SSH_AUTH_SOCK):rw \
    -v /etc/passwd:/etc/passwd:ro \
    -v /etc/group:/etc/group:ro \
    -v ${WORKDIR}:/projects/cfme_vol/ \
    -v /var/tmp/:${HOME}/ \
    ${SSH_VOL} -v /var/tmp/bashrc:${HOME}/.bashrc \
    --security-opt=label=type:spc_t \
    -e SSH_AUTH_SOCK=$SSH_AUTH_SOCK \
    ${ENV_VARS} \
    ${DOCK_IMG} \
    bash -c ". /etc/bashrc; pip install -e .; $1"
}
    #-v ${PROJECTS_DIR}:${HOME}/${PROJECTS_DIR} \


    # bash -c ". /etc/bashrc; deactivate; source ../cfme_venv/bin/activate; cp ../../bin/chromedriver ../cfme_venv/bin; $1"
    # -v /home/patchkez/projects/integration_tests_files/wrapanapi/wrapanapi/:/projects/cfme_vol/cfme_venv/lib/python2.7/site-packages/wrapanapi/ \

case $1 in
test*)
  log "Testing..."
  get_version 
  ;;
init*)
  log "Starting init"
  run_config $2
  ;;
update*)
  log "Starting updating integration_tests"
  run_config $2
  ;;
ipython)
  log "Starting ipython..."
  run_command "${VNC_SERVER_CMD}; ipython"
  ;;
cmd)
  log "Run cmd"
  run_command "${VNC_SERVER_CMD}; ${@:2}"
  ;;
set_url)
  log "Setup base url"
  run_config "-t set_url"
  ;;
set_browser)
  log "Setup base url"
  run_config "-t set_browser"
  ;;
*)
  log "No argument was provided!\n\n
      Available arguments are:\n
        init - configure CFME tests environment\n
        update - pull latest changes for GIT repositories\n
        ipython - start ipython once environment is configured\n
        cmd - start any command inside CFME docker container \n
        set_url (does not work yet, tags must be implemented inside playbook)\n
        set_browser (does not work yet, tags must be implemented inside playbook)\n"
  ;;
esac
