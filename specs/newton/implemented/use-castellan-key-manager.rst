..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================
Integrate Castellan for Key Management
======================================

https://blueprints.launchpad.net/nova/+spec/use-castellan-key-manager

Castellan is a key manager interface library that is intended to be usable
with multiple back ends, including Barbican. The Castellan code is based on
the basic key manager interface that resides in Nova and Cinder. Now that the
key manager interface lives in a separate library, the key manager code can be
removed from Nova and Cinder, and Castellan can be used as the key manager
interface instead.

Problem description
===================

As encryption features in OpenStack projects are becoming more common, the
projects typically need a way to interface with a key manager. Different
deployers may have different requirements for key managers, so the key
manager interface must also be configurable to have different back ends. The
Castellan key manager interface was based off the key manager interfaces found
in Cinder and Nova. Now that the shared key manager interface lives in a
separate library, the original key manager interface embedded in Nova can be
removed and Castellan used instead.

Use Cases
----------

Castellan supports existing features such as ephemeral storage encryption and
volume encryption.

Proposed change
===============

Castellan by default pulls configuration options from a Castellan-specific
configuration file in /etc/castellan, but can also take in configuration
options if passed in directly. The configuration options for the key manager
can still be specified in nova.conf, and passed along to Castellan.

The old key manager interface code and back end implementations in nova/keymgr
and tests in nova/tests/unit/keymgr can be removed. Any place in the Nova code
where the key manager interface was called will be replaced by calls to
Castellan instead. Castellan does not include ConfKeyManager, an insecure
fixed-key key manager that reads the key from the configuration file. The
implementation for ConfKeyManager will remain in Nova as the Nova community
agrees that it provides a valuable test fixture.

Alternatives
------------

Castellan was integrated into Nova, but ConfKeyManager still remains in the
Nova source code. There are a few options for improving the integration.
The goals in determining a path forward are the following:

 * Keep Castellan a key manager interface for production-ready back ends
 * Deprecate class-based loading
 * Find a back end to serve as a test fixture for encryption features

However, class-based loading is a Castellan feature, and so the spec for
deprecating class-based loading should live in the Castellan/Barbican specs.
The followng are possible alternatives, which solve one or more of the goals:

 * Remove and replace ConfKeyManager

   One strategy for a path forward is to deprecate and remove ConfKeyManager
   and find an alternative back end suitable for testing. The ConfKeyManager
   back end reads a single, fixed key from a configuration file. It does not
   live in Castellan because ConfKeyManager is very insecure and is only
   suitable for testing. It is only useful for basic testing of encryption
   features using one key, such as Cinder volume encryption. If any
   administrators decided to use ConfKeyManager in their production
   deployment, they will be able to store the fixed key in the new back end as
   part of the migration necessary after deprecation. Other security features
   such as Glance image signing and verification use certificates and cannot
   be tested with ConfKeyManager. A back end closer to what is used in
   production would provide better testing. The following are options for
   replacing ConfKeyManager:

   * Option 1: KMIP Castellan back end

     The Key Manager Interoperability Protocol (KMIP) is a standardized
     protocol for interacting with a key manager. The PyKMIP library [6]
     includes not only client code necessary for interacting with a KMIP
     hardware device but also a KMIP software server with Keystone
     authentication that is useful for functional testing where a hardware
     device is not an option. Work on a KMIP Castellan back end has already
     started [7], but would need to be completed for this option. The PyKMIP
     software server is already used in the Barbican functional gate. New
     DevStack gate checks could be configured to use the PyKMIP server for the
     encryption Tempest tests, or the existing ones could be modified. This
     option satisfies all three of the goals listed above.

   * Option 2: Barbican Castellan back end

     A Barbican back end already exists for Castellan. This option entails
     editing DevStack gate jobs and/or DevStack itself to configure and launch
     Barbican. This option is beneficial because it would test encryption
     features as they should be used in production, as Barbican is the
     recommended back end. However, just 2% of production deployments use
     Barbican [4] so it may not make sense to include it in all of the gates.
     This option would satisfy all three of the goals listed above.

   * Option 3: New database back end

     This option is to create a new Castellan test fixture back end that can
     store multiple objects in a database. While this option will not provide
     a deployment-ready back end, it will be better than ConfKeyManager and
     will be able to support functional testing of features such as signed
     image verification that need to retrieve certificates. This is an
     improvement from using ConfKeyManager because this will allow the key
     manager testing code to be closer to what a deployment configuration
     would look like. However, this back end does not exist yet, and would
     require work to implement the database interactions. Option 1 or Option 2
     would require less Castellan development work. Once completed, this
     option would satisfy two of the three goals.

 * Move ConfKeyManager elsewhere

   The community has expressed concern about ConfKeyManager living in the
   Nova code base, but moving ConfKeyManager into Castellan is not preferred.
   The following are options for if ConfKeyManager cannot be deprecated:

   * Option 4: Move ConfKeyManager to Tempest

     The Tempest tests are the only place where ConfKeyManager should be used,
     so the back end could be moved to Tempest. As long as Castellan provides
     an option to register back ends if class-based loading is deprecated,
     this option could satisfy all three of the goals above.

   * Option 5: Move ConfKeyManager to Castellan

     This is not a recommended option. The ConfKeyManager does not support
     testing of features such as signed image verification [8], which uses
     certificates, not keys. Moving ConfKeyManager to Castellan will push
     the problem of not having an adequate testing back end down the road.

 * Revert the Castellan integration patch

    * Option 6: Revert to nova/keymgr

      This is not a recommended option. The key manager interface will be left
      as it is in nova/keymgr, but this means that Nova's key manager will not
      benefit from the updates, new features, and future additional back ends
      available in Castellan. The key manager interface will not be unified
      across Nova, as the volume encryption feature and encrypted ephemeral
      storage feature will use nova/keymgr, but the image signature
      verification feature already uses Castellan.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

