# -*- coding: utf-8 -*-
# pylint: disable=W0621
import pytest
import requests
import StringIO
from datetime import datetime


@pytest.fixture(scope="module",  # IGNORE:E1101
               params=["rhevm_pxe_setup"])
def provisioning_setup_data(request, cfme_data):
    param = request.param
    return cfme_data["provisioning_setup"][param]


@pytest.fixture
def host_provisioning_setup_data(cfme_data):
    return cfme_data["provisioning_setup"]['host_provisioning_setup']['pxe_server']


@pytest.fixture
def vm_provisioning_setup_data(cfme_data):
    return cfme_data["provisioning_setup"]['vm_provisioning_setup']['pxe_server']


def setup_pxe_server(db, provisioning_setup_data):
    row_val = None
    for row in db.session.query(db['pxe_image_types']):
        if row.name == provisioning_setup_data['pxe_image_type_name']:
            row_val = row.id

    server_name = []
    for row in db.session.query(db['pxe_servers']):
        server_name.append(row.name)
    if not provisioning_setup_data['pxe_server_name'] in server_name:

        '''Add a PXE Server'''
        new_pxe_server = db['pxe_servers'](
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
        db.session.add(new_pxe_server)
        db.session.commit()
        server_id = []
        for row in db.session.query(db['pxe_servers']):
            server_id.append(row.id)
        server_last_id = server_id.pop()
        return row_val, server_last_id
    return row_val, False


def setup_pxe_menu(db, provisioning_setup_data, server_last_id):
    ''' Add PXE Menu'''
    pxe_menu = db['pxe_menu']
    doc = requests.get(provisioning_setup_data['pxe_menu_file'], verify=False)
    content = StringIO.StringIO(doc.content).read()
    new_pxe_menu = pxe_menu(
        file_name=provisioning_setup_data['menu_file_name'],
        created_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%M%m"),
        pxe_server_id=server_last_id,
        type=provisioning_setup_data['menu_type'],
        updated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%M%m"),
        contents=content)
    db.session.add(new_pxe_menu)
    db.session.commit()
    menu_id = []
    for row in db.session.query(pxe_menu):
        menu_id.append(row.id)
    menu_last_id = menu_id.pop()
    return menu_last_id


def setup_pxe_image(db, provisioning_setup_data, server_last_id,
        menu_last_id, row_val):
    '''Add PXE Image'''
    new_pxe_image = db['pxe_images'](
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
    with db.transaction:
        db.session.add(new_pxe_image)


def setup_customization_template(db, provisioning_setup_data, row_val,
        ks_file_handle=None):
    row_val = None
    for row in db.session.query(db['pxe_image_types']):
        if row.name == provisioning_setup_data['pxe_image_type_name']:
            row_val = row.id

    customization_template = []
    for row in db.session.query(db['customization_templates']):
        customization_template.append(row.name)
    if not provisioning_setup_data['ct_name'] in customization_template:

        '''Add a Customization Template'''
        if ks_file_handle is None:
            f_ks = open(provisioning_setup_data['ks_file'], 'r+')
        else:
            f_ks = ks_file_handle
        new_customization_template = db['customization_templates'](
            created_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%M%m"),
            description=provisioning_setup_data['ct_description'],
            name=provisioning_setup_data['ct_name'],
            pxe_image_type_id=row_val,
            system=provisioning_setup_data['ct_system'],
            type=provisioning_setup_data['ct_type'],
            updated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%M%m"),
            script=f_ks.read())
        with db.transaction as session:
            session.add(new_customization_template)


@pytest.fixture
def setup_pxe_provision(uses_pxe, db, provisioning_setup_data):
    '''Sets up Infrastructure PXE for provisioning'''
    row_val, server_last_id = setup_pxe_server(db, provisioning_setup_data)
    if server_last_id is not False:
        menu_last_id = setup_pxe_menu(db, provisioning_setup_data, server_last_id)
        setup_pxe_image(db, provisioning_setup_data, server_last_id, menu_last_id, row_val)
    setup_customization_template(db, provisioning_setup_data, row_val)

    '''Edit System Image Type'''
    rhel_type = db.session.query(db['pxe_image_types']).get(row_val)
    with db.transaction:
        rhel_type.provision_type = 'vm'


@pytest.fixture
def setup_host_provisioning_pxe(uses_pxe, db, host_provisioning_setup_data,
        datafile):
    row_val, server_last_id = setup_pxe_server(db, host_provisioning_setup_data)
    if server_last_id is not False:
        ks_file_handle = datafile(host_provisioning_setup_data['ks_file'])
        menu_last_id = setup_pxe_menu(db, host_provisioning_setup_data, server_last_id)
        setup_pxe_image(db, host_provisioning_setup_data, server_last_id, menu_last_id,
                        row_val)
        setup_customization_template(db, host_provisioning_setup_data, row_val,
                                     ks_file_handle=ks_file_handle)

    # Edit System Image Type
    rhel_type = db.session.query(db['pxe_image_types']).get(row_val)
    with db.transaction:
        rhel_type.provision_type = 'host'


@pytest.fixture
def setup_vm_provisioning_pxe(uses_pxe, db, vm_provisioning_setup_data, datafile):
    row_val, server_last_id = setup_pxe_server(db, vm_provisioning_setup_data)
    if server_last_id is not False:
        doc = requests.get(vm_provisioning_setup_data['ks_file'], verify=False)
        ks_file_handle = StringIO.StringIO(doc.content)
        menu_last_id = setup_pxe_menu(db, vm_provisioning_setup_data, server_last_id)
        setup_pxe_image(db, vm_provisioning_setup_data, server_last_id, menu_last_id,
                        row_val)
        setup_customization_template(db, vm_provisioning_setup_data, row_val,
                                     ks_file_handle=ks_file_handle)

    # Edit System Image Type
    with db.transaction:
        rhel_type = db.session.query(db['pxe_image_types']).get(row_val)
        rhel_type.provision_type = 'vm'
