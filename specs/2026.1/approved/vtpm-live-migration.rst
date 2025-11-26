..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================
vTPM live migration
===================

https://blueprints.launchpad.net/nova/+spec/vtpm-live-migration

When Nova first added vTPM support, all non-spawn operations were `rejected
<https://review.opendev.org/c/openstack/nova/+/741500>`_ at the API level.
Extra work was necessary to manage the vTPM state when moving an instance. This
work was eventually completed for resize and cold migration, and those
operations were `unblocked <https://review.opendev.org/c/openstack/nova/+/639934/52>`_.
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
:ref:`vtpm-live-migration-2026.1-problem-description`), but Nova changes are
necessary before being able to remove the API block. This spec describes those
changes.

.. _vtpm-live-migration-2026.1-problem-description:

Problem description
===================

There are four aspects to vTPM live migration: shared vs non-shared vTPM state
storage, Libvirt support, and secret management. There is also an adjacent
problem, that - while not related to live migration - can be resolved by the
changes necessary to support live migration: vTPM instances cannot be started
back up by Nova after a compute host reboot.

vTPM state storage
------------------

vTPM state storage is not the same as instance state storage and Libvirt
supports the use of local storage and shared storage such as NFS, for both.

Libvirt can be told where to store the vTPM state via the `source
<https://libvirt.org/formatdomain.html#tpm-device>`_ XML element, which Nova
`does not support
<https://opendev.org/openstack/nova/src/commit/c79bec0f2257967da1dcccc9f562253d6ede535d/nova/virt/libvirt/config.py#L1146-L1153>`_.
Nova deployments use the Libvirt default vTPM state path. On both Ubuntu and
Red Hat operating systems, this path is ``/var/lib/libvirt/swtpm/<instance
UUID>``. This path is distinct from the instance state path.

Testing will generally focus on local storage and could be expanded to shared
storage like NFS in the future. Currently the Nova CI gate does not have any
jobs that are configured with NFS.

Libvirt support
---------------

Though it was impossible to find Libvirt artifacts explicitly demonstrating
vTPM live migration support for non-shared vTPM state storage, as of `version
8.10 <https://www.libvirt.org/news.html#v8-10-0-2022-12-01>`_, vTPM live
migration with shared vTPM storage is supported, and `this comment
<https://github.com/stefanberger/swtpm/issues/525#issuecomment-914542936>`_
suggests that for non-shared storage, vTPM live migration has been supported
since version 7.1.0.

Therefore, this spec requires Libvirt 7.1.0. Our current minimum Libvirt
version is 8.0.0 as of 2025.1 (Epoxy), so we will not need to do any minimum
version checks while implementing this feature.

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

.. list-table:: ``tpm_secret_security`` values
   :header-rows: 1

   * - Value
     - Mechanism
     - Security implications
     - Instance mobility
   * - ``user``
     - Only the instance owner has access to the Barbican secret. This is
       existing behavior and will be the default behavior.
     - This is the most secure option, as even the Nova service user and root
       on the compute host cannot read the secret.
     - The instance is immovable and cannot be restarted by Nova in the event
       of a compute host crash or reboot.
   * - ``host``
     - The Libvirt secret is persistent and retrievable.
     - This is "medium" security. API-level admins and the Nova service user do
       not have access to the secret, but it can be accessed by users with
       sufficient privileges on the compute host.
     - The instance can be live migrated because Nova can read the secret back
       from Libvirt on the source host and send it to the destination over RPC.
       Security over the wire is left as the operator's responsibility, but TLS
       or similar is assumed. The instance can also be restarted by Nova in the
       event of a compute host crash or reboot for the exact same reason.
   * - ``deployment``
     - The Nova service user owns the Barbican secret.
     - This is the least secure but most flexible option.
     - The instance can be live migrated because Nova can download the secret
       from Barbican and define it in Libvirt on the destination host. The
       instance can also be restarted by Nova in the event of a compute host
       crash or reboot for the exact same reason.

Users are able to choose what level they require on their instance by selecting
a flavor that sets the new ``hw:tpm_secret_security`` flavor extra spec.  If no
specific policy was indicated in the flavor extra spec, the instance will
default to the ``user`` policy, which is the same as legacy behavior.

For simplicity, if ``hw:tpm_secret_security`` is not set in the flavor extra
specs, an instance with vTPM will default to the ``user`` TPM secret security
policy.

