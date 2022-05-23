..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================
Allow unshelve to a specific host
=================================

https://blueprints.launchpad.net/nova/+spec/unshelve-to-host

This blueprint proposes to allow administrator to specify ``host``
to unshelve a shelved offloaded server.

Problem description
===================
Currently, an instance can only be unshelved to a specific availability zone.
The proposal is to extend the unshelve behavior allowing an instance to be
unshelved to a specific host.

Use Cases
---------
As a PROJECT_ADMIN, I want to specify a destination host when executing
unshelve on a shelved-offloaded instance.

Proposed change
===============
Add a new microversion to extend the unshelve API behavior to support a
specific destination host.

Add ``host`` attribute to POST /server/uuid/action for unshelve request body.

Add 2 checks:

- Ensure the user is a PROJECT_ADMIN.
- Ensure the instance state is ``shelved_offloaded``.

With the introduction of the new microversion, change the scheduling and
request specification (reqspec) behaviors of the unshelve API.

Current behavior:

+----------+------------------------+----------------------------------------+
| Boot     | Unshelve after offload | Result                                 |
+==========+========================+========================================+
| No AZ    | No AZ                  | Free scheduling, reqspec.AZ kept None  |
+----------+------------------------+----------------------------------------+
| No AZ    | AZ                     | Schedule in the AZ, update reqspec.AZ  |
|          |                        | to the requested one                   |
+----------+------------------------+----------------------------------------+
| With AZ  | No AZ                  | Schedule in original AZ, keep reqspec  |
|          |                        | pointing that AZ                       |
+----------+------------------------+----------------------------------------+
| With AZ  | AZ                     | Schedule to the new AZ, update the     |
|          |                        | reqspec.AZ to the new AZ               |
+----------+------------------------+----------------------------------------+

Proposed new behavior:

+----------+---------------------------+-------+-----------------------------+
| Boot     | Unshelve after offload AZ | Host  | Result                      |
+==========+===========================+=======+=============================+
|  No AZ   | No AZ or AZ=null          | No    | Free scheduling,            |
|          |                           |       | reqspec.AZ=None             |
+----------+---------------------------+-------+-----------------------------+
|  No AZ   | No AZ or AZ=null          | Host1 | Schedule to host1,          |
|          |                           |       | reqspec.AZ=None             |
+----------+---------------------------+-------+-----------------------------+
|  No AZ   | AZ="AZ1"                  | No    | Schedule to AZ1,            |
|          |                           |       | reqspec.AZ="AZ1"            |
+----------+---------------------------+-------+-----------------------------+
|  No AZ   | AZ="AZ1"                  | Host1 | Verify that host1 in AZ1,   |
|          |                           |       | or (3). Schedule to         |
|          |                           |       | host1, reqspec.AZ="AZ1"     |
+----------+---------------------------+-------+-----------------------------+
|  AZ1     | No AZ                     | No    | Schedule to AZ1,            |
|          |                           |       | reqspec.AZ="AZ1"            |
+----------+---------------------------+-------+-----------------------------+
|  AZ1     | AZ=null                   | No    | Free scheduling,            |
|          |                           |       | reqspec.AZ=None             |
+----------+---------------------------+-------+-----------------------------+
|  AZ1     | No AZ                     | Host1 | If host1 is in AZ1,         |
|          |                           |       | then schedule to host1,     |
|          |                           |       | reqspec.AZ="AZ1", otherwise |
|          |                           |       | reject the request (1)      |
+----------+---------------------------+-------+-----------------------------+
|  AZ1     | AZ=null                   | Host1 | Schedule to host1,          |
|          |                           |       | reqspec.AZ=None             |
+----------+---------------------------+-------+-----------------------------+
|  AZ1     | AZ="AZ2"                  | No    | Schedule to AZ2,            |
|          |                           |       | reqspec.AZ="AZ2"            |
+----------+---------------------------+-------+-----------------------------+
|  AZ1     | AZ="AZ2"                  | Host1 | If host1 in AZ2 then        |
|          |                           |       | schedule to host1,          |
|          |                           |       | reqspec.AZ="AZ2",           |
|          |                           |       | otherwise reject (1)        |
+----------+---------------------------+-------+-----------------------------+

(1) Check at the api and return an error.

Alternatives
------------
The current proposal rejects unshelve to a specific host if the instance state
is not shelved_offloaded.
Alternatively, a request to unshelve to a specific host would change the
instance state to shelved_offloaded automatically. So the user would not have
to worry about the initial instance state.

Data model impact
-----------------
None

REST API impact
---------------

Change the validation schema allowing ``availability_zone=null`` and
``host``.
An error in schema validation will raise a HTTP400.

Ensure the instance state is ``shelved_offloaded``.
An error in such case will rise a HTTP409.

Starting from the new API microversion, the
POST ``/servers/{server_id}/action``
API can be called with the following body:

- {"unshelve": null}   (Keep compatibility with previous microversions)

or

- {"unshelve": {"availability_zone": <string>}}
- {"unshelve": {"availability_zone": null}}   (Unpin availability zone)
- {"unshelve": {"host": <fqdn>}}
- {"unshelve": {"availability_zone": <string>, "host": <fqdn>}}
- {"unshelve": {"availability_zone": null, "host": <fqdn>}}


Everything else is not allowed, examples:

- {"unshelve": {}}
- {"unshelve": {"host": <fqdn>, "host": <fqdn>}}
- {"unshelve": {"foo": <string>}}

Security impact
---------------
None

Notifications impact
--------------------
None

Other end user impact
---------------------
The ``python-openstackclient`` will be updated and will provide support for
the new microversion.

A new switch ``--unpin-az`` will be introduced to the unshelve command allowing
PROJECT_ADMIN to remove the availability zone constraint of a server.

The ``python-novaclient`` will just be extended with the python helper
functions.


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
  Uggla (rene.ribaud)

Feature Liaison
---------------
Feature liaison:
  sbauza

Work Items
----------
* Add a new microversion to the unshelve to a specific host
  (unshelve Action) API
* Add related tests

Dependencies
============
None

Testing
=======
- Add related unit tests
- Add related functional tests
- Add a tempest test

Documentation Impact
====================
The API reference and the unshelve documentation will be updated to explain
the new behavior introduced by the new microversion.

References
==========
None

History
=======
.. list-table:: Revisions
    :header-rows: 1

    * - Release Name
      - Description
    * - Zed
      - Introduced
