..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================================
Add support for encrypted emulated virtual TPM
==============================================

https://blueprints.launchpad.net/nova/+spec/add-emulated-virtual-tpm

There are a class of applications which expect to use a TPM device to store
secrets. In order to run these applications in a virtual machine, it would be
useful to expose a virtual TPM device within the guest. Accordingly, the
suggestion is to add flavor/image properties which a) translate to placement
traits for scheduling and b) cause such a device to be added to the VM by the
relevant virt driver.

Problem description
===================

Currently there is no way to create virtual machines within nova that provide
a virtual TPM device to the guest.

Use Cases
---------

Support the virtualizing of existing applications and operating systems which
expect to make use of physical TPM devices. At least one hypervisor
(libvirt/qemu) currently supports the creation of an emulated TPM device which
is associated with a per-VM ``swtpm`` process on the host, but there is no way
to tell nova to enable it.

Proposed change
===============

In recent libvirt and qemu (and possibly other hypervisors as well) there is
support for an emulated vTPM device. We propose to modify nova to make use
of this capability.

This spec describes only the libvirt implementation.

XML
---

The desired libvirt XML arguments are something like this (`source
<https://libvirt.org/formatdomain.html#elementsTpm>`_)::

    ...
    <devices>
      <tpm model='tpm-tis'>
        <backend type='emulator' version='2.0'>
          <encryption secret='6dd3e4a5-1d76-44ce-961f-f119f5aad935'/>
        </backend>
      </tpm>
    </devices>
    ...

Prerequisites
-------------

Support for encrypted emulated TPM requires at least:

* libvirt version 5.6.0 or greater.
* qemu 2.11 at a minimum, though qemu 2.12 is recommended. The virt driver code
  should add suitable version checks (in the case of LibvirtDriver, this would
  include checks for both libvirt and qemu). Currently emulated TPM is only
  supported for x86, though this is an implementation detail rather than an
  architectural limitation.
* The ``swtpm`` binary and libraries on the host.
* Access to a castellan-compatible key manager, such as barbican, for storing
  the passphrase used to encrypt the virtual device's data. (The key manager
  implementation's public methods must be capable of consuming the user's auth
  token from the ``context`` parameter which is part of the interface.)
* Access to an object-store service, such as swift, for storing the file the
  host uses for the virtual device data during operations such as shelve.

Config
------

All of the following apply to the compute (not conductor/scheduler/API)
configs:

* A new config option will be introduced to act as a "master switch" enabling
  vTPM. This config option would apply to future drivers' implementations as
  well, but since this spec and current implementation are specific to libvirt,
  it is in the ``libvirt`` rather than the ``compute`` group::

     [libvirt]
     vtpm_enabled = $bool (default False)

* To enable move operations (anything involving rebuilding a vTPM on a new
  host), nova must be able to lay down the vTPM data with the correct ownership
  -- that of the ``swtpm`` process libvirt will create -- but we can't detect
  what that ownership will be. Thus we need a pair of config options on the
  compute indicating the user and group that should own vTPM data on that
  host::

     [libvirt]
     swtpm_user = $str (default 'tss')
     swtpm_group = $str (default 'tss')

* (Existing, known) options for ``[key_manager]``.

* New standard keystoneauth1 auth/session/adapter options for ``[swift]`` will
  be introduced.

Traits, Extra Specs, Image Meta
-------------------------------

In order to support this functionality we propose to:

* Use the existing ``COMPUTE_SECURITY_TPM_1_2`` and
  ``COMPUTE_SECURITY_TPM_2_0`` traits. These represent the two different
  versions of the TPM spec that are currently supported. (Note that 2.0 is not
  backward compatible with 1.2, so we can't just ignore 1.2. A summary of the
  differences between the two versions is currently available here_.) When all
  the Prerequisites_ have been met and the Config_ switch is on, the libvirt
  compute driver will set both of these traits on the compute node resource
  provider.
