# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert

@pytest.fixture
def namespace(random_string):
    '''Returns random name for namespace'''
    return '%s_namespace' % random_string

@pytest.fixture
def subnamespace(random_string):
    '''Returns random name for subnamespace'''
    return '%s_subnamespace' % random_string

@pytest.fixture
def classm(random_string):
    '''Returns random name for class'''
    return '%s_class' % random_string

@pytest.fixture
def instance(random_string):
    '''Returns random name for instance'''
    return '%s_instance' % random_string

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")

def test_add_components(automate_explorer_pg, namespace, \
    subnamespace, classm, instance):
    ''' Adds each component that the explorer supports'''

    # Text to be added to CodeMirror editor
    method_text =  '''parm1 = $evm.object["parm1"]
    $evm.log("info","AStudent - Parm1: #{parm1}")
    parm2 = $evm.object["parm2"]
    $evm.log("info","AStudent - Parm2: #{parm2}")
    '''
    ae_pg = automate_explorer_pg

    # add namespace
    ae_pg.accordion.current_content.find_node_by_name("Datastore").click()
    ae_pg = ae_pg.click_on_add_new_namespace()
    ae_pg = ae_pg.fill_namespace_info(namespace, namespace)

    # add secondary namespace
    ae_pg.accordion.current_content.find_node_by_name(namespace).click()
    ae_namespace_pg = ae_pg.click_on_add_new_namespace()
    ae_namespace_pg.fill_namespace_info(subnamespace, subnamespace)

    # add class
    ae_pg.accordion.current_content.find_node_by_name(subnamespace).click()
    ae_class_pg = ae_pg.click_on_add_new_class()
    ae_class_pg = ae_class_pg.fill_class_info(classm, classm, classm)

    # edit schema
    ae_pg.accordion.current_content.find_node_by_name(\
        "%s (%s)" % (classm, classm)).click()
    tab_buttons = ae_class_pg.tabbutton_region
    tab_buttons.tabbutton_by_name("Schema").click()
    ae_schema_pg = ae_class_pg.click_on_edit_schema()
    ae_schema_pg.add_new_field("param1", "Attribute", "String")
    ae_schema_pg.add_new_field("param2", "Attribute", "String")
    ae_schema_pg.add_new_field("GetParams", "Method", "String")
    ae_schema_pg.add_new_field("rel", "Relationship", "String")
    ae_schema_pg.click_on_schema_save_button()

    # add method
    tab_buttons.tabbutton_by_name("Methods").click()
    ae_methods_pg = ae_class_pg.click_on_add_new_method()
    ae_methods_pg.fill_method_info(\
        "GetParams", "GetParams", "inline", method_text)
    ae_methods_pg.click_on_validate_method_button()
    Assert.equal(ae_methods_pg.flash_message_method.text, \
        "Data validated successfully")
    ae_methods_pg.click_on_add_system_button()

    # add instance
    tab_buttons.tabbutton_by_name("Instances").click()
    ae_instances_pg = ae_class_pg.click_on_add_new_instance()
    ae_instances_pg.fill_instance_info(instance, instance, instance)
    field_array = [ae_instances_pg.param_row_zero_value, \
        ae_instances_pg.param_row_one_value, \
        ae_instances_pg.param_row_two_value, \
        ae_instances_pg.param_row_three_value]
    value_array = ["FirstA", "LastA", "GetParams", \
        "%s/%s/%s/GetParams" % (namespace, subnamespace, classm)]
    ae_instances_pg.fill_instance_field_value_only(field_array, value_array)
    ae_instances_pg.click_on_add_system_button()

    # check all value appear in properties
    ae_properties_pg = tab_buttons.tabbutton_by_name("Properties").click()
    Assert.equal(ae_properties_pg.retrieve_properties_values(\
        "Fully Qualified Name"),
        "%s / %s / %s" % (namespace, subnamespace, classm))
    Assert.equal(ae_properties_pg.retrieve_properties_values("Name"), \
        classm)
    Assert.equal(ae_properties_pg.retrieve_properties_values("Instances"), \
         "1")

    # teardown - remove class
    ae_class_pg.click_on_remove_this_class()

    # teardown - remove parent namespace
    ae_namespace_pg = ae_pg.click_on_namespace_access_node("Datastore")
    ae_namespace_pg.click_on_namespace_item(namespace)
    ae_namespace_pg.click_on_remove_selected_namespaces()