Castellan behaves very similarly to the current Nova key manager. Castellan
has added improvements and bug fixes beyond what is currently in the Nova and
Cinder key managers, making it more secure. The fixed-key key manager found in
Nova and Cinder is insecure for deployments, but it is useful for testing.
Castellan doesn't include the fixed-key key manager, so the ConfKeyManager
will remain in Nova.

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

The deployer should be made aware of a change in the default key manager back
end. The current default back end in Nova is a fixed key, but Castellan uses
Barbican as the default. This means the deployer should ensure Barbican is
running and the fixed key added to Barbican so it can continue to be used.

The options in the Nova configuration file for disk encryption will change. The
option group 'keymgr' will be spelled out to 'key_manager'. The key manager
option group will still have an option 'api_class' to specify the desired back
end, but an option to specify the fixed key will no longer be available. In
the 'barbican' option group, a few new options will be available to increase
the robustness of the back end, such as the number of times to check if a key
has been successfully created.

To maintain backwards compatibility, the old options will still be listed as
deprecated options. Standard deprecation policy will be followed, and these
old options should be removed in the next release cycle.

Developer impact
----------------

Nova developers should not be impacted by this change. If developers find more
uses for a key manager, Castellan should be just as easy to use as the current
Nova key manager interface.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Kaitlin Farr <kaitlin.farr@jhuapl.edu> kfarr on IRC

Other contributors:
  None

Work Items
----------

 * Remove calls to Nova's key manager with calls to Castellan.
 * Remove Nova key manager code.
 * Update documentation.

Dependencies
============

This change depends on Castellan, version >= 0.2.0. Castellan is already in
OpenStack's global requirements.

Testing
=======

This change can be unit tested using a simple in-memory back end. As actual
deployments should be using Barbican, this feature should be tested using a
Barbican back end, too.

Documentation Impact
====================

These changes will be documented. Nova documentation for disk encryption will
be updated to reference Castellan [5].

References
==========

[1] Castellan source code
  https://github.com/openstack/castellan

[2] Castellan in OpenStack's global requirements
  https://github.com/openstack/requirements/blob/master/global-requirements.txt

[3] Current Nova key manager implementation
  https://github.com/openstack/nova/tree/master/nova/keymgr

[4] April 2016 OpenStack User Survey
  http://www.openstack.org/assets/survey/April-2016-User-Survey-Report.pdf

[5] Disk encryption configuration reference
  http://docs.openstack.org/liberty/config-reference/content/section_volume-encryption.html

[6] PyKMIP source code
  https://github.com/openkmip/pykmip

[7] KMIP backend for Castellan
  https://review.openstack.org/#/c/298991/

[8] Glance image signing and verification specification
  https://specs.openstack.org/openstack/glance-specs/specs/liberty/image-signing-and-verification-support.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced
   * - Newton
     - Amended
