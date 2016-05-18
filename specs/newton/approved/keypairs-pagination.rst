..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================
Keypairs pagination support
===========================

https://blueprints.launchpad.net/nova/+spec/keypairs-pagination

The blueprint aims to add `limit` and `marker` optional parameters
to GET /os-keypairs request.

Problem description
===================

Right now user can only get all non-deleted key pairs, which can be too slow.
Compute API user wants to be able to get only a subset of all tenant key pairs
using pagination mechanism.

Use Cases
---------

The scale testing of Horizon faced several problems with a lot of data being
received from Nova side. The change can be useful for showing key pairs in
Horizon on several pages instead of one general list.

Proposed change
===============

Add an API microversion that allows to get several key pairs using
general pagination mechanism with the help of `limit` and `marker`
optional parameters to GET /os-keypairs request. Also, update the
'key_pair_get_all_by_user' DP API function to order_by key pairs by user_id
to have the server-side sorting for paging to work.

* **marker**: The last key pair NAME of the previous page. Displays list of key
  pairs after "marker".

* **limit**: Maximum number of key pairs to display. If limit is None,
  all key pairs will be displayed. If limit is bigger than `osapi_max_limit`
  option of Nova API, limit `osapi_max_limit` will be used instead.

.. note:: This does not add support for an admin user to list all tenant
          key pairs.

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

The proposal would add API microversion for getting several key pairs using
general pagination mechanism. New optional parameters `limit` and `marker`
will be added to GET /os-keypairs request. API will return HTTP 404
if the `marker` is not found.

Generic request format ::

    GET /os-keypairs?limit={limit}&marker={kp_name}

1) Get all key pairs ::

    GET /os-keypairs

   Response ::

    {
        "keypairs": [
            {
                "keypair": {
                    "public_key": <ssh-key1>,
                    "name":"kp1",
                    "fingerprint": "cc:cc:cc:cc"
                }
            },
            {
                "keypair": {
                    "public_key": <ssh-key2>,
                    "name":"kp2",
                    "fingerprint": "aa:aa:aa:aa"
                }
            },
            {
                "keypair": {
                    "public_key": <ssh-key3>,
                    "name":"kp3",
                    "fingerprint": "bb:bb:bb:bb"
                }
            }
        ]
    }

2) Get no more than 2 key pairs ::

    GET /os-keypairs?limit=2

   Response ::

    {
        "keypairs": [
            {
                "keypair": {
                    "public_key": <ssh-key1>,
                    "name":"kp1",
                    "fingerprint": "cc:cc:cc:cc"
                }
            },
            {
                "keypair": {
                    "public_key": <ssh-key2>,
                    "name":"kp2",
                    "fingerprint": "aa:aa:aa:aa"
                }
            }
        ]
    }

3) Get all key pairs after kp2 ::

    GET /os-keypairs?marker=kp2

   Response ::

    {
        "keypairs": [
            {
                "keypair": {
                    "public_key": <ssh-key3>,
                    "name":"kp3",
                    "fingerprint": "bb:bb:bb:bb"
                }
            }
        ]
    }

4) Get no more than 1 key pair from kp1 ::

    GET /os-keypairs?marker=kp1&limit=1

   Response ::

    {
        "keypairs": [
            {
                "keypair": {
                    "public_key": <ssh-key2>,
                    "name":"kp2",
                    "fingerprint": "aa:aa:aa:aa"
                }
            }
        ]
    }

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

Reduce load on Horizon with the help of pagination of retrieving key pairs from
Nova side.

Other deployer impact
---------------------

None

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  pkholkin

Work Items
----------

Create a new API microversion for getting several key pairs using general
pagination mechanism.

Dependencies
============

None

Testing
=======

Would need new Tempest, functional and unit tests.

Documentation Impact
====================

Docs needed for new API microversion and usage.

References
==========

Nova bug describes the problem:

[1] https://bugs.launchpad.net/nova/+bug/1510504

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced
   * - Newton
     - Re-proposed
