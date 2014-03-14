def test_create_service_dialog(automate_customization_pg, random_string):
    '''Create service dialog'''
    new_dialog_pg = automate_customization_pg\
        .click_on_service_dialog_accordion().add_new_service_dialog()
    service_dialog_name = "auto_dialog_" + random_string
    new_dialog_pg.create_service_dialog(random_string, service_dialog_name,
        "descr", "service_name")
    assert new_dialog_pg.flash.message.startswith(
        'Dialog "%s" was added' % service_dialog_name)


def test_edit_service_dialog(automate_customization_pg, random_string):
    '''Edit service dialog'''
    new_dialog_pg = automate_customization_pg\
        .click_on_service_dialog_accordion().add_new_service_dialog()
    service_dialog_name = "auto_dialog_" + random_string
    new_dialog_pg.create_service_dialog(random_string, service_dialog_name,
        "descr", "service_name")
    assert new_dialog_pg.flash.message.startswith(
        'Dialog "%s" was added' % service_dialog_name)
    edit_dialog_name = service_dialog_name + "_edited"
    new_dialog_pg.edit_service_dialog(edit_dialog_name)
    assert new_dialog_pg.flash.message.startswith(
        'Dialog "%s" was saved' % edit_dialog_name)


def test_delete_service_dialog(automate_customization_pg, random_string):
    '''Delete service dialog'''
    new_dialog_pg = automate_customization_pg\
        .click_on_service_dialog_accordion().add_new_service_dialog()
    service_dialog_name = "auto_dialog_" + random_string
    new_dialog_pg.create_service_dialog(random_string, service_dialog_name,
        "descr", "service_name")
    assert new_dialog_pg.flash.message.startswith(
        'Dialog "%s" was added' % service_dialog_name)
    new_dialog_pg.delete_service_dialog()
    assert new_dialog_pg.flash.message.startswith(
        'Dialog "%s": Delete successful' % service_dialog_name)


def test_duplicate_service_dialog(automate_customization_pg, random_string):
    '''Duplicate service dialog'''
    new_dialog_pg = automate_customization_pg\
        .click_on_service_dialog_accordion().add_new_service_dialog()
    service_dialog_name = "auto_dialog_" + random_string
    new_dialog_pg.create_service_dialog(random_string, service_dialog_name,
        "descr", "service_name")
    assert new_dialog_pg.flash.message.startswith(
        'Dialog "%s" was added' % service_dialog_name)
    dup_pg = new_dialog_pg.add_new_service_dialog()
    dup_pg.create_service_dialog(random_string, service_dialog_name,
        "descr", "service_name")
    assert dup_pg.flash.message.startswith(
        'Dialog Label has already been taken')