* Support the following new flavor extra_specs and their corresponding image
  metadata properties (which are simply ``s/:/_/`` of the below):

  * ``hw:tpm_version={1.2|2.0}``. This will be:

    * translated to the corresponding
      ``required=COMPUTE_SECURITY_TPM_{1_2|2_0}`` in the allocation candidate
      request to ensure the instance lands on a host capable of vTPM at the
      requested version
    * used by the libvirt compute driver to inject the appropriate guest XML_.

    .. note:: Whereas it would be possible to specify
          ``trait:COMPUTE_SECURITY_TPM_{1_2|2_0}=required`` directly in the
          flavor extra_specs or image metadata, this would only serve to
          land the instance on a capable host; it would not trigger the libvirt
          driver to create the virtual TPM device. Therefore, to avoid
          confusion, this will not be documented as a possibility.

  * ``hw:tpm_model={TIS|CRB}``. Indicates the emulated model to be used. If
    omitted, the default is ``TIS`` (this corresponds to the libvirt default).
    ``CRB`` is only compatible with TPM version 2.0; if ``CRB`` is requested
    with version 1.2, an error will be raised from the API.

To summarize, all and only the following combinations are supported, and are
mutually exclusive (none are inter-compatible):

* Version 1.2, Model TIS
* Version 2.0, Model TIS
* Version 2.0, Model CRB

Note that since the TPM is emulated (a process/file on the host), the
"inventory" is effectively unlimited. Thus there are no resource classes
associated with this feature.

If both the flavor and the image specify a TPM trait or device model and the
two values do not match, an exception will be raised from the API by the
flavor/image validator.

.. _here: https://en.wikipedia.org/wiki/Trusted_Platform_Module#TPM_1.2_vs_TPM_2.0

Instance Lifecycle Operations
-----------------------------

Descriptions below are libvirt driver-specific. However, it is left to the
implementation which pieces are performed by the compute manager vs. the
libvirt ComputeDriver itself.

.. note:: In deciding whether/how to support a given operation, we use "How
          does this work on baremetal" as a starting point. If we can support a
          VM operation without introducing inordinate complexity or user-facing
          weirdness, we do.

Spawn
~~~~~

#. Even though swift is not required for spawn, ensure a swift endpoint is
   present in the service catalog (and reachable? version discovery?
   implementation detail) so that a future unshelve doesn't break the instance.
#. Nova generates a random passphrase and stores it in the configured key
   manager, yielding a UUID, hereinafter referred to as ``$secret_uuid``.
#. Nova saves the ``$secret_uuid`` in the instance's ``system_metadata`` under
   key ``tpm_secret_uuid``.
#. Nova uses the ``virSecretDefineXML`` API to define a private (value can't be
   listed), ephemeral (state is stored only in memory, never on disk) secret
   whose ``name`` is the instance UUID, and whose UUID is the ``$secret_uuid``.
   The ``virSecretSetValue`` API is then used to set its value to the generated
   passphrase. We already provide a wrapper around this API at
   ``nova.virt.libvirt.host.Host.create_secret`` for use with encrypted volumes
   and will expand this to cover vTPM also.
#. Nova injects the XML_ into the instance's domain. The ``model`` and
   ``version`` are gleaned from the flavor/image properties, and the ``secret``
   is ``$secret_uuid``.
#. Once libvirt has created the guest, nova uses the ``virSecretUndefine`` API
   to delete the secret. The instance's emulated TPM continues to function.

.. note:: Spawning from an image created by snapshotting a VM with a vTPM will
          result in a fresh, empty vTPM, even if that snapshot was created by
          ``shelve``. By contrast, `spawn during unshelve`_ will restore such
          vTPM data.

Cold Boot
~~~~~~~~~

...and any other operation that starts the guest afresh. (Depending on the `key
manager`_ security model, these may be restricted to the instance owner.)

#. Pull the ``$secret_uuid`` from the ``tpm_secret_uuid`` of the instance's
   ``system_metadata``.
#. Retrieve the passphrase associated with ``$secret_uuid`` via the configured
   key manager API.

Then perform steps 4-6 as described under Spawn_.

Migrations and their ilk
~~~~~~~~~~~~~~~~~~~~~~~~

For the libvirt implementation, the emulated TPM data is stored in
``/var/lib/libvirt/swtpm/<instance>``. Certain lifecycle operations require
that directory to be copied verbatim to the "destination". For (cold/live)
migrations, only the user that nova-compute runs as is guaranteed to be able to
have SSH keys set up for passwordless access, and it's only guaranteed to be
able to copy files to the instance directory on the destination node. We
therefore propose the following procedure for relevant lifecycle operations:

