import os

from dynaconf import LazySettings
from hvac import Client

VAULT_APPROLE = 'cfme-qe-infra'
extra_dynaconf_args = {}

# The process to authenticate is to basically create AppRole Token and use that to authenticate
# with vault and every time you authenticate also renew the token. That token will allow you
# to create role_id and secret_id which together lets you authenticate to AppRole
vault_approle_token = os.environ.get("VAULT_APPROLE_TOKEN", None)
vault_url = os.environ.get("VAULT_URL_FOR_DYNACONF", None)


def _login_and_renew_token(url, token):
    """Log into Vault, renew the token, and return the Vault client"""
    vault = Client(url=url, token=token, verify=False)
    if not vault.is_authenticated():
        return None
    # Renew the token so that it's valid for another 7 days
    vault.renew_token()
    return vault


def _get_approle_ids(url, token):
    vault = _login_and_renew_token(url, token)
    if not vault:
        return None
    role_id = vault.get_role_id(VAULT_APPROLE)
    secret_id = vault.create_role_secret_id(VAULT_APPROLE).get("data", {}).get("secret_id")
    return {"role_id": role_id, "secret_id": secret_id}


if vault_approle_token and vault_url:
    # Generate secret id
    vault_approle_ids = _get_approle_ids(vault_url, vault_approle_token)
    if not vault_approle_ids:
        raise Exception(f"Cannot auth with Vault with AppRole token '{vault_approle_token}'")
    extra_dynaconf_args.update(
        {
            "VAULT_ROLE_ID": vault_approle_ids["role_id"],
            "VAULT_ROLE_ID_FOR_DYNACONF": vault_approle_ids["role_id"],  # Jenkins vault
            "VAULT_SECRET_ID": vault_approle_ids["secret_id"],
            "VAULT_SECRET_ID_FOR_DYNACONF": vault_approle_ids["secret_id"],  # Jenkins vault
        }
    )
settings = LazySettings(
    VAULT_PATH_FOR_DYNACONF="cfme-qe-sprout",
    VAULT_VERIFY_FOR_DYNACONF=False,
    VAULT_ENABLED_FOR_DYNACONF=True,
    **extra_dynaconf_args
)
