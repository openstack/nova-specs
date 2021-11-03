..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Update userdata
==========================================

https://blueprints.launchpad.net/nova/+spec/update-userdata

It should be possible to update an instance's user data without
the need to rebuild the corresponding instance.

Problem description
===================

Currently, it is not possible to update an instance's user data without
rebuilding it.

Rebuilding takes much more time than just propagating updated user data,
e. g. via cloud-init, and may be unfavorable in production.
Editing a few lines in a cloud config file should not lead to a whole
rebuild of an instance.

Additionally, other public cloud providers like Azure [1] have the
functionality to update user data for an existing instance, so
end users may expect this to work in Nova as well.

AWS requires the instance to be powered off [2] before updating user data
and Google also allows updates at any time [3][4].

| [1] https://docs.microsoft.com/en-us/azure/virtual-machines/user-data#what-is-user-data
| [2] https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/user-data.html#user-data-view-change
| [3] https://cloud.google.com/container-optimized-os/docs/how-to/create-configure-instance#using_cloud-init_with_the_cloud_config_format
| [4] https://cloud.google.com/compute/docs/reference/rest/v1/instances/setMetadata

Use Cases
---------

As a user, I want to dynamically reconfigure the time and name servers used
by my instance via user data in order to update theses settings using the
same interface (user data) I initially used to bootstrap the instance.

As a user with experience at provisioning ephemeral workloads with tools like
cloud-init, I would like to manage my stateful workload via user data and
metadata on each boot. Metadata is used to store my external configuration
while user data is used to perform operations like rejoining a cluster when the
update has been applied.

Proposed change
===============

The existing ``PUT /servers/{server_id}`` API should accept an additional
parameter named ``user_data`` to allow updates to the instance's user data.

If the parameter is set in the request body, Nova should update the instance's
user data to the value set in the request parameter (if the input is valid,
i. e. not longer than 65535 bytes).

In case the instance uses a config drive, the above method should not be
allowed and rejected with a clear response message and 409 (conflict) status
code. Instead, the user data can be updated via a hard reboot, i. e. via the
``POST /servers/{server_id}/action`` API, with an additional parameter similar
to the above method. The config drive will be rebuilt automatically on a hard
reboot, containing the updated user data.

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

The ``PUT /servers/{server_id}`` API is extended by the
``user_data`` parameter. This is added in a new microversion.
The ``POST /servers/{server_id}/action`` API is updated accordingly.

* PUT /servers/{server_id}

  .. code-block:: json

    {
        "server": {
            "user_data": "data"
        }
    }

* POST /servers/{server_id}/action

  .. code-block:: json

    {
        "reboot": {
            "type": "HARD",
            "user_data": "data"
        }
    }

The above is an example of a minimal request which changes the user data
to ``data``.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

The option to update user data with openstackclient is required:
``openstack server set --user-data {data} {server_id}``

An option to update user data on a hard reboot should be added as well.

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
  jhartkopf

Feature Liaison
---------------

Liaison Needed

Work Items
----------

* Implement API changes
* Add tests
* Add docs

Dependencies
============

* openstackclient needs to be updated to implement this change

Testing
=======

* Add unit tests (positive and negative)
* Add functional test (API samples)

Documentation Impact
====================

The API reference needs to be updated to reflect the new microversion's
feature.

In addition, make clear that user data is mutable but also that it does not
replace proper config management.

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Yoga
     - Introduced
   * - Zed
     - Reproposed