A new image property is intentionally not provided because server rebuild is
blocked in the API. If a user were to create a server with a given TPM secret
security policy via an image property, that policy would become locked-in and
unable to be changed. The user would not be able to change the image property
because they would not be able to rebuild, and they would not be able to resize
to a different TPM secret security policy because the image property and flavor
extra spec would conflict and fail with HTTP 409.

Operators are able to specify what level they support by using the new
``[libvirt]supported_tpm_secret_security`` config option. This is a
per compute host list option that can take the value of one or more of the
security levels from the previous table. Its default value is all three levels.
These values are exposed as driver capability traits. The
``hw:tpm_secret_security`` flavor extra spec is translated to a required trait
to match the driver capabilities.

The behavior of an instance during live migration is defined by its persisted
embedded flavor ``hw:tpm_secret_security`` extra spec. Instances with ``user``
cannot be live migrated. For instances with ``host``, the source compute host
reads the secret from Libvirt and sends it over RPC to the destination. For
instances with ``deployment``, the destination host downloads the secret from
Barbican and defines it in Libvirt. Because the instance's
``hw:tpm_secret_security`` value translates to a required trait, it's
guaranteed that the destination host chosen for live migration supports
whatever behavior the instance requires.

Alternatives
------------

This is the only version of this spec that covers the essentials: users of new
instances can choose the security level that they require, and operators can
choose which security levels they are willing to support given the limitations
imposed by higher security levels.

We could also provide an image property for selection of the TPM secret
security policy but it would be problematic because of the current inability to
rebuild instances with vTPM (it is blocked in the API). Without the ability to
rebuild a vTPM instance, any user who chose their policy via image property
would be locked in to that policy unable to change it. They would not be able
to change the image property value because they cannot rebuild and they would
also not be able to change the policy via flavor extra spec because that would
fail due to conflicting values between image property vs flavor extra spec.

If we would like to support image property in the future, we could possibly do
it if we could add the ability to rebuild vTPM instances at the same time. It
is not yet known if there are any technical limitations that prevent the
possibility of implementing rebuild, but we could certainly investigate.

Data model impact
-----------------

None.

REST API impact
---------------

No new microversion. The flavor extra spec validation code is updated to allow
``hw:tpm_secret_security``.

Security impact
---------------

The main security consequences of this spec are the implications of the
``host`` and ``deployment`` values of ``hw:tpm_secret_security``.

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

A compute service version bump is necessary.

Live migration of instances with vTPM will be blocked until the minimum
service version of the deployment is the upgraded version. The cloud must be
fully upgraded.

Deployers must create flavor(s) with the ``hw:tpm_secret_security`` extra spec
set to ``host`` or ``deployment`` in order to enable creation of instances with
the respective TPM secret security policies.

Any instances without this set are pre-existing instances and for simplicity,
they will not be migrated. If a user would like to opt-in to live migration,
they can resize their pre-existing instance to a flavor that has the
``hw:tpm_secret_security`` extra spec set to ``host`` or ``deployment``.

Automatic migration of pre-existing instances into TPM secret security
policies could be discussed and considered as future work.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  notartom, melwitt

Feature Liaison
---------------

Feature liaison:
  melwitt, dansmith

Work Items
----------

* Introduce the ``hw:tpm_secret_security`` flavor extra spec, and
  ``[libvirt]supported_tpm_secret_security`` config option
* Add ``vtpm_secret_uuid`` and ``vtpm_secret_value`` fields to the
  ``LibvirtLiveMigrateData`` object to carry the data over RPC from the
  source host to the destination host in the case of the ``host`` TPM secret
  security policy
* Modify the pre live migration and rollback code to handle secret definition
  and cleanup
* Modify the resize code to handle TPM secret security policy conversions
  including absence of TPM secret security policy for pre-existing instances
* Bump the service version
* Modify the existing API block to only allow live migration of ``host`` or
  ``deployment`` instances once the minimum service version has reached the
  bumped version
* Add a whitebox/integration test
* Add regular Tempest tests if possible
* Update the documentation

Dependencies
============

* Libvirt version 7.1.0. This can be enforced dynamically in code.

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
``supported_tpm_secret_security`` configuration option, as well as the
implications of all possible values. The expectation that vTPM state storage is
not shared and that shared vTPM state storage live migration is untested is
made explicit.

References
==========

Empty.

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2026.1 Gazpacho
     - Re-proposed
   * - 2025.2 Flamingo
     - Re-proposed
   * - 2025.1 Epoxy
     - Introduced
