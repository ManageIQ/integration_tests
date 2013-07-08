import paramiko

def ssh_client(self, hostname, user, pwd):
    """ Create an ssh client that auto-accepts host heys"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, username=user, password=pwd, allow_agent=False)
    return client
