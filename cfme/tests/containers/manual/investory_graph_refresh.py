import pytest

"""
Description:
Implement Inventory Graph Refresh for OpenShift to improve collection performance.
https://bugzilla.redhat.com/show_bug.cgi?id=1520488
"""


@pytest.mark.manual
def inventory_refresh_project():
    """
    - On the OpenShift Provider, add a new Project and record the name
    - Verify the Project does not exist on the CloudForm appliance
    - Manually Refresh the CloudForms appliance
    - Verify the Project exists on the CloudForms Appliance
    - Edit the Project
    - Verify the updates are not present on CloudForms appliance
    - Refresh the CloudForms appliance
    - Verify updates are present on CloudForms appliance
    - Deleted the Project
    - Verify the Project exists on the CloudForms Appliance
    - Refresh the CloudForms appliance
    - Verify the Project does not exist on the CloudForms Appliance
    - On the OpenShift Provider, add a new Project and record the name
    - Verify the Project exists on the CloudForms Appliance after an Auto Refresh has run
    """
    pass


@pytest.mark.manual
def inventory_refresh_route():
    """
    - On the OpenShift Provider, add a new Route and record the name
    - Verify the Route does not exist on the CloudForm appliance
    - Manually Refresh the CloudForms appliance
    - Verify the Route exists on the CloudForms Appliance
    - Edit the Route
    - Verify the updates are not present on CloudForms appliance
    - Refresh the CloudForms appliance
    - Verify updates are present on CloudForms appliance
    - Deleted the Route
    - Verify the Route exists on the CloudForms Appliance
    - Refresh the CloudForms appliance
    - Verify the Route does not exist on the CloudForms Appliance
    - On the OpenShift Provider, add a new Route and record the name
    - Verify the Route exists on the CloudForms Appliance after an Auto Refresh has run
    """
    pass


@pytest.mark.manual
def inventory_refresh_volume():
    """
    - On the OpenShift Provider, add a new Volume and record the name
    - Verify the Volume does not exist on the CloudForm appliance
    - Manually Refresh the CloudForms appliance
    - Verify the Volume exists on the CloudForms Appliance
    - Deleted the Volume
    - Verify the Volume exists on the CloudForms Appliance
    - Refresh the CloudForms appliance
    - Verify the Volume does not exist on the CloudForms Appliance
    - On the OpenShift Provider, add a new Volume and record the name
    - Verify the Volume exists on the CloudForms Appliance after an Auto Refresh has run
    """
    pass


@pytest.mark.manual
def inventory_refresh_container_template():
    """
    - On the OpenShift Provider, add a new Container Template and record the name
    - Verify the Container Template does not exist on the CloudForm appliance
    - Manually Refresh the CloudForms appliance
    - Verify the Container Template exists on the CloudForms Appliance
    - Deleted the Container Template
    - Verify the Container Template exists on the CloudForms Appliance
    - Refresh the CloudForms appliance
    - Verify the Container Template does not exist on the CloudForms Appliance
    - On the OpenShift Provider, add a new Container Template and record the name
    - Verify the Container Template exists on the CloudForms Appliance after an Auto Refresh has run
    """
    pass


@pytest.mark.manual
def inventory_refresh_service():
    """
    - On the OpenShift Provider, add a new Service and record the name
    - Verify the Service does not exist on the CloudForm appliance
    - Manually Refresh the CloudForms appliance
    - Verify the Service exists on the CloudForms Appliance
    - Edit the Service
    - Verify the updates are not present on CloudForms appliance
    - Refresh the CloudForms appliance
    - Verify updates are present on CloudForms appliance
    - Deleted the Service
    - Verify the Service exists on the CloudForms Appliance
    - Refresh the CloudForms appliance
    - Verify the Service does not exist on the CloudForms Appliance
    - On the OpenShift Provider, add a new Service and record the name
    - Verify the Service exists on the CloudForms Appliance after an Auto Refresh has run
    """
    pass


@pytest.mark.manual
def inventory_refresh_pod():
    """
    - On the OpenShift Provider, add a new Pod and record the name
    - Verify the Pod does exists on the CloudForm appliance due to the auto refresh
    - Stop the pod
    - Verify the action triggers an automatic refresh
    - Verify the CloudForms appliance data is updated correctly
    - Start the pod
    - Verify the action triggers an automatic refresh
    - Verify the CloudForms appliance data is updated correctly
    - Schedule a new pod
    - Verify the action triggers an automatic refresh
    - Verify the CloudForms appliance data is updated correctly
    - Schedule a new pod but cause it to failed scheduling
    - Verify the action triggers an automatic refresh
    - Verify the CloudForms appliance data is updated correctly
    - Create a pod but cause it to fail validation
    - Verify the action triggers an automatic refresh
    - Verify the CloudForms appliance data is updated correctly
    - Kill the pod
    - Verify the action triggers an automatic refresh
    - Verify the CloudForms appliance data is updated correctly
    """
    pass