* Copy the directory into the local instance directory, changing the ownership
  to match it.
* Perform the move, which will automatically carry the data along.
* Change ownership back and move the directory out to
  ``/var/lib/libvirt/swtpm/<instance>`` on the destination.
* On confirm/revert, delete the directory from the source/destination,
  respectively. (This is done automatically by libvirt when the guest is torn
  down.)
* On revert, the data directory must be restored (with proper permissions) on
  the source.

Since the expected ownership on the target may be different than on the source,
and is (we think) impossible to detect, the admin must inform us of it via the
new ``[libvirt]swtpm_user`` and ``[libvirt]swtpm_group`` Config_ options if
different from the default of ``tss``.

This should allow support of cold/live migration and resizes that don't change
the device.

.. todo:: Confirm that the above "manual" copying around is actually necessary
          for migration. It's unclear from reading
          https://github.com/qemu/qemu/blob/6a5d22083d50c76a3fdc0bffc6658f42b3b37981/docs/specs/tpm.txt#L324-L383

Resize can potentially add a vTPM to an instance that didn't have one before,
or remove the vTPM from an instance that did have one, and those should "just
work". When resizing from one version/model to a different one the data can't
and won't carry over (for same-host resize, we must *remove* the old backing
file). If both old and new flavors have the same model/version, we must ensure
we convey the virtual device data as described above (for same-host resize, we
must *preserve* the existing backing file).

Shelve (offload) and Unshelve
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Restoring vTPM data when unshelving a shelve-offloaded server requires the vTPM
data to be persisted somewhere. We can't put it with the image itself, as it's
data external to the instance disk. So we propose to put it in object-store
(swift) and maintain reference to the swift object in the instance's
``system_metadata``.

The shelve operation needs to:

#. Save the vTPM data directory to swift.
#. Save the swift object ID and digital signature (sha256) of the directory to
   the instance's ``system_metadata`` under the (new) ``tpm_object_id`` and
   ``tpm_object_sha256`` keys.
#. Create the appropriate ``hw_tpm_version`` and/or ``hw_tpm_model`` metadata
   properties on the image. (This is to close the gap where the vTPM on
   original VM was created at the behest of image, rather than flavor,
   properties. It ensures the proper scheduling on unshelve, and that the
   correct version/model is created on the target.)

The unshelve operation on a shelved (but not offloaded) instance should "just
work" (except for deleting the swift object; see below). The code path for
unshelving an offloaded instance needs to:

#. Ensure we land on a host capable of the necessary vTPM version and model
   (we get this for free via the common scheduling code paths, because we did
   step 3 during shelve).
#. Look for ``tpm_object_{id|sha256}`` and ``tpm_secret_uuid`` in the
   instance's ``system_metadata``.
#. Download the swift object. Validate its checksum and fail if it doesn't
   match.
#. Assign ownership of the data directory according to
   ``[libvirt]swtpm_{user|group}`` on the host.
#. Retrieve the secret and feed it to libvirt; and generate the appropriate
   domain XML (we get this for free via ``spawn()``).
#. Delete the object from swift, and the ``tpm_object_{id|sha256}`` from the
   instance ``system_metadata``. This step must be done from both code paths
   (i.e. whether the shelved instance was offloaded or not).

.. note:: There are a couple of ways a user can still "outsmart" our checks and
          make horrible things happen on unshelve. For example:

          * The flavor specifies no vTPM properties.
          * The *original* image specified version 2.0.
          * Between shelve and unshelve, edit the snapshot to specify version
            1.2.

          We will happily create a v1.2 vTPM and restore the (v2.0) data into
          it. The VM will (probably) boot just fine, but unpredictable things
          will happen when the vTPM is accessed.

          We can't prevent *all* stupidity.

.. note:: As mentioned in `Security impact`_, if shelve is performed by the
          admin, only the admin will be able to perform the corresponding
          unshelve operation. And depending on the `key manager`_ security
          model, if shelve is performed by the user, the admin may not be able
          to perform the corresponding unshelve operation.

