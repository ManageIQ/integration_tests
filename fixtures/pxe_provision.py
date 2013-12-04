# -*- coding: utf-8 -*-
# pylint: disable=W0621
import pytest
import db
import os
from datetime import datetime


@pytest.fixture(scope="module",  # IGNORE:E1101
               params=["rhevm_pxe_setup"])
def provisioning_setup_data(request, cfme_data):
    param = request.param
    return cfme_data.data["provisioning_setup"][param]


@pytest.fixture
def setup_pxe_provision(db_session, provisioning_setup_data):
    '''Sets up Infrastructure PXE for provisioning'''
    session = db_session

    row_val = None
    for row in session.query(db.PxeImageType):
        if row.name == provisioning_setup_data['pxe_image_type_name']:
            row_val = row.id

    server_name = []
    for row in session.query(db.PxeServer):
        server_name.append(row.name)
    if not provisioning_setup_data['pxe_server_name'] in server_name:

        '''Add a PXE Server'''
        new_pxe_server = db.PxeServer(
            access_url=provisioning_setup_data['access_url'],
            pxe_directory=provisioning_setup_data['pxe_directory'],
            customization_directory=provisioning_setup_data['customization_directory'],
            windows_images_directory=provisioning_setup_data['windows_image_directory'],
            name=provisioning_setup_data['pxe_server_name'],
            uri="%s%s" % ('nfs://', provisioning_setup_data['uri']),
            uri_prefix=provisioning_setup_data['uri_prefix'],
            visibility=provisioning_setup_data['visibility'],
            created_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%M%m"),
            updated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%M%m"))
        session.add(new_pxe_server)
        session.commit()
        server_id = []
        for row in session.query(db.PxeServer):
            server_id.append(row.id)
        server_last_id = server_id.pop()

        ''' Add PXE Menu'''
        os.system("%s %s" % ("wget", provisioning_setup_data['pxe_menu_file']))
        f = open(provisioning_setup_data['menu_file_name'], 'r+')
        new_pxe_menu = db.PxeMenu(
            file_name=provisioning_setup_data['menu_file_name'],
            created_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%M%m"),
            pxe_server_id=server_last_id,
            type=provisioning_setup_data['menu_type'],
            updated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%M%m"),
            contents=f.read())
        session.add(new_pxe_menu)
        session.commit()
        menu_id = []
        for row in session.query(db.PxeMenu):
            menu_id.append(row.id)
        menu_last_id = menu_id.pop()

        '''Add PXE Image'''
        new_pxe_image = db.PxeImage(
            default_for_windows=None,
            description=provisioning_setup_data['image_description'],
            initrd=provisioning_setup_data['initrd'],
            kernel=provisioning_setup_data['kernel'],
            kernel_options=provisioning_setup_data['kernel_options'],
            name=provisioning_setup_data['image_name'],
            path=provisioning_setup_data['image_path'],
            pxe_image_type_id=row_val,
            pxe_menu_id=menu_last_id,
            pxe_server_id=server_last_id,
            type=provisioning_setup_data['image_type'],
            created_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%M%m"),
            updated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%M%m"))
        session.add(new_pxe_image)
        session.commit()

        '''Cleanup'''
        os.system("%s %s" % ("rm -rf", provisioning_setup_data['pxe_menu_file']))

    customization_template = []
    for row in session.query(db.CustomizationTemplate):
        customization_template.append(row.name)
    if not provisioning_setup_data['ct_name'] in customization_template:

        '''Add a Customization Template'''
        f_ks = open(provisioning_setup_data['ks_file'], 'r+')
        new_customization_template = db.CustomizationTemplate(
            created_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%M%m"),
            description=provisioning_setup_data['ct_description'],
            name=provisioning_setup_data['ct_name'],
            pxe_image_type_id=row_val,
            system=provisioning_setup_data['ct_system'],
            type=provisioning_setup_data['ct_type'],
            updated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%M%m"),
            script=f_ks.read())
        session.add(new_customization_template)
        session.commit()

    '''Edit System Image Type'''
    rhel_type = session.query(db.PxeImageType).get(row_val)
    rhel_type.provision_type = 'vm'
    session.commit()
