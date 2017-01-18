# Dockerized ManageIQ Integration tests

## About


## How it works
- User will install docker on his machine
- afterthat  integration_tests repo must be cloned to his PC/laptop
- runs wrapper script which will pull needed docker containers
- script can than start container with preinstalled ansible and will mount volume containing playbooks
 - after this task si completed, wrapper script can be started again with py.test command and specified test
- this will start another container which will mount volume (integration_tests / yaml cloned repos) , start VNC server with selenium
- user then can connect to localhost VNC port and watch tests running
- after automated test is completed (successfully or failed), container is exited

### This solution consists of:
We have 3 Docker images (all Fedora 23 based):
 - integration_tests_base - this is base image with all packages which won't be changing often
- integration_tests_config - this is small image which contains Ansible. Before every initialization/re-configuration of integration_tests e.g. changing URL of appliance, this image is executed with specific playbook which will configure mounted directories from host system. This directory is then mounted by integraton_tests image.
- integration_tests - is the main image which will be used for executing py.test, ipython, vnc commands
Both images are linked to integration_tests_base image, so when any change to this image is detected, these 2 images will be rebuilt automatically by Dockerhub

- bash wrapper script which is responsible:
	- cloning integration_tests and repos
	- starting/stopping containers with different arguments, volumes
	- checking if there is newer version of Docker images in docker registry
	- can be used to run ipython
- Ansible playbooks + 1 custom action-plugin

Updating of Docker images works by pushing changes to integration_tests Dockerfiles. 


## Features
- wrapper script can be executed as many times as needed
- answers collected from user are stored, so when the script is executed next time, user can confirm values which won't change

## Prerequisities
 - bash, GNU sed, awk, curl
 - git => 2.10
 - vncviewer
 - Docker installed from official Docker repositories