Since the backing device data is virt driver-specific, it must be managed by
the virt driver; but we want the object-store interaction to be done by compute
manager. We therefore propose the following interplay between compute manager
and virt driver:

The ``ComputeDriver.snapshot()`` contract currently does not specify a return
value. It will be changed to allow returning a file-like with the (prepackaged)
backing device data. The libvirt driver implementation will open a ``tar`` pipe
and return that handle. The compute manager is responsible for reading from
that handle and pushing the contents into the swift object. (Implementation
detail: we only do the swift thing for snapshots during shelve, so a) the virt
driver should not produce the handle except when the VM is in
``SHELVE[_OFFLOADED]`` state; and/or the compute manager should explicitly
close the handle from other invocations of ``snapshot()``.)

.. _`spawn during unshelve`:

The compute driver touchpoint for unshelving an offloaded instance is
``spawn()``. This method will get a new kwarg which is a file-like. If not
``None``, virt driver implementations are responsible for streaming from that
handle and reversing whatever was done during ``snapshot()`` (in this case un-\
``tar``\ -ing). For the unshelve path for offloaded instances, the compute
manager will pull down the swift object and stream it to ``spawn()`` via this
kwarg.

createImage and createBackup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Because vTPM data is associated with the **instance**, not the **image**, the
``createImage`` and ``createBackup`` flows will not be changed. In particular,
they will not attempt to save the vTPM backing device to swift.

This, along with the fact that fresh Spawn_ will not attempt to restore vTPM
data (even if given an image created via ``shelve``)  also prevents "cloning"
of vTPMs.

This is analogous to the baremetal case, where spawning from an image/backup on
a "clean" system would get you a "clean" (or no) TPM.

Rebuild
~~~~~~~

Since the instance is staying on the same host, we have the ability to leave
the existing vTPM backing file intact. This is analogous to baremetal behavior,
where restoring a backup on an existing system will not touch the TPM (or any
other devices) so you get whatever's already there. However, it is also
possible to lock your instance out of its vTPM by rebuilding with a different
image, and/or one with different metadata. A certain amount of responsibility
is placed on the user to avoid scenarios like using the TPM to create a master
key and not saving that master key (in your rebuild image, or elsewhere).

That said, rebuild will cover the following scenarios:

* If there is no existing vTPM backing data, and the rebuild image asks for a
  vTPM, create a fresh one, just like Spawn_.
* If there is an existing vTPM and neither the flavor nor the image asks for
  one, delete it.
* If there is an existing vTPM and the flavor or image asks for one, leave the
  backing file alone. However, if different versions/models are requested by
  the old and new image in combination with the flavor, we will fail the
  rebuild.

Evacuate
~~~~~~~~

Because the vTPM data belongs to libvirt rather than being stored in the
instance disk, the vTPM is lost on evacuate, *even if the instance is
volume-backed*. This is analogous to baremetal behavior, where the (hardware)
TPM is left behind even if the rest of the state is resurrected on another
system via shared storage.

(It may be possible to mitigate this by mounting ``/var/lib/libvirt/swtpm/`` on
shared storage, though libvirt's management of that directory on guest
creation/teardown may stymie such attempts. This would also bring in additional
security concerns. In any case, it would be an exercise for the admin; nothing
will be done in nova to support or prevent it.)

Destroy
~~~~~~~

#. Delete the key manager secret associated with
   ``system_metadata['tpm_secret_uuid']``.
#. libvirt deletes the vTPM data directory as part of guest teardown.
#. If ``system_metadata['tpm_object_id']`` exists, the *API side* will delete
   the swift object it identifies. Since this metadata only exists while an
   instance is shelved, this should only be applicable in corner cases like:

   * If the ``destroy()`` is performed between shelve and offload.
   * Cleaning up a VM in ``ERROR`` state from a shelve, offload, or unshelve
     that failed (at just the right time).
   * Cleaning up a VM that is deleted while the host was down.

Limitations
-----------

This is a summary of odd or unexpected behaviors resulting from this design.

* Except for migrations and shelve-offload, vTPM data sticks with the
  instance+host. In particular:

  * vTPM data is lost on Evacuate_.
  * vTPM data is not carried with "reusable snapshots"
    (``createBackup``/``createImage``).

