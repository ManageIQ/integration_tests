#!ipxe

menu MTC iPXE Boot Menu

item --gap
item --gap --         -----MIQ Server Auto-Install:
item       fed16          Install Fedora 16
item       fed17          Install Fedora 17
item       fed18          Install Fedora 18
item rhel63server    RHEL 6.3 x86_64 Server
item fedora18        Fedora 18
item winpex64        WindowsPE_amd64

item --gap
item --gap --         -----Other Stuff:
item reboot             Reboot the Machine
item local              Boot Local

choose --default local --timeout 60000 os && goto ${os}
#choose --default reboot --timeout 60000 os && goto ${os}

########## MIQ Desktop Images ##########



########## MIQ Server Images ##########
:rhel63server
kernel http://${next-server}/ks/dist/ks-rhel-x86_64-server-6-6.3/images/pxeboot/vmlinuz ramdisk_size=10000 ks=http://${next-server}/pub/miq/ipxe/customization/rhel63.ks.cfg
initrd http://${next-server}/ks/dist/ks-rhel-x86_64-server-6-6.3/images/pxeboot//initrd.img
boot

:fedora18
kernel http://${next-server}/ks/dist/ks-fedora-x86_64-18/images/pxeboot/vmlinuz ramdisk_size=10000
initrd http://${next-server}/ks/dist/ks-fedora-x86_64-18/images/pxeboot/initrd.img
boot

:winpex64
kernel http://${next-server}/pub/miq/ipxe/sources/misc/memdisk iso raw
initrd http://${next-server}/pub/miq/ipxe/sources/microsoft/winpe_amd64.iso
boot


########## Other Stuff ##########

:reboot
reboot

:local
exit
