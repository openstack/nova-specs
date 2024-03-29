..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================================
Remove the API support for generating a keypair
===============================================

https://blueprints.launchpad.net/nova/+spec/keypair-generation-removal


As agreed on the last PTG, given RSA-SHA1 support is removed from recent OSes,
we prefer to remove the possibility to generate a keypair directly by Nova and
just be able to import a public key.


Problem description
===================

During the Yoga release, we triaged an open bug report [1]_ which noted
the fact that OpenSSH 8.8 removed support for RSA/SHA1 signatures
[2]_. As a result of this change in OpenSSH behavior, keypairs generated by
Nova are incompatible with recent guest OSes like CentOS9.
This leads to guests that are inaccessible via SSH using the created keypairs.

The consensus of the Nova community during the last PTG was to remove the
generation of keypairs from the ``os-keypairs`` API.

Use Cases
---------

As a user, I want to ssh to my instance without getting problems because I
generated a keypair.

As an admin, I want a seamless experience for my users and I let them to
generate their own keypairs depending on the images they want.


Proposed change
===============

We'll propose a new API microversion that will force the user to send a
public key.

Accordingly, the JSON request schema of POST /os-keypairs will look like this :


.. code-block:: python

  create_v2XX = {
      'type': 'object',
      'properties': {
          'keypair': {
              'type': 'object',
              'properties': {
                  'name': parameter_types.name,
                  'type': {
                      'type': 'string',
                      'enum': ['ssh', 'x509']
                  },
                  'public_key': {'type': 'string'},
                  'user_id': {'type': 'string'},
              },
              'required': ['name', 'public_key'],
              'additionalProperties': False,
          },
      },
      'required': ['keypair'],
      'additionalProperties': False,
  }

The JSON response will also change as we no longer generate private keys :

* ``private_key`` will never be returned from that microversion


Given we'll create a new microversion, we'll also use it for allowing
``. (dot)`` and ``@ (at)`` characters for the keypair name as it was accepted
on a previous spec for Xena [3]_.

This will mean that we will modify the _validate_new_key_pair() method to
accept those parameters only if wanted (which also means we will move this
method to the keypairs specific API module).


Alternatives
------------

For API interoperability reasons, we would have had to also create a new API
microversion if we wanted to support a new keypair type, eg. edcsa, which
defeats the purpose of simplicity.


Data model impact
-----------------

None.

REST API impact
---------------

All the details are already described above. The response will only drop the
meaningless private_key value as we continue to return a keypair with its
signature.
No policy changes are identified, as we only drop support for a capability.


Security impact
---------------

We'll improve security, for sure, by not letting Nova to create keypairs that
are disabled by OS policy due to the flaws of SHA-1 (even if ssh-rsa can
verify keys with SHA-256 hash algorithm) [4]_.


Notifications impact
--------------------

None.


Other end user impact
---------------------

novaclient and openstackclient new releases will remove support for generating
a keypair if you opt-in for the recent server microversion.


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

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  sylvain-bauza

Feature Liaison
---------------

None.

Work Items
----------

* write the API change.
* amend documentation and tests.
* write novaclient, openstacksdk and openstackclient support for this.


Dependencies
============

None.


Testing
=======

Unittests for sure, but we'll also need to modify Tempest to generate
the keypair by itself and import it into Nova. Thanks to the FIPS support we
already have, a conditional in Tempest already pre-generates a keypair and
tampers the payload by adding the generated public key [5]_, so we should just
make it default in our upstream jobs.


Documentation Impact
====================

None, besides API documentation.


References
==========

* .. [1] https://bugs.launchpad.net/nova/+bug/1962726
* .. [2] https://www.openssh.com/txt/release-8.8
* .. [3] https://specs.openstack.org/openstack/nova-specs/specs/xena/approved/allow-special-characters-in-keypair-name.html
* .. [4] "SHA-1 is a Shambles: First Chosen-Prefix Collision on SHA-1 and
     Application to the PGP Web of Trust" Leurent, G and Peyrin, T
     (2020) https://eprint.iacr.org/2020/014.pdf
* .. [5] https://github.com/openstack/tempest/blob/c545cb1c7c14d36d2bc65a55ec13e0c6cd095425/tempest/lib/services/compute/keypairs_client.py#L81-L88


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Zed
     - Introduced
