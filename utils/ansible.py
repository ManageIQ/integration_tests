import tempfile
from os import listdir, mkdir, makedirs, path
from shutil import copy, copyfile, rmtree
from subprocess import check_output, CalledProcessError, STDOUT

from fauxfactory import gen_alphanumeric
from utils import conf
from utils.providers import get_crud

from git import Repo
from yaml import load, dump

local_git_repo = "manageiq_ansible_module"
yml_path = path.join(path.dirname(__file__), local_git_repo)
yml_templates_path = path.join(path.dirname(__file__), 'ansible_conf')
yml = ".yml"
random_token = str(gen_alphanumeric(906))
random_miq_user = str(gen_alphanumeric(8))
pulled_repo_library_path = path.join(local_git_repo, 'library')
remote_git_repo_url = "git://github.com/dkorn/manageiq-ansible-module.git"


def create_tmp_directory():
    global lib_path
    lib_path = tempfile.mkdtemp()
    lib_sub_path = 'ansible_conf'
    lib_sub_path_library = path.join(lib_sub_path, 'library')
    makedirs(path.join((lib_path), lib_sub_path_library))
    global library_path_to_copy_to
    global basic_yml_path
    library_path_to_copy_to = path.join(lib_path, lib_sub_path_library)
    basic_yml_path = path.join(lib_path, lib_sub_path)


def fetch_miq_ansible_module():
    if path.isdir(local_git_repo):
        rmtree(local_git_repo)
    mkdir(local_git_repo)
    if path.isdir(library_path_to_copy_to):
        rmtree(library_path_to_copy_to)
    mkdir(library_path_to_copy_to)
    Repo.clone_from(remote_git_repo_url, local_git_repo)
    src_files = listdir(pulled_repo_library_path)
    for file_name in src_files:
        full_file_name = path.join(pulled_repo_library_path, file_name)
        if path.isfile(full_file_name):
            copy(full_file_name, library_path_to_copy_to)
    rmtree(local_git_repo)


def get_values_for_providers_test(provider):
    return {
        'name': provider.name,
        'state': 'present',
        'miq_url': config_formatter(),
        'miq_username': conf.credentials['default'].username,
        'miq_password': conf.credentials['default'].password,
        'provider_api_hostname': conf.cfme_data.get('management_systems', {})
        [provider.key].get('hostname', []),
        'provider_api_auth_token': get_crud('cm-env1').credentials['token'].token,
        'hawkular_hostname': conf.cfme_data.get('management_systems', {})
        [provider.key].get('hostname', [])
    }


def get_values_for_users_test(provider):
    return {
        'fullname': 'MIQUser',
        'name': 'MIQU',
        'password': 'smartvm',
        'state': 'present',
        'miq_url': config_formatter(),
        'miq_username': conf.credentials['default'].username,
        'miq_password': conf.credentials['default'].password,
    }


def get_values_for_custom_attributes_test(provider):
    return {
        'entity_type': 'provider',
        'entity_name': conf.cfme_data.get('management_systems', {})
        [provider.key].get('name', []),
        'miq_url': config_formatter(),
        'miq_username': conf.credentials['default'].username,
        'miq_password': conf.credentials['default'].password,
    }


def get_values_from_conf(provider, script_type):
    if script_type == 'providers':
        return get_values_for_providers_test(provider)
    if script_type == 'users':
        return get_values_for_users_test(provider)
    if script_type == 'custom_attributes':
        return get_values_for_custom_attributes_test(provider)


# TODO Avoid reading files every time
def read_yml(script, value):
    with open(yml_path + script + yml, 'r') as f:
            doc = load(f)
    return doc[0]['tasks'][0]['manageiq_provider'][value]


def get_yml_value(script, value):
    with open(path.join(basic_yml_path, script) + yml, 'r') as f:
            doc = load(f)
    return doc[0]['tasks'][0]['manageiq_provider'][value]


def setup_basic_script(provider, script_type):
    script_path_source = path.join(yml_templates_path, script_type + "_" + basic_script)
    script_path = path.join(basic_yml_path, script_type + "_" + basic_script)
    copyfile(script_path_source, script_path)
    with open(script_path, 'rw') as f:
        doc = load(f)
        values_dict = get_values_from_conf(provider, script_type)
    for key in values_dict:
        if script_type == 'providers':
            doc[0]['tasks'][0]['manageiq_provider'][key] = values_dict[key]
        elif script_type == 'users':
            doc[0]['tasks'][0]['manageiq_user'][key] = values_dict[key]
        elif script_type == 'custom_attributes':
            doc[0]['tasks'][0]['manageiq_custom_attributes'][key] = values_dict[key]
        with open(script_path, 'w') as f:
            f.write(dump(doc))


def open_yml(script, script_type):
    copyfile((path.join(basic_yml_path, script_type + "_" + basic_script)),
             path.join(basic_yml_path, script + yml))
    with open(path.join(basic_yml_path, script + yml), 'rw') as f:
        return load(f)


def write_yml(script, doc):
    with open(path.join(basic_yml_path, script + yml), 'w') as f:
        f.write(dump(doc))


def setup_ansible_script(provider, script, script_type=None, values_to_update=None):
    # This function prepares the ansible scripts to work with the correct
    # appliance configs that will be received from Jenkins
    setup_basic_script(provider, script_type)
    if script == 'add_provider':
        copyfile(path.join(basic_yml_path, providers_basic_script),
                 path.join(basic_yml_path, script + yml))

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


def run_ansible(script):
    cmd = "ansible-playbook " + path.join(basic_yml_path, script + yml)
    try:
        response = check_output(cmd, shell=True, stderr=STDOUT)
    except CalledProcessError as exc:
        print("Status : FAIL", exc.returncode, exc.output)
        return exc.output
    else:
        print("Output: \n{}\n".format(response))


# TODO For further usage with reply statuses test. Not being used at the moment
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


def config_formatter():
    if "https://" in conf.env.get("base_url", None):
        return conf.env.get("base_url", None)
    else:
        return "https://" + conf.env.get("base_url", None)


def remove_tmp_files():
    rmtree(lib_path, ignore_errors=True)
