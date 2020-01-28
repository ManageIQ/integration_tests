"""Test requirements mapping

This module contains predefined pytest markers for MIQ/CFME product requirements.

Please import the module instead of elements:

.. code-block:: python

    from cfme import test_requirements

    pytestmark = [test_requirements.alert]

    @test_requirements.quota
    def test_quota_alert():
        pass

The markers can have metadata kwargs assigned to them
These fields will be parsed for dump2polarion export, and will populate the work items in polarion

The first argument to the marker definition is the title of the requirement.
The assigned name of the marker object is equivalent to the 'short name' of the requirement.

Example:
    .. code-block:: python
        # A requirement for automate domain import
        import = pytest.mark.requirement(
            'Automate Domain Import',
            description='Import of automate domain items via a SCM repository'
            assignee_id='mshriver',
            approver_ids='izapolsk:approved',
            severity_id='must_have'
        )

Included for quick reference, but potentially inaccurate
See dump2polarion.exporters.requirements_exporter for up-to-date information
Above module is converting pythonic keys (assignee_id) into polarion compatible keys ('assignee-id')
Supported requirement metadata fields (and example data)
    .. code-block:: python
        {
            "title": "requirement_complete",
            "description": "Complete Requirement",
            "approver_ids": "mkourim:approved",
            "assignee_id": "mkourim",
            "category_ids": "category_id1, category_id2",
            "due_date": "2018-09-30",
            "planned_in_ids": "planned_id1 planned_id2",
            "initial_estimate": "1/4h",
            "priority_id": "high",
            "severity_id": "should_have",
            "status_id": "status_id",
            "reqtype": "functional",
        }

"""
import pytest


ansible = pytest.mark.requirement(
    "Ansible Automation",
    description='Embedded Ansible Automation Requirement',
    assignee_id='sbulage',
)

access = pytest.mark.requirement(
    "Access",
    description='Direct integration of SaaS offerings in MIQ/CFME',
    assignee_id='juwatts',
    planned_in_ids="5_11",
)

alert = pytest.mark.requirement(
    "Alerts",
    description='Alerting in MIQ',
    assignee_id='jdupuy',
)

appliance = pytest.mark.requirement(
    "Appliance",
    description='Appliance',
    assignee_id='jhenner'
)

app_console = pytest.mark.requirement(
    "Appliance Console",
    description='Appliance console operations support',
    assignee_id='mnadeem'
)

auth = pytest.mark.requirement(
    "Authentication",
    description='Authentication in MIQ/CFME, external authentication provider support',
    assignee_id='jdupuy',
)

automate = pytest.mark.requirement(
    "Automate",
    description='Automate and related control behavior',
    assignee_id='ghubale',
)

azure = pytest.mark.requirement(
    'Azure Integration',
    description='Integration of Azure in MIQ/CFME',
    assignee_id='anikifor',
)

bottleneck = pytest.mark.requirement(
    "Optimization and Bottleneck",
    description='Optimizations and Bottleneck ID, planned deprecation',
    assignee_id='nachandr',
    planned_in_ids="5_10",
)

c_and_u = pytest.mark.requirement(
    "Capacity and Utilization",
    description='Capacity and Utilization data collection',
    assignee_id='nachandr',
)

chargeback = pytest.mark.requirement(
    "Chargeback",
    description='Chargeback rates, calculations, and reports',
    assignee_id='tpapaioa',
)

cloud = pytest.mark.requirement(
    "Cloud",
    description='Generic cloud',
    assignee_id='mmojzis'
)

cloud_init = pytest.mark.requirement(
    "Provisioning with cloud_init",
    description='Provisioning lifecycle with cloud-init resource configuration',
    assignee_id='',  # FIXME needs assigned
)

configuration = pytest.mark.requirement(
    "Configuration",
    description='Configuration pages of MIQ/CFME, also partially covered by specific requirements',
    assignee_id='tpapaioa',
)

control = pytest.mark.requirement(
    "Control",
    description='Control / Compliance policies and enforcement',
    assignee_id='jdupuy',
)

containers = pytest.mark.requirement(
    "Containers",
    description='Integration of OpenShift in MIQ/CFME',
    assignee_id='juwatts',
)

cockpit = pytest.mark.requirement(
    "Cockpit",
    description='Cockpit web console for VMs',
    assignee_id='nansari'
)

