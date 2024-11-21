..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================
vTPM live migration
===================

https://blueprints.launchpad.net/nova/+spec/vtpm-live-migration

When Nova first added vTPM support, all non-spawn operations were `rejected
<https://review.opendev.org/c/openstack/nova/+/741500>`_ at the API level. Extra
work was necessary to manage the vTPM state when moving an instance. This work
was eventually completed for resize and cold migration, and those operations
were `unblocked <https://review.opendev.org/c/openstack/nova/+/639934/52>`_.
The blocks on live migration, evacuation, shelving and rescue are `still in
place
<https://docs.openstack.org/nova/2024.2/admin/emulated-tpm.html#limitations>`_.

A TPM device is `required for certain features
<https://learn.microsoft.com/en-us/windows-server/get-started/hardware-requirements>`_
of Windows Server 2022 and 2025, notably BitLocker Drive Encryption. It's also
required to run `Windows 11 at all
<https://www.microsoft.com/en-us/windows/windows-11-specifications>`_. The
inability to live migrate instances with vTPM is a major roadblock for anyone
operating Windows guests in an OpenStack cloud.

Libvirt support for vTPM live migration now exists (more details in
:ref:`problem-description`), but Nova changes are necessary before being able
to remove the API block. This spec describes those changes.

.. _problem-description:

Problem description
===================

There are four aspects to vTPM live migration: shared vs non-shared vTPM state
storage, Libvirt support, and secret management. There is also an adjacent
problem, that - while not related to live migration - can be resolved by the
changes necessary to support live migration: vTPM instances cannot be started
back up by Nova after a compute host reboot.

vTPM state storage
------------------

vTPM state storage is not the same as instance state storage. The latter can be
configued to be shared, for example on NFS. The former is always non-shared.
Libvirt can be told where to store the vTPM state via the `source
<https://libvirt.org/formatdomain.html#tpm-device>`_ XML element, which Nova
`does not support
<https://opendev.org/openstack/nova/src/commit/c79bec0f2257967da1dcccc9f562253d6ede535d/nova/virt/libvirt/config.py#L1146-L1153>`_.
Nova deployments use the Libvirt default vTPM state path. On both Ubuntu and
Red Hat operating systems, this path is ``/var/lib/libvirt/swtpm/<instance
UUID>``. This path is distinct from the instance state path and can be expected
to never be on shared storage.

Thus, this spec requires vTPM state storage to be not shared, and declares live
migration with shared vTPM state storage to be untested. This will be
documented.

Libvirt support
---------------

Though it was impossible to find Libvirt artifacts explicitly demonstrating
vTPM live migration support for non-shared vTPM state storage, as of `version
8.10 <https://www.libvirt.org/news.html#v8-10-0-2022-12-01>`_, vTPM live
migration with shared vTPM storage is supported, and `this comment
<https://github.com/stefanberger/swtpm/issues/525#issuecomment-914542936>`_
suggests that for non-shared storage, vTPM live migration has been supported
since version 7.1.0.

Therefore, this spec requires Libvirt 7.1.0.

Secret management
-----------------

When creating an instance with vTPM, Nova asks a key manager - normally
Barbican - to generate a secret. Crucially, this is done with the user's token,
and the created secret is owned by the user, with no one else - not even admin
or the Nova service user - being able to read it. Nova then `defines the secret
in Libvirt <https://libvirt.org/formatsecret.html>`_, and in the instance XML
references the secret by its UUID. This tells Libvirt to encrypt the instance's
vTPM state using the contents of that secret as the symmetric key. Nova
`undefines the secret
<https://opendev.org/openstack/nova/src/commit/c79bec0f2257967da1dcccc9f562253d6ede535d/nova/virt/libvirt/driver.py#L8077>`_
once the Libvirt domain spawns successfully.

