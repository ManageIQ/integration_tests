#!/usr/bin/env bash

#necessary external env variables: NFSHOST, NFSPATH

NFS_HOST=${NFSHOST}  #ex: '10.8.218.9'
NFS_PATH=${NFSPATH}  #ex: "/exports/volumes/"
ALIVEPVNUM=100

oc login --username='system:admin'

# removing old unused persistent volumes
echo "looking for old unused persistent volumes"
for status in Failed Released
do
	for pv in `oc get pv |grep ${status}|cut -f1 -d' '`
	do
		PV_PATH=$(oc get --output=json pv/${pv}|\
		          python -c "import sys, json; print json.load(sys.stdin)['spec']['nfs']['path']")
		VOL_TO_DELETE=$(dirname ${PV_PATH})

        echo "removing unused pv ${pv}"
		oc delete pv ${pv}

		echo ${VOL_TO_DELETE}|grep -q "${NFS_PATH}"
		if [[ $? -eq 0 || "${VOL_TO_DELETE}" > "${NFS_PATH}" ]]
		then
		    echo "removing volume ${VOL_TO_DELETE}"
		    rm -rf ${VOL_TO_DELETE}
		else
		    echo "wrong path ${VOL_TO_DELETE} is passed to rm -rf. So, ignoring removal statement"
		fi
	done
done

# counting left pvs and adding new pvs
echo "checking how many available or used persistent volumes are left"
((PVNUM=$(oc get pv |grep "Available\|Bound"|wc -l)/2))
if [[ ${PVNUM} -lt ${ALIVEPVNUM} ]]
then
    echo "${PVNUM} volumes are present whereas ${ALIVEPVNUM} should exist. Creating new pvs"
    umask 0000
    for CUR_PV_NUM in `seq ${PVNUM} ${ALIVEPVNUM}`
    do
        DB_VOL_ID=$(pwgen -A 6 1)
        DB_VOLUME_NAME="volume-${DB_VOL_ID}"  # folder name
        DB_BASE_PATH="${NFS_PATH}/${DB_VOLUME_NAME}"
        DB_PV_NAME="cfme-db-pv-${DB_VOL_ID}"
        mkdir -p "${DB_BASE_PATH}/cfme-db"

        APP_VOL_ID=$(pwgen -A 6 1)
        APP_VOLUME_NAME="volume-${APP_VOL_ID}"  # folder name
        APP_BASE_PATH="${NFS_PATH}/${APP_VOLUME_NAME}"
        APP_PV_NAME="cfme-app-pv-${APP_VOL_ID}"
        mkdir -p "${APP_BASE_PATH}/cfme-app"

        echo "persistent volumes ${APP_PV_NAME}, ${DB_PV_NAME} are being created"
        oc process cloudforms-app-pv --namespace=openshift -p BASE_PATH=${APP_BASE_PATH} \
                                                           -p NFS_HOST=${NFS_HOST} \
                                                           -p VOL_NAME=${APP_PV_NAME}\
                                                           | oc create -f -
        oc process cloudforms-db-pv --namespace=openshift -p BASE_PATH=${DB_BASE_PATH} \
                                                          -p NFS_HOST=${NFS_HOST} \
                                                          -p VOL_NAME=${DB_PV_NAME}\
                                                           | oc create -f -
    done
fi