@pytest.mark.manual
def inventory_refresh_replication_controller():
    """
    - On the OpenShift Provider, add a new Replication Controller and record the name
    - Verify the Replication Controller does exists on the CloudForm appliance due to
    the auto refresh
    - Add a new Replication Controller but cause it to fail to create
    - Verify the action triggers an automatic refresh
    - Verify the CloudForms appliance data is updated correctly
    - Deleted the Replication Controller
    - Verify the Replication Controller exists on the CloudForms Appliance
    - Refresh the CloudForms appliance
    - Verify the Replication Controller does not exist on the CloudForms Appliance
    """

    pass


@pytest.mark.manual
def inventory_refresh_container_image():
    """
    - On the OpenShift Provider, add a new Container Image and record the name
    - Verify the Container Image does not exist on the CloudForm appliance
    - Manually Refresh the CloudForms appliance
    - Verify the Container Image exists on the CloudForms Appliance
    - Deleted the Container Image
    - Verify the Container Image exists on the CloudForms Appliance
    - Refresh the CloudForms appliance
    - Verify the Container Image does not exist on the CloudForms Appliance
    - On the OpenShift Provider, add a new Container Image and record the name
    - Verify the Container Image exists on the CloudForms Appliance after an Auto Refresh has run
    """
    pass


@pytest.mark.manual
def inventory_refresh_node():
    """
    - On the OpenShift Provider, add a new Node and record the name
    - Verify the Node does not exist on the CloudForm appliance due to the auto refresh
    - Verify the CNode does not exist on the CloudForm appliance
    - Manually Refresh the CloudForms appliance
    - Verify the Node exists on the CloudForms Appliance
    - Reboot the Node
    - Verify the action triggers an automatic refresh
    - Verify the CloudForms appliance data is updated correctly
    - Mark the Node "Not Ready"
    - Verify the action triggers an automatic refresh
    - Verify the CloudForms appliance data is updated correctly
     - Mark the Node "Ready"
    - Verify the action triggers an automatic refresh
    - Verify the CloudForms appliance data is updated correctly
    - Mark the Node "Not Schedulable"
    - Verify the action triggers an automatic refresh
    - Verify the CloudForms appliance data is updated correctly
    - Mark the Node "Schedulable"
    - Verify the action triggers an automatic refresh
    - Verify the CloudForms appliance data is updated correctly
    - Deleted the Node
    - Verify the Node exists on the CloudForms Appliance
    - Refresh the Node
    - Verify the Node does not exist on the CloudForms Appliance
    """
    pass


@pytest.mark.manual
def inventory_refresh_container():
    """
    - On the OpenShift Provider, add a new Container and record the name
    - Verify the Container does not exist on the CloudForm appliance
    - Manually Refresh the CloudForms appliance
    - Verify the Container exists on the CloudForms Appliance
    - Edit the Container
    - Verify the updates are not present on CloudForms appliance
    - Refresh the CloudForms appliance
    - Verify updates are present on CloudForms appliance
    - Deleted the Container
    - Verify the Container exists on the CloudForms Appliance
    - Refresh the CloudForms appliance
    - Verify the Container does not exist on the CloudForms Appliance
    - On the OpenShift Provider, add a new Container and record the name
    - Verify the Container exists on the CloudForms Appliance after an Auto Refresh has run
    """
    pass


@pytest.mark.manual
def inventory_refresh_container_registry():
    """
    - On the OpenShift Provider, add a new Container Registry and record the name
    - Verify the Container Registry does not exist on the CloudForm appliance
    - Manually Refresh the CloudForms appliance
    - Verify the Container Registry exists on the CloudForms Appliance
    - Deleted the Container Registry
    - Verify the Container Registry exists on the CloudForms Appliance
    - Refresh the CloudForms appliance
    - Verify the Container Registry does not exist on the CloudForms Appliance
    - On the OpenShift Provider, add a new Container Registry and record the name
    - Verify the Container Registry exists on the CloudForms Appliance after an Auto Refresh has run
    """
    pass


@pytest.mark.manual
def inventory_refresh_build():
    """
    - On the OpenShift Provider, add a new Build and record the name
    - Verify the Build does not exist on the CloudForm appliance
    - Manually Refresh the CloudForms appliance
    - Verify the Build exists on the CloudForms Appliance
    - Deleted the Build
    - Verify the Build exists on the CloudForms Appliance
    - Refresh the CloudForms appliance
    - Verify the Build does not exist on the CloudForms Appliance
    - On the OpenShift Provider, add a new Build and record the name
    - Verify the Build exists on the CloudForms Appliance after an Auto Refresh has run
    """
    pass


@pytest.mark.manual
def inventory_refresh_pod_template_object_null():
    """
    - Create a new pod
    - Verify the pod was created
    - Edit the pod, replace the objects list with 'objects: null', saved the changes
    - Verify the Pod changed were saved
    - Refresh the provider
    - Verify no ERRORs were observed
    """
    pass