custom_button = pytest.mark.requirement(
    "Custom Buttons",
    description='Custom Buttons and Custom Groups',
    assignee_id='ndhandre',
)

customer_stories = pytest.mark.requirement(
    "Customer Stories",
    description='Integration of multiple FAs, Day 2 Operations type tests',
    assignee_id='ndhandre',
)

dashboard = pytest.mark.requirement(
    "Dashboard",
    description='MIQ/CFME Dashboards creation, usability',
    assignee_id='jhenner',
)

dialog = pytest.mark.requirement(
    "Service Dialogs",
    description='Service dialogs, creation and form behavior on order',
    assignee_id='nansari',
)

discovery = pytest.mark.requirement(
    "Provider Discovery",
    description='Discovery of Cloud/Infra/etc providers',
    assignee_id='pvala',
)

distributed = pytest.mark.requirement(
    "Distributed Appliances",
    description='Distributed Appliance deployment, configuration, and interaction',
    assignee_id='tpapaioa',
)

drift = pytest.mark.requirement(
    "Drift Analysis",
    description='Drift benchmarking and analysis of MIQ entities (host, instance)',
    assignee_id='sbulage',
)

events = pytest.mark.requirement(
    "Events",
    description='Provider event handling in MIQ/CFME (not including timelines)',
    assignee_id='jdupuy'
)

ec2 = pytest.mark.requirement(
    "EC2Provider",
    description='EC2Provider integration with CFME',
    assignee_id='mmojzis'
)

filtering = pytest.mark.requirement(
    "Searching and Filtering",
    description='Searching and Filtering in the UI/SSUI',
    assignee_id='anikifor',
)

genealogy = pytest.mark.requirement(
    "VM/Instance Genealogy",
    description='Genealogy of VMs/Instances in MIQ/CFME',
    assignee_id='spusater',
)

general_ui = pytest.mark.requirement(
    "General UI Components",
    description='General UI verification',
    assignee_id='pvala',
)

generic_objects = pytest.mark.requirement(
    "Generic Objects",
    description='Generic Object classes for automate',
    assignee_id='jdupuy',
)

html5 = pytest.mark.requirement(
    "VM Consoles: HTML5/SPICE",
    description='HTML5 and SPICE VM console support',
    assignee_id='apagac',
)

ipv6 = pytest.mark.requirement(
    "IPv6 Support",
    description='IPv6 support at all levels of CFME',
    assignee_id='',
)

infra_hosts = pytest.mark.requirement(
    "Infrastructure Hosts Support",
    description='Support functionality for infrastructure hosts',
    assignee_id='prichard',
)

log_depot = pytest.mark.requirement(
    "Log Collection and Depot",
    description='MIQ/CFME Log collection and storage',
    assignee_id='anikifor',
)

multi_region = pytest.mark.requirement(
    "MIQ Multi-Region deployments",
    description='Multi-Region deployment and Central Administration',
    assignee_id='izapolsk',
)

multi_tenancy = pytest.mark.requirement(
    "MIQ Multi-Tenancy",
    description='Support for Tenants in MIQ/CFME',
    assignee_id='nachandr',
)

ownership = pytest.mark.requirement(
    "VM/Instance Ownership",
    description='Ownership settings for VM/Instances',
    assignee_id='spusater',
)

power = pytest.mark.requirement(
    "Power Control from CFME",
    description='Power Control operations on virtualization resources',
    assignee_id='ghubale',
)

provision = pytest.mark.requirement(
    "Provisioning Lifecycle",
    description='Lifecycle and service provisioning on all providers',
    assignee_id='jhenner',
)

quota = pytest.mark.requirement(
    "Quota Setting and Enforcement",
    description='Setting and enforcement of virtualization resource quota through CFME',
    assignee_id='ghubale',
)

rbac = pytest.mark.requirement(
    "RoleBasedAccessControl (RBAC)",
    description='Role based access control testing of CFME authorization (Tenants, groups, roles)',
    assignee_id='apagac',
)

reconfigure = pytest.mark.requirement(
    "VM/Instance Reconfiguration",
    description='Reconfiguration options and execution through CFME',
    assignee_id='nansari',
)

relationships = pytest.mark.requirement(
    'Relationship Discovery',
    description='Discovery of entities related to providers, '
                'display and linking of those collections',
    assignee_id='ghubale',
)

