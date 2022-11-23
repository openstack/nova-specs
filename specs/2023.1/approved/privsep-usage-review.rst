..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================
Review usage of oslo-privsep library on Nova
============================================

https://blueprints.launchpad.net/nova/+spec/privsep-usage-review

Nova's usage of the privsep library is too broad. A single global permission
profile with all needed capabilities is defined for all functions that interact
with privsep to use. While this works, it is not the best usage of the library
as functions are getting a set of rights they do not need and thus should not
receive. This spec seeks to fix this situation by defining a more specialized
usage of the library.

Problem description
===================

Nova compute services use the oslo-privsep library to obtain elevated
privileges on the host system with the intention of invoking python functions
or linux commands that affect areas of the host that require of such
privileges.

Today, Nova's usage of privsep follows best practices that were recommended
by the library when it was first created:

#. Create a dedicated module for privileged functions.
#. Create a single context and restrict its usage to that module.
#. Limit scope of privileged functions and reuse their actions as unprivileged
   code.

Based on usage of the library over the years, it has become clear that this
approach is neither secure nor desirable to be continued. In the current
design, a single profile is shared by all functions that make use of the
library. This one aggregates all capabilities required by all privileged
functions on the code. This means that for a single function that operates
over the filesystem, all the other ones that do not also get such capability.
This fact may lead to unexpected behaviors that can be avoided if more precise
profiles are used for each case.

Use Cases
---------

As a developer, I want to have a fined tuned method for acquiring capabilities.
As an admin, I want Nova to use as little elevated privileges as possible.

Proposed change
===============

Given that all current functions that use the privsep library are found under
``nova.privsep``. First step is to study and map each with the capabilities
they require. Next, a set of profiles can be defined for common use cases,
such as network or system rights, and cover with them as much as possible.
The rest will have to be divided into smaller functions that do fit into one
of those profiles. If that is not possible, then the current all-capable
profile will need to be kept for them until a better solution is found.

Profiles will now be defined under the ``__init__.py`` file found at:
`<https://github.com/openstack/nova/blob/master/nova/__init__.py>`_, while
functions using these will be distributed through other packages. Here is an
example on how the file may end up looking like::

  legacy_pctxt = priv_context.PrivContext(
      'nova',
      cfg_section='nova_sys_admin',
      pypath=__name__ + '.legacy_pctxt',
      capabilities=[capabilities.CAP_CHOWN,
                    capabilities.CAP_DAC_OVERRIDE,
                    capabilities.CAP_DAC_READ_SEARCH,
                    capabilities.CAP_FOWNER,
                    capabilities.CAP_NET_ADMIN,
                    capabilities.CAP_SYS_ADMIN],
  )

  sys_admin_pctxt = priv_context.PrivContext(
      'nova',
      cfg_section='privsep_sys_admin',
      pypath=__name__ + '.sys_admin_pctxt',
      capabilities=[capabilities.CAP_SYS_ADMIN],
  )

  net_admin_pctxt = priv_context.PrivContext(
      'nova',
      cfg_section='privsep_net_admin',
      pypath=__name__ + '.net_admin_pctxt',
      capabilities=[capabilities.CAP_NET_ADMIN],
  )

  file_admin_pctxt = priv_context.PrivContext(
      'nova',
      cfg_section='privsep_file_admin',
      pypath=__name__ + '.file_admin_pctxt',
      capabilities=[capabilities.CAP_CHOWN,
                    capabilities.CAP_DAC_OVERRIDE,
                    capabilities.CAP_DAC_READ_SEARCH,
                    capabilities.CAP_FOWNER],
  )

Each newly defined profile will spawn a daemon that consumes resources on the
host. For such reason, no more than 4 profiles may be defined at a single time
to avoid over encumbering it.

For the sake of improving usability, shared code found across the package's
functions should be extracted into other, unprivileged functions with broader
contracts. These will take care of performing more generic actions, like
'chown' or 'mkdir', that may not require more than the user's rights to be
done. When elevated permissions are required though, specialized single use
functions with a narrow contract will be defined using one of the new privsep
contexts. These functions will be created following these conditions:

* Will contain the ``privileged_`` prefix on their name.
* Will be defined at the same package that uses them.
* Will only be imported by a single module, excepting unit tests.

Here is an example of how this implementation would be like::

  # in nova/common/filesytem.py

  def write_file(
    path: str,
    data: str = None,
    mode: str = 'w'
  ) -> ty.Optional[str]:
      try:
          with open(path, mode=mode) as fd:
              fd.write(data)
      except (OSError, ValueError) as e:
          LOG.debug(e)
          raise

  def chown_file(
    path: str,
    usr: str = None,
    grp: str = None
  ) -> ty.Optional[str]:
      try:
          shutil.chown(path, user=usr, group=grp)
      except (OSError, ValueError) as e:
          LOG.debug(e)
          raise

  # in nova/virt/libvirt/driver.py
  import nova

  from nova.common import filesystem as fs
  ...

  @nova.file_admin_pctxt
  def privileged_write_tpm_data(
    instance: uuid,
    tpm_data: str
  ) -> ty.Optional[str]:
      if not oslo_utils.uuidutils.is_uuid_like(instance):
          raise ValueError(f"instance: {instance} is not a valid uuid")
      path = os.path.join(CONF.instace_state_dir, instance)
      try:
          fs.write_file(path, data=tpm_data, mode='wb')
          fs.chown_file(path, "nova", "qemu")
      except (OSError, ValueError) as e:
          LOG.debug(e)

Alternatives
------------

None that I can think of. Please, provide any feedback on the scope of this
spec and its approach.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

Requires the use of elevated privileges.

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

In case the tenant's openstack distribution does not use defaults for
elevated privileges configuration, then the privsep daemons spawned after this
spec must be configured following the options at:
`<https://docs.openstack.org/nova/latest/configuration/config.html#privsep>`_.


Developer impact
----------------

Developers will need to analyze which capabilities are required for any new
functions under ``nova.privsep`` and apply the correct profile accordingly.

Upgrade impact
--------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jsanemet

Feature Liaison
---------------

Feature liaison:
  sylvainb

Work Items
----------

* Study functions that already use oslo-privsep to determine which capabilities
  each need.
* Define profiles for functions that share a common context, i.e.: run a system
  command, modify network settings...

Dependencies
============

None

Testing
=======

Tempest tests must continue to pass without the need for any modifications,
verifying that everything still works the same running under reduced
permission sets.

Documentation Impact
====================

None

References
==========

First discussed at:
https://etherpad.opendev.org/p/nova-privsep-review

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2023.1 Antelope
     - Introduced
