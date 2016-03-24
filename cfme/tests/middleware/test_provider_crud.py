from cfme.middleware.hawkular import HawkularProvider
from cfme import login

login.login_admin()

hawkular = HawkularProvider('My Hawkular', 'livingontheedge.hawkular.org', '80')

hawkular.create(cancel=False, validate_credentials=False)