..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================================
Support for tracking traits removed from provider.yaml
======================================================

https://blueprints.launchpad.net/nova/+spec/copy-applied-provider-yaml

This specification proposes a feature to ensure that traits removed from the
provider.yaml are also properly deleted from the resource provider.

Problem description
===================

Nova-compute has a feature to register custom traits with the resource provider
using config files (provider.yaml).
https://docs.openstack.org/nova/latest/admin/managing-resource-providers.html

In this configuration file, even if the values of custom traits are modified or
the trait is deleted, the original trait does not be removed from the target
resource provider.
In scenarios where the custom trait registered with the resource provider is
replaced and old custom traits affect scheduling, this behavior can be a
problem.

Use Cases
---------

- As a cloud operator, I would like to ensure that only one trait is registered
  with the resource provider for custom traits of the same type.

- As a cloud operator, I would like to complete the registration of custom
  traits in the config file of nova-compute without additional implementation
  (calling the Placement API using API/CLI in another system).

Proposed change
===============

We propose adding a process for nova-compute to copy the contents of the
provider.yaml file to ``/var/lib/nova/applied_provider.yaml`` after they have
been applied to the placement.

Then, when updating the placement based on the provider.yaml file, nova-compute
perform a diff between ``/var/lib/nova/applied_provider.yaml`` and
``/etc/nova/provider.yaml`` to detect if any traits have been removed from the
provider.yaml file.

For now, the diff is limited to traits, but later this logic can be extended to
allow the use of the diff for any part of the provider.yaml.

Alternatives
------------

- Register only the custom traits defined in the file with the resource
  provider, treating provider.yaml as declarative data. However, this is a
  destructive change and there are concerns about the impact on the existing
  environment.

- Add a definition like ``declarative_prefix`` to provider.yaml to handle only
  traits with a ``declarative_prefix`` declaratively. In this case, the
  extensibility to non-trait elements in provider.yaml is limited, and both the
  definition in provider.yaml and the code of the resource tracker become
  complex.

Data model impact
-----------------

None

REST API impact
---------------

None

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

No performance impact on nova is anticipated. If there are frequent updates to
custom traits, requests for deleting and creating traits will be frequently
sent to the Placement API.

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
  mkuroha

Other contributors:
  None

Feature Liaison
---------------

Feature liaison:
  Liaison Needed

Work Items
----------

* Implement the copying of provider.yaml and extraction of trait diffs with
  applied_provider.yaml in the ``_merge_provider_configs`` method.

Dependencies
============

None

Testing
=======

- Add unit/functional tests

Documentation Impact
====================

Update the existing `Managing Resource Providers Using Config Files <https://
docs.openstack.org/nova/latest/admin/managing-resource-providers.html>`_ guide
to explation the behavior with applied_provider.yaml.

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2025.2 Flamingo
     - Approved
   * - 2026.1 Flamingo
     - Reproposed
