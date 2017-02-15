import fauxfactory
import os
import subprocess
import yaml
from shutil import copyfile
from utils import conf
from utils.providers import get_crud

yml_path = os.path.dirname(__file__) + "/manageiq_ansible_module/"
library_path = yml_path + "library/"
basic_yml_path = os.path.dirname(__file__) + "/ansible_conf/"
library_path_to_copy_to = basic_yml_path + "library"
providers_basic_script = "providers_basic_script.yml"
users_basic_script = "users_basic_script.yml"
provider_name = 'CI OSE'
random_token = fauxfactory.gen_alphanumeric(906),
random_miq_user = fauxfactory.gen_alphanumeric(8)


def get_values_from_conf(provider, script_type):
    # TODO Clean where possible
    if script_type == 'providers':
        return {
            'name': provider_name,
            'state': 'present',
            'miq_url': config_formatter(),
            'miq_username': conf.credentials['default'].username,
            'miq_password': conf.credentials['default'].password,
            'provider_api_hostname': conf.cfme_data.get('management_systems', {})
            [provider.key].get('hostname', []),
            'provider_api_auth_token': get_crud('ci-ose').credentials['token'].token,
            'hawkular_hostname': conf.cfme_data.get('management_systems', {})
            [provider.key].get('hostname', [])
        }
    elif script_type == 'users':
        return {
            'fullname': 'MIQUser',
            'name': 'MIQU',
            'password': 'smartvm',
            'state': 'present',
            'miq_url': config_formatter(),
            'miq_username': conf.credentials['default'].username,
            'miq_password': conf.credentials['default'].password,
        }
    elif script_type == 'custom_attributes':
        return {
            'entity_type': 'provider',
            'entity_name': provider_name,
            'miq_url': config_formatter(),
            'miq_username': conf.credentials['default'].username,
            'miq_password': conf.credentials['default'].password,
        }


# TODO Avoid reading files every time


def read_yml(script, value):
    with open(yml_path + script + ".yml", 'r') as f:
            doc = yaml.load(f)
    return doc[0]['tasks'][0]['manageiq_provider'][value]


def get_yml_value(script, value):
    with open(basic_yml_path + script + ".yml", 'r') as f:
            doc = yaml.load(f)
    return doc[0]['tasks'][0]['manageiq_provider'][value]


def setup_basic_script(provider, script_type):
    with open(basic_yml_path + script_type + "_basic_script.yml", 'rw') as f:
        doc = yaml.load(f)
        values_dict = get_values_from_conf(provider, script_type)
    for key in values_dict:
        if script_type == 'providers':
            doc[0]['tasks'][0]['manageiq_provider'][key] = values_dict[key]
        elif script_type == 'users':
            doc[0]['tasks'][0]['manageiq_user'][key] = values_dict[key]
        elif script_type == 'custom_attributes':
            doc[0]['tasks'][0]['manageiq_custom_attributes'][key] = values_dict[key]
        with open(basic_yml_path + script_type + "_basic_script.yml", 'w') as f:
            f.write(yaml.dump(doc))


def open_yml(script, script_type):
    copyfile(basic_yml_path + "/" + script_type + "_basic_script.yml",
             basic_yml_path + script + ".yml")
    with open(basic_yml_path + script + ".yml", 'rw') as f:
        return yaml.load(f)


def write_yml(script, doc):
    with open(basic_yml_path + script + ".yml", 'w') as f:
        f.write(yaml.dump(doc))