Follow official documentation on how to [install](https://www.docker.com/products/overview#/install_the_platform) Docker on your favourite platform.

## Configure CFME 
Create working folder on your laptop:
```
export PROJECTS="${HOME}/projects"
export CFME_TESTS="${PROJECTS}/integration_tests_files"
mkdir -p ${CFME_TESTS}; cd ${CFME_TESTS}
```
### Copy custom YAML files (optional)
```
mkdir ./my_custom_yaml_files
cp -r /<path to custom yamls>/*.y*ml ./my_custom_yaml_files
```
When you will be asked for custom yamls, type relative path as used above e.g. ./my_custom__yaml_files

### Clone integration_tests repo
Clone integration_tests repo from GitHub:
```
<!---
git clone https://github.com/ManageIQ/integration_tests
Testing:
git clone https://github.com/ManageIQ/integration_tests
--->
git clone git://github.com/ManageIQ/integration_tests.git
cd integration_tests; git fetch origin pull/3254/head:integration_tests_container
git checkout integration_tests_container
cd ..; ln -s integration_tests/integration_tests_install/integration_tests_init.sh .

```

## Execution of wrapper script
Get information about how to use the wrapper script:
```
cd ${CFME_TESTS}
/bin/bash ./integration_tests_init.sh
```
Configure environment:
```
cd ${CFME_TESTS}
/bin/bash ./integration_tests_init.sh init
```
Note: Answers collected from user during init phase are stored inside .vars_config.yml.

Run test:
Note: This test requires to have YAML files configured.
```
cd ${CFME_TESTS}
/bin/bash ./integration_tests_init.sh cmd "py.test cfme/tests/test_login.py -k test_login -v"
```

## Building images manually
Clone integration_tests repo which contains Dockerfiles:
```
cd /var/tmp/
# git clone https://github.com/ManageIQ/integration_tests
# Testing:
git clone -b integration_tests_container  https://github.com/patchkez/cfme_tests
#cd integration_tests/integration_tests_install/dockerfiles
# testing:
cd cfme_tests/integration_tests_install/dockerfiles/
```

### Base image
Build image:
```
cd integration_tests_base;docker build -t redhatqe/integration_tests_base:`date "+%Y%m%d-%H%M"` .
```

Tag new built image as latest:
```
docker tag <image_id> redhatqe/integration_tests_base:latest
```

### Config image
Build image:
```
cd integration_tests_config; docker build -t redhatqe/integration_tests_config:`date "+%Y%m%d-%H%M"` .
```

> We can use image id, instead of name which we do not know after successfull build, because we use date format as a version
Tag new built image as latest:
```
docker tag <image_id> redhatqe/integration_tests_config:latest
```

### Tests image
Build image:
```
cd integration_tests; docker build -t redhatqe/integration_tests:`date "+%Y%m%d-%H%M"` .
```
Tag new built image as latest:
```
docker tag <image_id> redhatqe/integration_tests:latest
```


Double check if we have something like this (image tagged as latest must point to our new images):
```
% docker images | grep integration
redhatqe/integration_tests          20160624-1302       d650af89ca31        5 minutes ago       1.63 GB
redhatqe/integration_tests          latest              d650af89ca31        5 minutes ago       1.63 GB
redhatqe/integration_tests_config   20160624-1226       e530dbc0c3bc        41 minutes ago      1.699 GB
redhatqe/integration_tests_config   latest              e530dbc0c3bc        41 minutes ago      1.699 GB
redhatqe/integration_tests_base     latest              6e0e1aff46b9        About an hour ago   1.59 GB
redhatqe/integration_tests_base     20160624-1004       97cb61206b92        3 hours ago         1.106 GB
```

## Examine CFME images
```
docker run -it redhatqe/integration_tests:latest /bin/bash
```

## Running containers manually without wrapper script

Export paths:
```
export WORK_DIR="~/projects/integration_tests_files"
export INT_TESTS="${WORKDIR}/integration_tests/integrations_tests_install"
export PLAY_LOCATION="${INT_TESTS}/inetgration_tests_config"
```
### Examine if vols are mounted correctly
```
docker run -it \
-v ${PLAY_LOCATION:/projects/ansible_virtenv/ansible_work \
-v ${WORK_DIR}:/projects/cfme_env/cfme_vol/ \
redhatqe/integration_tests_config:latest /bin/bash
```

### Run config management
```
docker run -it \
-v ${PLAY_LOCATION}:/projects/ansible_virtenv/ansible_work \
-v ${WORKDIR}:/projects/cfme_env/cfme_vol/ \
redhatqe/integration_tests_config:latest
```

### Run config management
```
docker run -it \
-v ${PLAY_LOCATION}:/projects/ansible_virtenv/ansible_work \
-v ${WORKDIR}:/projects/cfme_env/cfme_vol/ \
-v ~/.ssh:/home/${USERNAME}/.ssh:ro \
-e "USER_ID=$(id -u)" -e "GROUP_ID=$(id -g)" -e "USERNAME=$(whoami)" -e "GROUPNAME=$(id -gn)" \
redhatqe/integration_tests_config:latest
```

### Run config management in verbose mode
```
docker run -it \
-v ${PLAY_LOCATION}:/projects/ansible_virtenv/ansible_work \
-v ${WORKDIR}:/projects/cfme_env/cfme_vol/ \
-v ~/.ssh:/home/${USERNAME}/.ssh:ro \
-e "USER_ID=$(id -u)" -e "GROUP_ID=$(id -g)" -e "USERNAME=$(whoami)" -e "GROUPNAME=$(id -gn)" \
redhatqe/integration_tests_config:latest \
/bin/bash -l -c "ansible-playbook -i inventory -c local configure_integration_tests.yml -vvvv"
```

### Run integration_tests container
```
docker run -it -p 5999:5999 \
-v ${WORKDIR}:/projects/cfme_env/cfme_vol/ \
-e DISPLAY=$DISPLAY \
redhatqe/integration_tests:latest \
/bin/bash -l -c "vncserver :99 -SecurityTypes None && tail -F /root/.vnc/*.log"
```
### Run ipython
```
docker run -it redhatqe/integration_tests:latest ipython
docker run -it -v ${WORKDIR}:/projects/cfme_env/cfme_vol/ redhatqe/integration_tests:latest ipython
```

### Execute test
```
docker run -it \
-v ${WORKDIR}:/projects/cfme_env/cfme_vol/ \
redhatqe/integration_tests:latest \
"py.test tests/configure/test_access_control.py -k superadmin_tenant -v"
```

```
docker run -it \
-v ${WORKDIR}:/projects/cfme_env/cfme_vol/ \
redhatqe/integration_tests:latest \
/bin/bash -l -c "py.test cfme_vol/cfme_tests/cfme/tests/configure/test_access_control.py -k superadmin_tenant -v"
```

```
docker run -it \
-v ${WORKDIR}:/projects/cfme_env/cfme_vol/ \
redhatqe/integration_tests:latest \
/bin/bash -l -c \
"cd cfme_vol/cfme_tests/cfme; py.test tests/configure/test_access_control.py -k superadmin_tenant -v"
```

#### Docker maintenance
Remove all not running containers which were started from redhatqe/integration_tests image
```
docker rm $(docker ps -q -f ancestor=redhatqe/integration_tests -f status=created)
```

#### Notes/Todo
- tested on Docker 1.13.0 rc7
- configuration tested with CFME QE setup
- if yaml files are not provided by user - rename template: conf/cfme_data.yaml.template
- run smoke test after container configuration - tests/test_appliance.py
- provide example how to run smoke tests:
- yamls must contain examples of all upstream providers
- replace occurences of cfme
