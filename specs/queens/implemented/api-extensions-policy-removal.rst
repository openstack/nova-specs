..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================
API Extensions Policy Removal
=============================

https://blueprints.launchpad.net/nova/+spec/api-extensions-policy-removal

This spec is to deprecate the API extensions policy which are
specially added when API extensions were introduced.


Problem description
===================

Nova API extension concept is removed in Pike. But code is still present across
different files.
For Example: api/openstack/compute/extended_availability_zone.py extensions
adds the AZ in GET server API with extending the Show, Detail methods.

These extensions code have their own policies enforcement.
For example, extended_availability_zone.py which extend the GET server API
response and has policy 'os_compute_api:os-extended-availability-zone'.
Due to that, GET server API have multiple policies enforcement:
show server policy + each extensions policies.

As there is no way to enable/disable extensions in API but we allow
extensions policies to control the APIs in term of their extended behavior.

This can cause the interoprability issue which was one of the issue got solved
by removing the API extensions concept.

Also I cannot find any real use case for these policies, these were added along
with extensions.

Use Cases
---------

* As an operator, I want clean and very clear policies for APIs. Multiple
  policies controlling single APIs for different response element might
  not be good and clear always.

* As an API developer, I want easy to maintain the policies for APIs by
  cleaning up the legacy extensions policies.

Proposed change
===============

This spec propose to deprecate the below policies which are very much specific
to API extensions and not default to admin only.

Server extensions:

* Config Drive:

  * File: api/openstack/compute/config_drive.py
  * Purpose: add the 'config_drive' in GET server response
  * Policies: 'os_compute_api:os-config-drive'
  * Policy Enforcement: Soft (Not Raising exception)
  * Proposal: To deprecate.

* Extended AZ:

  * File: api/openstack/compute/extended_availability_zone.py
  * Purpose: add the 'OS-EXT-AZ:availability_zone' in GET server response
  * Policies: 'os_compute_api:os-extended-availability-zone'
  * Policy Enforcement: Soft (Not Raising exception)
  * Proposal: To deprecate.

* Extended Status:

  * File: api/openstack/compute/extended_status.py
  * Purpose: add server status ('task_state', 'vm_state', 'power_state'])
    attributes in GET server response
  * Policies: 'os_compute_api:os-extended-status'
  * Policy Enforcement: Soft (Not Raising exception)
  * Proposal: To deprecate.

* Extended Volume:

  * File: api/openstack/compute/extended_volumes.py
  * Purpose: add the 'os-extended-volumes:volumes_attached' in GET server
    response.
  * Policies: 'os_compute_api:os-extended-volumes'
  * Policy Enforcement: Soft (Not Raising exception)
  * Proposal: To deprecate.

* Hide Server Addresses:
  This is going to be taken care by other BP.
  - https://blueprints.launchpad.net/nova/+spec/remove-configurable-hide-server-address-feature

* Keypairs:

  * File: api/openstack/compute/keypairs.py
  * Purpose: add the 'key_name' in GET server response
  * Policies: 'os_compute_api:os-keypairs'
  * Policy Enforcement: Soft (Not Raising exception)
  * Proposal: To deprecate.

* Security Groups:

  * File: api/openstack/compute/security_groups.py
  * Purpose: add the 'security_groups' in GET, POST server response
  * Policies: 'os_compute_api:os-security-groups'
  * Policy Enforcement: Soft (Not Raising exception)
  * NOTE: Same policy is used by other security group API, so proposal here is
    to remove the policy enforcement from GET, POST server API only.
  * Proposal: To deprecate from GET, POST /servers API only.

* Server Usage:

  * File: api/openstack/compute/server_usage.py
  * Purpose: add the 'OS-SRV-USG:launched_at', 'OS-SRV-USG:terminated_at' in
    GET server response.
  * Policies: 'os_compute_api:os-server-usage'
  * Policy Enforcement: Soft (Not Raising exception)
  * Proposal: To deprecate.

Flavor extensions:

* Flavor rxtx:

  * File: api/openstack/compute/flavor_rxtx.py
  * Purpose: add the 'os-flavor-rxtx' in GET, POST flavor response
  * Policies: 'os_compute_api:os-flavor-rxtx'
  * Policy Enforcement: Soft (Not Raising exception)
  * Proposal: To deprecate.

* Flavor Access:

  * File: api/openstack/compute/flavor_access.py
  * Purpose: add the 'os-flavor-access:is_public' in GET, POST flavor response
  * Policies: 'os_compute_api:os-flavor-access'
  * Policy Enforcement: Soft (Not Raising exception)
  * NOTE: This policy is used by flavor access API also
    (GET /flavors/{flavor_id}/os-flavor-access), which will not be changed.
    Proposal here is to remove this policy enforcement from GET, POST flavor
    API only.
  * Proposal: To deprecate for  GET, POST /flavors API only.

Image extensions:

* Image Size:

  * File: api/openstack/compute/image_size.py
  * Purpose: add the 'OS-EXT-IMG-SIZE:size' in GET image response
  * Policies: 'os_compute_api:image-size'
  * Policy Enforcement: Soft (Not Raising exception)
  * Proposal: To deprecate.

All of the above policies are proposed to deprecate with deprecation period
of one cycle.


Alternatives
------------

Leave the policies and keep doing the multiple policies enforcement in single
API.

Data model impact
-----------------

None

REST API impact
---------------

Below mentioned policies will be deprecated and removed in next cycle.
After removal, those policies will not control the extended attribute
and those attributes will be added always without checking of these
specific policy. Main policy for these API are still valid
and enforced.

Main policy here is the existing policies for Show, Detail APIs
if there is any.
For example:
GET servers/{server_id} - "os_compute_api:servers:show"
GET servers/detail - "os_compute_api:servers:detail"
POST flavors - 'os_compute_api:os-flavor-manage:create'

GET flavors, there is no policy on Show, Detail APIs.
GET images, there is no policy on Show, Detail APIs.

Show & List detail server::

    GET /servers/{server_id}
    GET /servers/detail

    Policies to be deprecated:
    'os_compute_api:os-config-drive'
    'os_compute_api:os-extended-availability-zone'
    'os_compute_api:os-extended-status'
    'os_compute_api:os-extended-volumes'
    'os_compute_api:os-keypairs'
    'os_compute_api:os-security-groups'
    'os_compute_api:os-server-usage'

Create, Show & List detail flavor::

    POST /flavors
    GET /flavors/{flavor_id}
    GET /flavors/detail

    Policies to be deprecated:
    'os_compute_api:os-flavor-rxtx'
    'os_compute_api:os-flavor-access'

Show & List detail image::

    GET /images/{image_id}
    GET /images/detail

    Policies to be deprecated:
    'os_compute_api:image-size'

No change in success cases of APIs as all of those policies
are enforced softly and does not raise exception if fail.

Security impact
---------------

Cloud provider who overridden the above mentioned policies will be impacted by
the policies deprecation and then removal in their respective APIs.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

Policies controlling extended attributes will not control
their addition in response.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    Ghanshyam Mann <ghanshyammann@gmail.com>

Work Items
----------

* Deprecate the respective policies in queens cycle.
* Remove the deprecated policies in Next(Rocky) cycle.

Dependencies
============

Oslo Policy Deprecation BP:
https://blueprints.launchpad.net/oslo.policy/+spec/policy-deprecation

Testing
=======

The corresponding unittest and functional test will be modified.

Documentation Impact
====================

None

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - Introduced