def setup_ansible_script(provider, script, script_type=0, values_to_update=0, user_name=0):
    # This function prepares the ansible scripts to work with the correct
    # appliance configs that will be received from Jenkins
    setup_basic_script(provider, script_type)
    if script == 'add_provider':
        copyfile(basic_yml_path + providers_basic_script, basic_yml_path + script + ".yml")

    elif script == 'update_provider':
        doc = open_yml(script, 'providers')
        for key in values_to_update:
            doc[0]['tasks'][0]['manageiq_provider'][key] = values_to_update[key]
            write_yml(script, doc)

    elif script == 'remove_provider':
        doc = open_yml(script, 'providers')
        doc[0]['tasks'][0]['manageiq_provider']['state'] = 'absent'
        write_yml(script, doc)

    elif script == 'remove_non_existing_provider':
        doc = open_yml(script, 'providers')
        doc[0]['tasks'][0]['manageiq_provider']['state'] = 'absent'
        doc[0]['tasks'][0]['manageiq_provider']['name'] = random_miq_user
        write_yml(script, doc)

    elif script == 'remove_provider_bad_user':
        doc = open_yml(script, 'providers')
        doc[0]['tasks'][0]['manageiq_provider']['miq_username'] = random_miq_user
        write_yml(script, doc)

    elif script == 'add_provider_bad_token':
        doc = open_yml(script, 'providers')
        doc[0]['tasks'][0]['manageiq_provider']['provider_api_auth_token'] = random_token
        write_yml(script, doc)

    elif script == 'add_provider_bad_user':
        doc = open_yml(script, 'providers')
        doc[0]['tasks'][0]['manageiq_provider']['miq_username'] = random_miq_user
        write_yml(script, doc)

    elif script == 'update_non_existing_provider':
        doc = open_yml(script, 'providers')
        doc[0]['tasks'][0]['manageiq_provider']['provider_api_hostname'] = random_miq_user
        write_yml(script, doc)

    elif script == 'update_provider_bad_user':
        doc = open_yml(script, 'providers')
        for key in values_to_update:
            doc[0]['tasks'][0]['manageiq_provider'][key] = values_to_update[key]
        doc[0]['tasks'][0]['manageiq_provider']['miq_username'] = random_miq_user
        write_yml(script, doc)

    elif script == 'create_user':
        doc = open_yml(script, "users")
        for key in values_to_update:
            doc[0]['tasks'][0]['manageiq_user'][key] = values_to_update[key]
            write_yml(script, doc)

    elif script == 'update_user':
        doc = open_yml(script, "users")
        for key in values_to_update:
            doc[0]['tasks'][0]['manageiq_user'][key] = values_to_update[key]
            write_yml(script, doc)

    elif script == 'create_user_bad_user_name':
        doc = open_yml(script, "users")
        doc[0]['tasks'][0]['manageiq_user']['miq_username'] = random_miq_user
        for key in values_to_update:
            doc[0]['tasks'][0]['manageiq_user'][key] = values_to_update[key]
        write_yml(script, doc)

    elif script == 'delete_user':
        doc = open_yml(script, "users")
        doc[0]['tasks'][0]['manageiq_user']['name'] = values_to_update
        doc[0]['tasks'][0]['manageiq_user']['state'] = 'absent'
        write_yml(script, doc)

    elif script == 'add_custom_attributes':
        doc = open_yml(script, "custom_attributes")
        count = 0
        while count < len(values_to_update):
            for key in values_to_update:
                doc[0]['tasks'][0]['manageiq_custom_attributes']['custom_attributes'][count] = key
                count += 1
                write_yml(script, doc)

    elif script == 'add_custom_attributes_bad_user':
        doc = open_yml(script, 'custom_attributes')
        doc[0]['tasks'][0]['manageiq_custom_attributes']['miq_username'] = str(random_miq_user)
        write_yml(script, doc)

    elif script == 'remove_custom_attributes':
        doc = open_yml(script, "custom_attributes")
        count = 0
        doc[0]['tasks'][0]['manageiq_custom_attributes']['state'] = 'absent'
        while count < len(values_to_update):
            for key in values_to_update:
                doc[0]['tasks'][0]['manageiq_custom_attributes']['custom_attributes'][count] = key
                count += 1
        write_yml(script, doc)
    # copy_manageiq_ansible()


def run_ansible(script):
    cmd = "ansible-playbook " + basic_yml_path + script + ".yml"
    try:
        response = subprocess.check_output(cmd,
                                           shell=True,
                                           stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as exc:
        print("Status : FAIL", exc.returncode, exc.output)
        return exc.output
    else:
        print("Output: \n{}\n".format(response))


def reply_status(reply):
    ok_status = reply['stats']['localhost']['ok']
    changed_status = reply['stats']['localhost']['changed']
    failures_status = reply['stats']['localhost']['failures']
    skipped_status = reply['stats']['localhost']['skipped']
    message_status = reply['plays'][0]['tasks'][2]['hosts']['localhost']['result']['msg']
    if not ok_status == '0':
        ok_status = 'OK'
    else:
        ok_status = 'Failed'
    if changed_status:
        return 'Changed', message_status, ok_status
    elif skipped_status:
        return 'Skipped', message_status, ok_status
    elif failures_status:
        return 'Failed', message_status, ok_status
    else:
        return 'No Change', message_status, ok_status

#
# def copy_manageiq_ansible():
#     print("this is the library to copy to: " + library_path_to_copy_to)
#     print("this is the library to copy from: " + library_path)
#     if not os.path.exists(library_path_to_copy_to):
#         os.makedirs(library_path_to_copy_to)
#         copy_tree(library_path, library_path_to_copy_to)


def config_formatter():
    if "https://" in conf.env.get("base_url", None):
        return conf.env.get("base_url", None)
    else:
        return "https://" + conf.env.get("base_url", None)
