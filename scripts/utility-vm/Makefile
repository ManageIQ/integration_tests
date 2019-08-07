SOURCE_IMAGE=rhel-guest-image.qcow2
TMP_DISK=disk.qcow2.tmp

utility_vm.qcow2: snapshot.qcow2
	qemu-img convert -O qcow2 -p $< $@

snapshot.qcow2: ${SOURCE_IMAGE} customization-script.sh rhel7.repo rhel8.repo
	-rm ${TMP_DISK}
	qemu-img create -f qcow2 -o backing_file=`pwd`/$< ${TMP_DISK}
	virt-customize --network \
		           -a ${TMP_DISK} \
				   --upload rhel7.repo:/tmp/rhel7.repo \
				   --upload rhel8.repo:/tmp/rhel8.repo \
				   --upload customization-script.sh:/tmp/customization-script.sh \
				   --run-command "/bin/bash /tmp/customization-script.sh '${SHARE_PASSWORD}'" \
				   --selinux-relabel
	mv ${TMP_DISK} $@

%.repo: %.repo.template
ifndef RHEL_REPO_BASE
	$(error The env variable RHEL_REPO_BASE is undefined)
endif
	sed 's|RHEL_REPO_BASE|${RHEL_REPO_BASE}|g' $< >$@

${SOURCE_IMAGE}:
ifndef DOWNLOAD_LINK
	$(error The env variable DOWNLOAD_LINK is undefined)
endif
	curl -Sf "${DOWNLOAD_LINK}" -o $@

cloud_init.iso: user-data.yaml meta-data
	genisoimage -output "$@" -volid cidata -joliet -rock $^

user-data: user-data.yaml
	write-mime-multipart $< > $@

clean:
	-rm user-data cloud_init.iso rhel8.repo rhel7.repo utility_vm.qcow2 \
		${TMP_DISK} snapshot.qcow2

.PHONY: clean
