from cfme.utils.version import Version
from cfme.utils.version import VersionPicker

app_menu_v5_10 = {
    "config_net": "1",
    "set_timezone": "2",
    "set_date_time": "3",
    "create_db_bak": "4",
    "create_db_dump": "5",
    "restore_db_from_bak": "6",
    "config_db": "7",
    "config_db_rep": "8",
    "logfile_conf": "9",
    "config_app_db_failover_monitor": "10",
    "ext_temp_storage": "11",
    "config_external_auth": "12",
    "update_ext_auth_opt": "13",
    "gen_custom_encry_key": "14",
    "harden_app_scap_config": "15",
    "stop_evm": "16",
    "start_evm": "17",
    "restart_app": "18",
    "showdown_app": "19",
    "summary_info": "20",
    "quit": "21",
}

app_menu_v5_11 = {
    "config_net": "1",
    "create_db_bak": "2",
    "create_db_dump": "3",
    "restore_db_from_bak": "4",
    "config_db": "5",
    "config_db_rep": "6",
    "logfile_conf": "7",
    "config_app_db_failover_monitor": "8",
    "ext_temp_storage": "9",
    "config_external_auth": "10",
    "update_ext_auth_opt": "11",
    "gen_custom_encry_key": "12",
    "harden_app_scap_config": "13",
    "stop_evm": "14",
    "start_evm": "15",
    "restart_app": "16",
    "showdown_app": "17",
    "summary_info": "18",
    "quit": "19",
}
app_con_menu = VersionPicker({Version.lowest(): app_menu_v5_10, "5.11": app_menu_v5_11}).pick()