replication = pytest.mark.requirement(
    "Appliance Database Replication",
    description='Replication between appliance instances',
    assignee_id='mnadeem',
)

report = pytest.mark.requirement(
    "Reporting",
    description='Intelligence reporting: creating, scheduling, and queuing reports',
    assignee_id='pvala',
)

rest = pytest.mark.requirement(
    "REST",
    description='REST API interactions, covering all of MIQ/CFME',
    assignee_id='pvala',
)

restore = pytest.mark.requirement(
    "CFME Database Backup Restore",
    description='Database backup and restore tests',
    assignee_id='jhenner',
)


retirement = pytest.mark.requirement(
    "VM/Instance Retirement",
    description='Retirement of VMs/Instances and visibility of objects after retirement',
    assignee_id='tpapaioa',
)

rhev = pytest.mark.requirement(
    'RHEV Integration',
    description='Integration of RHEVM and RHEVH in MIQ/CFME',
    assignee_id='anikifor',
)

right_size = pytest.mark.requirement(
    "Normal Operating Ranges and Right Size Recommendations",
    description='Normal Operating Ranges and Right Size Recommendations',
    assignee_id='tpapaioa',
)

satellite = pytest.mark.requirement(
    "Configuration Management: Satellite",
    description='Configuration Management providers, specifically Red Hat Satellite',
    assignee_id='tpapaioa',
)

scheduled_ops = pytest.mark.requirement(
    'Scheduled Operations',
    description='Scheduled Operations',
    assignee_id='jhenner',
)

scvmm = pytest.mark.requirement(
    'SCVMM Integration',
    description='Support of SCVMM in MIQ/CFME',
    assignee_id='jdupuy',
)

sdn = pytest.mark.requirement(
    "Software Defined Networking",
    description='Support for software defined network management on cloud providers',
    assignee_id='mmojzis',
)

service = pytest.mark.requirement(
    "Services",
    description='Services, catalog items, bundles, catalogs, retirement',
    assignee_id='nansari',
)

settings = pytest.mark.requirement(
    "Settings",
    description='Per-user appliance settings',
    assignee_id='pvala',
)

smartstate = pytest.mark.requirement(
    "Smartstate Analysis",
    description='Smartstate analysis on all providers',
    assignee_id='sbulage',
)

snapshot = pytest.mark.requirement(
    "VM/Instance Snapshots",
    description='Snapshot support and management',
    assignee_id='prichard',
)

ssui = pytest.mark.requirement(
    "Self-Service UI",
    description='SSUI interface and use',
    assignee_id='nansari',
)

stack = pytest.mark.requirement(
    "Orchestration Stacks",
    description='Cloud provider orchestration stack management and ordering',
    assignee_id='nansari',
)

storage = pytest.mark.requirement(
    "Block/Object Storage",
    description='Cloud provider storage management for volumes and blocks',
    assignee_id='mmojzis',
)

tag = pytest.mark.requirement(
    "Tagging",
    description='Tag creation, assignment, visibility',
    assignee_id='anikifor',
)

timelines = pytest.mark.requirement(
    "Event Timelines",
    description='Event Timelines',
    assignee_id='jdupuy',
)

tower = pytest.mark.requirement(
    "Configuration Management: Tower",
    description='Configuration Management providers, specifically Ansible Tower',
    assignee_id='nachandr',
)

update = pytest.mark.requirement(
    "CFME update tests",
    description='Application update tests',
    assignee_id='jhenner',
)

db_migration = pytest.mark.requirement(
    "CFME Database Migrations",
    description='Database migration tests',
    assignee_id='jhenner',
)

v2v = pytest.mark.requirement(
    'IMS V2V Migration',
    description='Migration of Instance/VM from one provider to another using IMS',
    assignee_id='sshveta',
)

vm_migrate = pytest.mark.requirement(
    "VM/Instance Migration",
    description='Storage/Compute migration of VM/Instances on single provider',
    assignee_id='mnadeem',
)

vmrc = pytest.mark.requirement(
    "VM Consoles: VMWare RC",
    description='VMWare Remote Console support',
    assignee_id='apagac',
)

vmware = pytest.mark.requirement(
    "VMWare Integration",
    description='Support of VMWare in MIQ/CFME',
    assignee_id='kkulkarn'
)

webmks = pytest.mark.requirement(
    "VM Consoles: VMWare WebMKS",
    description='VMWare WebMKS support',
    assignee_id='apagac',
)