* The ability of instance owners or admins to perform certain instance
  lifecycle operations may be limited depending on the `security model
  <security impact_>`_ used for the `key manager`_.
* Since secret management is done by the virt driver, deleting an
  instance when the compute host is down can orphan its secret. If the host
  comes back up, the secret will be reaped when compute invokes the virt
  driver's ``destroy``. But if the host never comes back up, it would have to
  be deleted manually.

Alternatives
------------

* Rather than using a trait, we could instead use arbitrarily large inventories
  of ``1_2``/``2_0`` resource classes. Unless it can be shown that there's an
  actual limit we can discover, this just isn't how we do things.
* Instead of using specialized ``hw:tpm*`` extra_spec/image_meta properties,
  implicitly configure based on the placement-ese syntax
  (``resources:COMPUTE_SECURITY_TPM_*``). Rejected because we're trying to move
  away from this way of doing things in general, preferring instead to support
  syntax specific to the feature, rather than asking the admin to understand
  how the feature maps to placement syntax. Also, whereas in some cases the
  mapping may be straightforward, in other cases additional configuration is
  required at the virt driver level that can't be inferred from the placement
  syntax, which would require mixing and matching placement and non-placement
  syntax.
* That being the case, forbid placement-ese syntax using
  ``resources[$S]:COMPUTE_SECURITY_TPM_*``. Rejected mainly due to the
  (unnecessary) additional complexity, and because we don't want to get in the
  business of assuming there's no use case for "land me on a vTPM (in)capable
  host, but don't set one up (yet)".
* Use physical passthrough (``<backend type='passthrough'>``) of a real
  (hardware) TPM device. This is not feasible with current TPM hardware because
  (among other things) changing ownership of the secrets requires a host
  reboot.
* Block the operations that require object store. This is deemed nonviable,
  particularly since cross-cell resize uses shelve under the covers.
* Use glance or the key manager instead of swift to store the vTPM data for
  those operations. NACKed because those services really aren't intended for
  that purpose, and (at least glance) may block such usages in the future.
* Save vTPM data on any snapshot operation (including ``createImage`` and
  ``createBackup``). This adds complexity as well as some unintended behaviors,
  such as the ability to "clone" vTPMs. Users will be less surprised when their
  vTPM acts like a (hardware) TPM in these cases.
* Rather than checking for swift at spawn time, add an extra spec / image prop
  like ``vtpm_I_promise_I_will_never_shelve_offload=True`` or
  ``vtpm_is_totally_ephemeral=True`` which would either error or simply not
  back up the vTPM, respectively, on shelve-offload.

Data model impact
-----------------

The ``ImageMetaProps`` and ``ImageMetaPropsPayload`` objects need new versions
adding:

* ``hw_tpm_version``
* ``hw_tpm_model``
* ``tpm_object_id``
* ``tpm_object_sha256``

REST API impact
---------------

The image/flavor validator will get new checks for consistency of properties.
No new microversion is needed.

Security impact
---------------

The guest will be able to use the emulated TPM for all the security enhancing
functionality that a physical TPM provides, in order to protect itself against
attacks from within the guest.

The `key manager`_ and `object store`_ services are assumed to be adequately
hardened against external attack. However, the deployment must consider the
issue of authorized access to these services, as discussed below.

Data theft
~~~~~~~~~~

The vTPM data file is encrypted on disk, and is therefore "safe" (within the
bounds of encryption) from simple data theft.

We will use a passphrase of 384 bytes, which is the default size of an SSH key,
generated from ``/dev/urandom``. It may be desirable to make this size
configurable in the future.

Compromised root
~~~~~~~~~~~~~~~~

It is assumed that the root user on the compute node would be able to glean
(e.g. by inspecting memory) the vTPM's contents and/or the passphrase while
it's in flight. Beyond using private+ephemeral secrets in libvirt, no further
attempt is made to guard against a compromised root user.

Object store
~~~~~~~~~~~~

The object store service allows full access to an object by the admin user,
regardless of who created the object. There is currently no facility for
restricting admins to e.g. only deleting objects. Thus, if a ``shelve`` has
been performed, the contents of the vTPM device will be available to the admin.
They are encrypted, so without access to the key, we are still trusting the
strength of the encryption to protect the data.  However, this increases the
attack surface, assuming the object store admin is different from whoever has
access to the original file on the compute host.

