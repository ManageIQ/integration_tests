#!/bin/bash
# This file briefly describes the steps and can execute those as well - to create Approle Token.
# make sure to have exported VAULT_ADDR=https://addr:port
# and VAULT_SKIP_VERIFY=true to disable ssl verification

echo 'login with kerberos - make sure you are admin by reading listed policies'
vault login -method=ldap -tls-skip-verify=true username=<user>

# =======================================================================================
# NOTE: we do not need to run this every time, but only when you need a new AppRole Token.
echo 'write policy'
vault policy write cfme-qe-infra-ro-policy cfme-qe-infra-ro-policy.json

echo 'enable AppRole auth'
vault auth enable approle

echo 'create an AppRole called'
vault write auth/approle/role/cfme-qe-infra secret_id_ttl=10m secret_id_num_uses=0 token_num_uses=20 token_ttl=30m token_max_ttl=60m policies=cfme-qe-infra-ro-policy

echo 'Creating a Limited-Use Token'
vault policy write cfme-qe-infra-approle-token cfme-qe-infra-approle-token.json
vault token create -policy=cfme-qe-infra-approle-token
# =======================================================================================

echo  'Set following env variable.'
echo  'export VAULT_ENABLED_FOR_DYNACONF=true'
echo  'export VAULT_URL_FOR_DYNACONF=https://infra-assets.cfme2.lab.eng.rdu2.redhat.com:8201'
echo  'export VAULT_APPROLE_TOKEN=<token generated in previous step>'
echo  'export VAULT_VERIFY_FOR_DYNACONF=false'
