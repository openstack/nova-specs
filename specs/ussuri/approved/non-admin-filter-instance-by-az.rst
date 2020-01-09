..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================================
Non-Admin user can filter their instances by more filters
=========================================================

https://blueprints.launchpad.net/nova/+spec/non-admin-filter-instance-by-az

Many instances filter are restricted to admin-only users, while the related
attribute are readable when showing instance detail for non admin users.

In order to stay coherent, all existing instance filters that are related to a
field readable by default to non admin users when showing instance details,
should be allowed by default without policy modification.

Problem description
===================
The following instance filters are restricted to admin-only users (they are
ignored if provided by non admin), but the related attribute in server payload
are by default visible when displaying server informations:

- ``availability_zone``
- ``config_drive``
- ``key_name``
- ``created_at``
- ``launched_at``
- ``terminated_at``
- ``power_state``
- ``task_state``
- ``vm_state``
- ``progress``
- ``user_id``

This list was made by listing all existing admin-only instance filters [1]_,
extracting those where the related attribute is readable by default for
non-admin users in the nova server show API [2]_.

This spec target only existing filters for nova list API and does not aim to
add new one.

Use Cases
---------
It can be disturbing for a regular user who make some automation againt nova
API not to be able to filter its instances againt field he can consult without
any policy modification from operators, especially if the filter exist but is
qualified as admin-only.

By example, in a multiple availability zone deployment, it is a commonly
shared cloud pattern that users create their resources in multiple AZs in
order to get resilient in case of failure of one AZ.

Dealing with multiple availability zone can lead to complexity for the user,
by example in case of cinder usage, you can disable the ``cross_az_attach``
option to restrict volume attachment to be same AZ as the instance. In that
configuration, it can be really useful to the customer to be able to filter
their instance by AZ, by example in a user interface use-case, to display only
instance who can be attached to a given volume.

Proposed change
===============
Add a new microversion to servers list APIs to enable these filters
for non admin users.

As non admin filters are listed in the ``_get_server_search_options`` function
in ``nova/api/openstack/compute/servers.py``, it will only require to add
previously described values in that list for the given microversion.

Microversion bump is required in this context because API consumers need to
be able to discover whether they should expect this filter to work or not.
The mechanism for discovering that is by seeing whether a particular
microversion is supported, especially in this case where prior to this fix,
we'll silently ignore these filters and the consumer would have no good way
of knowing whether it worked or not. Hence why it is a blueprint and not a
bugfix.

Alternatives
------------
Currently the only way to allow non admin users to use these filters
is to edit the nova policy ``os_compute_api:servers:allow_all_filters``,
which can be really painful to maintain during upgrades and can cause security
issue as you don't want regular user to use filters like the hypervisor or node
one.

Data model impact
-----------------
None

REST API impact
---------------
A new microversion will be added as we change the behaviour of the API for
non admin users, even if we don't add or remove any parameter.

List API will no longer ignore query string parameter for the following filters
for regular user:

- ``availability_zone``
- ``config_drive``
- ``key_name``
- ``created_at``
- ``launched_at``
- ``terminated_at``
- ``power_state``
- ``task_state``
- ``vm_state``
- ``progress``
- ``user_id``

.. code::

  GET /servers?availability_zone=az2
  GET /servers/detail?availability_zone=az1
  GET /servers/detail?key_name=my_key&config_drive=True

Security impact
---------------
None

Notifications impact
--------------------
None

Other end user impact
---------------------
Python client may add help to inform users this new filter.
Add support for the these filters in python-novaclient for the 'nova list'
command.

Performance Impact
------------------
None

Other deployer impact
---------------------
None

Developer impact
----------------
None

Upgrade impact
--------------
None

Implementation
==============

Assignee(s)
-----------
Primary assignee:
  Victor Coutellier

Feature Liaison
---------------
Feature liaison:
  Balazs Gibizer
  Ghanshyam Mann

Work Items
----------
* Add filters to the non-admin whitelisted instance filters
* Add related test
* Add support for these filters to the 'nova list' operation in novaclient

Dependencies
============
None

Testing
=======
* Add related unittest
* Add related functional test

Documentation Impact
====================
The nova API documentation will need to be updated to reflect the
REST API changes, and adding microversion instructions.

References
==========
.. [1] All admin only server filters https://docs.openstack.org/api-ref/compute/?expanded=list-servers-detail#list-servers
.. [2] Server attributes returned to non-admin https://docs.openstack.org/api-ref/compute/?expanded=show-server-details-detail#show-server-details

History
=======
.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ussuri
     - Introduced
