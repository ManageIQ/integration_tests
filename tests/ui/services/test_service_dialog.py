from unittestzero import Assert


class TestServiceDialog:
    '''Service Dialog test cases'''
    def test_create_service_dialog(self, automate_customization_pg, random_string):
        '''Create service dialog'''
        new_dialog_pg = automate_customization_pg\
            .click_on_service_dialog_accordion().add_new_service_dialog()
        service_dialog_name = "auto_dialog_" + random_string
        new_dialog_pg.create_service_dialog(random_string, service_dialog_name,
            "descr", "service_name")
        Assert.true(new_dialog_pg.flash.message.startswith(
            'Dialog "%s" was added' % service_dialog_name))