For vTPM live migration to work, a Libvirt secret with the same UUID and
contents needs to be defined on the destination host so that destination
Libvirt can decrypt the vTPM state. Currently, Nova has no way of doing this.
Live migration is an admin operation, and neither admin nor the Nova service
user have access to the Barbican secret (unless the admin happens to be the
owen of the instance, but that's an edge case). The Libvirt secret cannot be
read back on the source host either, because it's defined as `private
<https://opendev.org/openstack/nova/src/commit/c79bec0f2257967da1dcccc9f562253d6ede535d/nova/virt/libvirt/host.py#L1115-L1116>`_
and is undefined once the domain spawns.

Compute host reboot
-------------------

For the exact same reasons (lack of Barbican secret access and inability to
read the Libvirt secret back from Libvirt), Nova cannot start back up vTPM
instances after a compute host reboot.

Use Cases
---------

As a cloud operator, I want to be able to live migrate instances with vTPM
devices, in particular Windows instances.

As a cloud user, I want to keep the contents of my instance's vTPM private.
The cloud system should only be able to decrypt it when I request it via my
user token and the system should only keep the decryption secret around for a
limited time. I as a user am willing to accept that such privacy requirements
limit some of the admin initiated lifecycle operations on my instance.

As a cloud operator, I want vTPM instances on a compute host to start back up
again after a host reboot.

Proposed change
===============

Because the security of the vTPM secret (either in Barbican or in Libvirt)
affects what operations can be performed on an instance, users should be able
to specify what level of security they require, and operators need to specify
what level of security they're willing to support. There also needs to be a
default level applied to an instance if nothing is explicitly specified.

Three possible security levels are proposed. They are presented in the table
below.

.. list-table:: ``vtpm_secret_security`` values
   :header-rows: 1

   * - Value
     - Mechanism
     - Security implications
     - Instance mobility
   * - ``user``
     - Only the instance owner has access to the Barbican secret. This is existing
       behavior.
     - This is the most secure option, as even the Nova service user and root on
       the compute host cannot read the secret.
     - The instance is immovable and cannot be restarted by Nova in the event of a
       compute host crash or reboot.
   * - ``host``
     - The Libvirt secret is persistent and retrievable.
     - This is "medium" security. API-level admins and the Nova service user do
       not have access to the secret, but it can be accessed by users with
       sufficient privileges on the compute host.
     - The instance can be live migrated because Nova can read the secret back
       from Libvirt on the source host and send it to the destination over RPC.
       Security over the wire is left as the operator's responsibility, but TLS or
       similar is assumed. The instance can also be restarted by Nova in the event
       of a compute host crash or reboot for the exact same reason.
   * - ``deployment``
     - The Nova service user owns the Barbican secret.
     - This is the least secure but most flexible option.
     - The instance can be live migrated because Nova can download the secret from
       Barbican and define it in Libvirt on the destination host. The instance can
       also be restarted by Nova in the event of a compute host crash or reboot
       for the exact same reason.

Users are able to chose what level they require on their instance by setting
the new ``hw_vtpm_secret_security`` image property. If this property is not
set, a default can be obtained from the new ``hw:vtpm_secret_security`` flavor
extra spec. For operators that do not want to deal with flavor explosion as a
consequence of this new extra spec, a new host configuration option is added as
a fallback. Called ``[compute]vtpm_secret_security`` with a default value of
``host``, an instance with no image property or flavor extra spec will have its
host's ``vtpm_secret_security`` policy persisted in its ``system_metadata``
upon booting on that host.

Operators ae able to specify what level they support by using the new
``[compute]supported_vtpm_secret_security`` config option. This is a
per compute host list option that can take the value of one or more of the
security levels from the previous table. Its default value is all three levels.
These values are exposed as driver capability traits. The
``hw_vtpm_secret_Security`` image property and flavor extra spec are translated
to required traits to match the driver capabilities.

The behavior of an instance during live migratioon is defined by its persisted
``hw_vtpm_secret_security`` (either explicitly set by the user, or added by
default by Nova from the host's config option). Instances with ``user`` cannot
be live migrated. For instances with ``host``, the source compute host reads
the secret from Libvirt and sends it over RPC to the destination. For instances
with ``deployment``, the destination host downloads the secret from Barbican
and defines it in Libvirt. Because the instance's ``hw_vtpm_secret_security``
value translates to a required trait, it's guaranteed that the destination host
chosen for live migration supports whatever behavior the instance requires.

Alternatives
------------

This is the only version of this spec that covers the essentials: users with
existing instances are informed of the vTPM secret security level set on their
instances by the operator, users of new instances can chose the security level
that they require, and operators can chose which security levels they are
willing to support given the limitations imposed by higher security levels.

Data model impact
-----------------

The ``ImageMetaProps`` Nova object is updated to support the new
``hw_vtpm_secret_security`` image property. The database schema is unaffected.

REST API impact
---------------

No new microversion. The flavor extra spec validation code is updated to allow
``hw:vtpm_secret_security``.

Security impact
---------------

The main security consequences of this spec are the implications of the
``host`` and ``deployment`` values of ``vtpm_secret_security``.

In the ``host`` case, anyone with sufficient access to the compute host can
read vTPM secrets. While this is not great, it's also something the user opts
in to, and the compute host are assumed to be secured by the cloud operator.

In the ``deployment`` case, a compromise of the Nova service user leads to an
exposure of all vTPM secrets. Once again, this is something the user opts in
to, and the Nova service user is assumed to be secure.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Upgrade impact
--------------

A compute service version bump is necessary. When nova-compute starts up with
the new service version, it checks all instances currently on the host. Any
instances created after the service version bump have a value for
``hw_vtpm_secret_security`` set in their ``system_metadata``, either explicitly
by the user or implicitly by Nova as  a fallback default, as described in the
`<Proposed change_>_` section. Any instances without this set are pre-existing
instances, and need to be upgraded. They are upgraded to the value of the
``[compute]default_vtpm_secret_security`` value. Just persisting this in their
``system_metadata`` is not enough - their owner also needs to performa an
operation with their token on the instance so that Nova can either convert the
Libvirt secret to non-private and persistent in the case of ``host``, or create
a new Barbican secret with the same contents, but owned by the Nova service
user, in the case of ``deployment``. Operators have no choice but to
communicate this to their users, at which point users have a choice to either
opt in to the new security level, or refuse by not touching their instances or
deleting them outright. In order to see what secret security level has been set
on their instances by the operators, this spec depends on the `Image props in
server show <https://review.opendev.org/c/openstack/nova-specs/+/938910>`_
spec, which will allow users to see the embedded image properties set on their
instance, and determine the vTPM secret security level that way.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  notartom

Feature Liaison
---------------

Feature liaison:
  melwitt, dansmith

Work Items
----------

#. Introduce the ``hw_vtpm_secret_security``, ``hw:vtpm_secret_security``,
   ``[compute]vtpm_secret_security``, and
   ``[compute]default_vtpm_secret_security`` image properties, flavor extra
   specs, and config options.
#. Modify the pre live migration and rollback code to handle secret definition
   and cleanup.
#. Bump the service version.
#. Modify the existing API block to only allow live migration of ``host`` or
   ``deployment`` instances once the minimum service version has reached the
   bumped version.
#. Add a whitebox/integration test.
#. Update the documentation.

Dependencies
============

* Libivrt version 7.1.0. This can be enforced dynamically in code.

Testing
=======

Nova's functional tests are extended to test the Nova logic using the Libvirt
fixture. This is particularly useful for cases that cannot be easily tested in
a real environment, like rollback.

The existing `whitebox-tempest-plugin vTPM tests
<https://opendev.org/openstack/whitebox-tempest-plugin/src/commit/bee34dbb867dc3c107f1262f68a997ef7ccff55a/whitebox_tempest_plugin/api/compute/test_vtpm.py>`_
are extended to test live migration in a real environment with an actual
Libvirt.

Documentation Impact
====================

Nova's `vTPM documentation
<https://docs.openstack.org/nova/latest/admin/emulated-tpm.html>`_ is updated
to remove the live migration limitation and explain the usage of the
``vtpm_secret_security`` configuration option, as well as the implications of
all possible values. The expectation that vTPM state storage is not shared and
that shared vTPM state storage live migration is untested is made explicit.

References
==========

Empty.

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2025.1 Epoxy
     - Introduced
