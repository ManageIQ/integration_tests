import os
import subprocess
import yaml
from utils import conf
from shutil import copyfile


yml_path = os.path.dirname(__file__) + "/manageiq_ansible_module/"
providers_basic_script = "providers_basic_script.yml"
users_basic_script = "users_basic_script.yml"


def get_values_from_conf(provider, script_type):
    #TODO Clean this shit
    if script_type == 'providers':
        return {
            'name': 'Openshift 3',
            'state': 'present',
            'miq_url': conf.env.get("base_url", None),
            'miq_username': 'admin',
            'miq_password': 'smartvm',
            'provider_api_hostname': conf.cfme_data.get('management_systems', {})
            [provider.key].get('hostname', []),
            'provider_api_auth_token': conf.credentials['openshift-3'].token,
            'hawkular_hostname': conf.cfme_data.get('management_systems', {})
            [provider.key].get('hostname', [])
        }
    elif script_type == 'users':
        return {
            'fullname': 'MIQUser',
            'name': 'MIQU',
            'password': 'smartvm',
            'state': 'present',
            'miq_url': conf.env.get("base_url", None),
            'miq_username': 'admin',
            'miq_password': 'smartvm'
        }


# TODO Avoid reading files every time


def read_yml(script, value):
    with open(yml_path + script + ".yml", 'r') as f:
            doc = yaml.load(f)
    return doc[0]['tasks'][0]['manageiq_provider'][value]


def get_yml_value(script, value):
    with open(yml_path + script + ".yml", 'r') as f:
            doc = yaml.load(f)
    return doc[0]['tasks'][0]['manageiq_provider'][value]


def setup_basic_script(provider, script_type):
    with open(yml_path + script_type + "_basic_script.yml", 'rw') as f:
        doc = yaml.load(f)
        values_dict = get_values_from_conf(provider, script_type)
    for key in values_dict:
        if script_type == 'providers':
            doc[0]['tasks'][0]['manageiq_provider'][key] = values_dict[key]
        elif script_type == 'users':
            doc[0]['tasks'][0]['manageiq_user'][key] = values_dict[key]
        with open(yml_path + script_type + "_basic_script.yml", 'w') as f:
            f.write(yaml.dump(doc))


def open_yml(script, script_type):
    copyfile(yml_path + "/" + script_type + "_basic_script.yml", yml_path + script + ".yml")
    with open(yml_path + script + ".yml", 'rw') as f:
        return yaml.load(f)


def write_yml(script,doc):
    with open(yml_path + script + ".yml", 'w') as f:
        f.write(yaml.dump(doc))


def setup_ansible_script(provider, script, script_type=0, values_to_update=0, user_name=0):
    # This function prepares the ansible scripts to work with the correct
    # appliance configs that will be received from Jenkins
    setup_basic_script(provider, script_type)
    if script == 'add_provider':
        copyfile(yml_path + providers_basic_script, yml_path + script + ".yml")

    elif script == 'update_provider':
        doc = open_yml(script, 'providers')
        for key in values_to_update:
            doc[0]['tasks'][0]['manageiq_provider'][key] = values_to_update[key]
            write_yml(script,doc)

    elif script == 'remove_provider':
        doc = open_yml(script, 'providers')
        doc[0]['tasks'][0]['manageiq_provider']['state'] = 'absent'
        write_yml(script,doc)

    elif script == 'create_user':
        doc = open_yml(script, "users")
        for key in values_to_update:
            doc[0]['tasks'][0]['manageiq_user'][key] = values_to_update[key]
            with open(yml_path + script + ".yml", 'w') as f:
                f.write(yaml.dump(doc))

    elif script == 'update_user':
        doc = open_yml(script, "users")
        for key in values_to_update:
            doc[0]['tasks'][0]['manageiq_user'][key] = values_to_update[key]
            with open(yml_path + script + ".yml", 'w') as f:
                f.write(yaml.dump(doc))

    elif script == 'delete_user':
        doc = open_yml(script, "users")
        doc[0]['tasks'][0]['manageiq_user']['name'] = values_to_update
        doc[0]['tasks'][0]['manageiq_user']['state'] = 'absent'
        with open(yml_path + script + ".yml", 'w') as f:
                f.write(yaml.dump(doc))


def run_ansible(script):
    subprocess.check_output(["ansible-playbook", yml_path + script + ".yml"])