By the same token (heh) if ``shelve`` is performed by the admin, the vTPM data
object will be created and owned by the admin, and therefore only the admin
will be able to ``unshelve`` that instance.

Key manager
~~~~~~~~~~~

The secret stored in the key manager is more delicate, since it can be used to
decrypt the contents of the vTPM device. The barbican implementation scopes
access to secrets at the project level, so the deployment must take care to
limit the project to users who should all be trusted with a common set of
secrets. Also note that project-scoped admins are by default allowed to access
and decrypt secrets owned by any project; if the admin is not to be trusted,
this should be restricted via policy.

However, castellan backends are responsible for their own authentication
mechanisms. Thus, the deployment may wish to use a backend that scopes
decryption to only the individual user who created the secret. (In any case it
is important that admins be allowed to delete secrets so that operations such
as VM deletion can be performed by admins without leaving secrets behind.)

Note that, if the admin is restricted from decrypting secrets, lifecycle
operations performed by the admin cannot result in a running VM. This includes
rebooting the host: even with `resume_guests_state_on_host_boot`_ set, an
instance with a vTPM will not boot automatically, and will instead have to be
powered on manually by its owner.  Other lifecycle operations which are by
default admin-only will only work when performed by the VM owner, meaning the
owner must be given the appropriate policy roles to do so; otherwise these
operations will be in effect disabled.

...except live migration, since the (already decrypted) running state of the
vTPM is carried along to the destination. (To clarify: live migration, unlike
other operations, would actually work if performed by the admin because of the
above.)

.. _resume_guests_state_on_host_boot: https://docs.openstack.org/nova/latest/configuration/config.html#DEFAULT.resume_guests_state_on_host_boot

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

* An additional API call to the key manager is needed during spawn (to register
  the passphrase), cold boot (to retrieve it), and destroy (to remove it).
* Additional API calls to libvirt are needed during spawn and other boot-like
  operations to define, set the value, and undefine the vTPM's secret in
  libvirt.
* Additional API calls to the object store (swift) are needed to create
  (during shelve), retrieve (unshelve), and delete (unshelve/destroy) the vTPM
  device data object.

Other deployer impact
---------------------

None

Developer impact
----------------

The various virt drivers would be able to implement the emulated vTPM as
desired.

Upgrade impact
--------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  stephenfin

Other contributors:
  cfriesen
  efried

Feature Liaison
---------------

stephenfin

Work Items
----------

* API changes to prevalidate the flavor and image properties.
* Scheduler changes to translate flavor/image properties to placement-isms.
* Libvirt driver changes to

  * detect Prerequisites_ and Config_ and report traits to placement.
  * communicate with the key manager API.
  * manage libvirt secrets via the libvirt API.
  * translate flavor/image properties to domain XML_.
  * copy vTPM files on relevant `Instance Lifecycle Operations`_.
  * communicate with object store to save/restore the vTPM files on (other)
    relevant `Instance Lifecycle Operations`_.

* Testing_

Dependencies
============

None

Testing
=======

Unit and functional testing will be added. New fixtures for object store and
key manager services will likely be necessary.

Because of the eccentricities of a) user authentication for accessing the
encryption secret, and b) management of the virtual device files for some
operations, CI coverage will be added for:

- Live migration
- Cold migration
- Host reboot (how?)
- Shelve (offload) and unshelve
- Backup and rebuild

Documentation Impact
====================

Operations Guide and End User Guide will be updated appropriately.
Feature support matrix will be updated.

References
==========

* TPM on Wikipedia: https://en.wikipedia.org/wiki/Trusted_Platform_Module

* ``swtpm``: https://github.com/stefanberger/swtpm/wiki

* Qemu docs on tpm:
  https://github.com/qemu/qemu/blob/master/docs/specs/tpm.txt

* Libvirt XML to request emulated TPM device:
  https://libvirt.org/formatdomain.html#elementsTpm

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Stein
     - Introduced
   * - Train
     - Re-proposed
   * - Ussuri
     - Re-proposed with refinements including encryption pieces
   * - Victoria
     - Re-proposed
