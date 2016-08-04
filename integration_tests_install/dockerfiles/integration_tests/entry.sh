#!/bin/bash
groupadd -g ${GROUP_ID} ${GROUPNAME} 2> /dev/null
adduser -u ${USER_ID} -g ${GROUPNAME} ${USERNAME} 2> /dev/null
#adduser ${USERNAME} sudo
#useradd -G wheel ${USERNAME} 2> /dev/null
#echo '%wheel ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
exec su -m ${USERNAME} -c "$@"
