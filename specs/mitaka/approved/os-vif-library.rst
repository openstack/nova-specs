..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================================
VIF port config versioned objects and driver plugin library
===========================================================

https://blueprints.launchpad.net/nova/+spec/os-vif-library

Define a standalone os-vif python library, inspired by os-brick, to provide
a versioned object model for data passed from neutron to nova for VIF port
binding, and an API to allow vendors to provide custom plug/unplug actions
for execution by Nova.

Problem description
===================

When plugging VIFs into VM instances there is communication between Nova
and Neutron to obtain a dict of port binding metadata. Nova passes this
along to the virt drivers which have a set of classes for dealing with
different VIF types. In the libvirt case, each class has three methods,
one for building the libvirt XML config, one for performing host OS config
tasks related to plugging a VIF and one for performing host OS config
tasks related to unplugging a VIF.

Currently, whenever a new Neutron mechanism driver is created, this results
in the definition of a new VIF type, and the addition of a new VIF class to
the libvirt driver to support it. Due to the wide variety of vendors,
there is a potentially limitless number of Neutron mechanisms that need
to be dealt with over time. Conversely the number of different libvirt
XML configurations is quite small and well defined. There are sometimes
new libvirt XML configs defined, as QEMU gains new network backends, but
this is fairly rare. Out of 15 different VIF types supported by libvirt's
VIF driver today, there are only 5 distinct libvirt XML configurations
required. These are illustrated in

  https://wiki.openstack.org/wiki/LibvirtVIFTypeXMLConfigs

The problem with this architecture is that the Nova libvirt maintainers
have task of maintaining the plug/unplug code in the VIF drivers, which
is really code that is defined by the needs of the Neutron mechanism.
This prevents Neutron project / vendors from adding new VIF types without
having a lock-step change in Nova.

A second related problem, is that the format of the data passed between
Nova and Neutron for the VIF port binding is fairly loosely defined. There
is no versioning of the information passed between them and no agreed formal
specification of what the different fields mean. This data is used both to
generate the libvirt XML config and to control the logic of the plug/unplug
actions.


Use Cases
----------

The overall use case is to facilitate the creation of new Neutron mechanisms
by removing Nova as a bottleneck for work. New features can be implemented
entirely in the Neutron codebase (or mechanism specific codebase) with no
need to add/change code in Nova, in the common case.

Proposed change
===============

Inspired by the os-brick library effort started by the Cinder project, the
proposal involves creation of a new library module that will be jointly
developed by the Neutron & Nova teams, for consumption by both projects.

This proposal is describing an architecture with the following high level
characteristics & split of responsibilities

 - Definition of VIF types and associated config metadata.

     * Owned jointly by Nova and Neutron core reviewer teams
     * Code shared in os-vif library
     * Ensures core teams have 100% control over data on
       the REST API

 - Setup of compute host OS networking stack

     * Owned by Neutron mechanism vendor team
     * Code distributed by mechanism vendor
     * Allows vendors to innovate without bottleneck on Nova
       developers in common case.
     * In the uncommon, event a new VIF type was required,
       this would still require os-vif modification with
       Nova & Neutron core team signoff.

 - Configuration of guest virtual machine VIFs ie libvirt XML

     * Owned by Nova virt driver team
     * Code distributed as part of Nova virt / VIF driver
     * Ensures hypervisor driver retains full control over
       how the guest instances are configured

Note that while the description below frequently refers to the Nova libvirt
driver, this proposal is not considered libvirt specific. The same concepts
and requirements for VIF type support exist in all the other virt drivers.
They merely support far fewer different VIF types than libvirt, so the
problems are not so immediately obvious in them.

The library will make use of the oslo.versionedobjects module in order to
formally define a set of objects to describe the VIF port binding data.
The data in this objects will be serialized into JSON, for transmission
between Neutron and Nova, just as is done with the current dicts used
today. The difference is that by using oslo.versionedobjects, we gain
a formal specification and the ability to extend and modify the objects
over time in a manner that is more future proof. One can imagine a base
object

::

    from oslo_versionedobjects import base

    class VIFConfig(base.VersionedObject)
        # Common stuff for all VIFs
        fields = {
            # VIF port identifier
            id:  UUIDField()

            # Various common fields see current
            # nova.network.model.VIF class and related ones
            ...snip...

            # Name of the class used for VIF (un)plugging actions
            plug: StringField()

            # Port profile metadata  - needed for network modes
            # like OVS, VEPA, etc
            profile: ObjectField("VIFProfile")
        }


This base object defines the fields that are common to all the
different VIF port binding types. There are a number of these attributes,
currently detailed in the VIF class in nova.network.model, or the equiv
in Neutron.

One addition here is a 'plug' field which will be the name of a class
that will be used to perform the vendor specific plug/unplug work on the
host OS. The supported values for the 'plug' field will be determined
by Nova via a stevedore based registration mechanism. Nova can pass
this info across to Neutron, so that mechanisms know what plugins have
been installed on the Nova compute node too. Tagging the plugin class
with a version will also be required to enable upgrades where the
Neutron mechanism versions is potentially newer than the nova installed
plugin.

This 'plug' field is what de-couples the VIF types from the vendor specific
work, and will thus allow the number of VIFConfig classes to remain at a
fairly small finite size, while still allowing arbitary number of Neutron
mechanisms to be implemented. As an example, from the current list of VIF
types shown at:

  https://wiki.openstack.org/wiki/LibvirtVIFTypeXMLConfigs

We can see that IVS, IOVISOR, MIDONET and VROUTER all use the same
libvirt type=ethernet configuration, but different plug scripts.
Similarly there is significant overlap between VIFs that use
type=bridge, but with different plug scripts.

The various VIFConfig subclasses will be created, based on the different
bits of information that are currently passed around. NB, this is not
covering all the current VIF_TYPE_XXX variants, as a number of them
have essentially identical config parameter requirements, and only differ
in the plug/unplug actions, hence the point previously about the 'plug'
class name.  All existing VIF types will be considered legacy. These
various config classes will define a completely new set of modern VIF
types. In many cases they will closely resemble the existing VIF types,
but the key difference is in the data serialization format which will
be using oslo.versionedobject serialization instead of dicts. By defining
a completely new set of VIF types, we make it easy for Nova to negotiate
use of the new types with Neutron. When calling Neutron, Nova will
indicate what VIF types it is capable of supporting, and thus Neutron
can determine whether it is able to use the new object based VIF types
or the legacy anonymous dict based types.

The following dependant spec describes a mechanism for communicating
the list of supported VIF types to Neutron when Nova creates a VIF
port.

  https://review.openstack.org/#/c/190917/

What is described in that spec will need some further improvements.
Instead of just a list of VIF types, it will need to be a list of
VIF types and their versions. This will allow Neutron to back-level
the VIF object data to an older version in the event that Neutron
is running a newer version of the os-vif library than is installed
on the Nova compute host. Second, in addition to the list of VIF
types, Nova will also need to provide a list of installed plugins
along with their versions.

So approximately the following set of objects would be defined to
represent the new VIF types. It is expected that the result of the
'obj_name()' API call (defined by oslo VersionedObject base class)
will be used as the VIF type name. This gives clear namespace
separation from legacy VIF type names.

::

    class VIFConfigBridge(VIFConfig):
        fields = {
            # Name of the host TAP device used as the VIF
            devname: StringField(nullable=True)

            # Name of the bridge device to attach VIF to
            bridgename: StringField()
        }

    class VIFConfigEthernet(VIFConfig):
        fields = {
            # Name of the host TAP device used as the VIF
            devname: StringField()
        }

    class VIFConfigDirect(VIFConfig):
        fields = {
            # Source device NIC name on host (eg eth0)
            devname: StringField()
            # An enum of 'vepa', 'passthrough', or 'bridge'
            mode: DirectModeField()
        }

    class VIFConfigVHostUser(VIFConfig):
        fields = {
            # UNIX socket path
            path: StringField()

            # Access permission mode
            mode: StringField()
        }

    class VIFConfigHostDevice(VIFConfig):
        fields = {
            # Host device PCI address
            devaddr: PCIAddressField()

            # VLAN number
            vlan: IntegerField()
        }

NB, the attributes listed in these classes above are not yet totally
comprehensive. At time of implementation, there will be more thorough
analysis of current VIF code to ensure that all required attributes
are covered.

This list is based on the information identified in this wiki page

  https://wiki.openstack.org/wiki/LibvirtVIFTypeXMLConfigs

Some of these will be applicable to other hypervisors too, but there may
be a few more vmware/hypervisor/xenapi specific config subclasses needed
too. This spec does not attempt to enumerate what those will be yet, but
they will be similarly simple and finite set.

Those looking closely will have see reference to a "VIFProfile" object
in the "VIFConfig" class shown earlier. This object corresponds to the
data that can be provided in the <portprofile>...</portprofile> XML
block. This is required data when a VIF is connected to OpenVSwitch,
or when using one of the two VEPA modes. This could have been provided
inline in the the VIFConfig subclasses, but there are a few cases
where the same data is needed by different VIF types, so breaking it
out into a separate object allows better reuse, without increasing
the number of VIF types.

::

     class VIFProfile(base.VersionedObject):
          pass

     class VIFProfile8021QBG(VIFProfile):
          fields = {
            managerid: IntegerField(),
            typeid: IntegerField()
            typeidversion: IntegerField()
            instanceid: UUIDField()
          }

     class VIFProfile8021QBH(VIFProfile):
          fields = {
            profileid: StringField()
          }

     class VIFProfileOpenVSwitch(VIFProfile):
          fields = {
            interfaceid: UUIDField()
            profileid: StringField()
          }


Finally, as alluded to in an earlier paragraph, the library will also need
to define an interface for enabling the plug / unplug actions to be performed.
This is a quite straightforward abstract python class

::

    class VIFPlug(object):

        VERSION = "1.0"

        def plug(self, config):
          raise NotImpementedError()

        def unplug(self, config):
          raise NotImpementedError()

The 'config' parameter passed in here will be an instance of the VIFConfig
versioned object defined above.

There will be at least one subclass of this VIFPlug class provided by each
Neutron vendor mechanism. These subclass implementations do not need to be
part of the os-vif library itself. The mechanism vendors would be expected
to distribute them independently, so decomposition of the neutron development
is maintained. It is expected the vendors will provide a separate VIFPlug
impl for each hypervisor they need to be able to integrate with, so info about
the Nova hypervisor must be provided to Neutron when Nova requests creation
of a VIF port.  The VIFPlug classes must be registered with Nova via the
stevedore mechanism, so that Nova can identify the list of implementations
it has available, and thus validate requests from Neutron to use a particular
plugin. It also allows Nova to tell Neutron which plugins are available for
use. The plugins will be versioned too, so that it is clear to Neutron which
version of the plugin logic will be executed by Nova.

The vendors would not be permitted to define new VIFConfig sub-classes, these
would remain under control of the os-vif library maintainers (ie Neutron and
Nova teams), as any additions to data passed over the REST API must be reviewed
and approved by project maintainers. Thus proposals for new VIFConfig classes
would be submitted to the os-vif repository where the will be reviewed jointly
by the Nova & Neutron representatives working on that library. It is expected
that this will be a fairly rare requirement, since most new mechanism can be
implemented using one of the many existing VIFConfigs.

So when a vendor wishes to create a new mechanism, they first decide which
VIFConfig implementation(s) they need to target, and populate that with the
required information about their VIF. This information is sufficient for
the Nova hypervisor driver to config the guest virtual machine. When
instantiating the VIFConfig impl, the Neutron vendor will set the 'plug'
attribute to refer to the name of the VIFPlug subclass they have implemented
with their vendor specific logic. The vendor VIFPlug subclasses must of course
be installed on the Nova compute nodes, so Nova can load them.

When Nova asks Neutron to create the VIF, neutron returns the serialized
VIFConfig class, which Nova loads. Nova compute manager passes this down
to the virt driver implementation, which instantiates the class defined
by the 'plug' attribute. It will then invoke either the 'plug' or 'unplug'
method depending on whether it is attaching or detaching a VIF to the
guest instance.  The hypervisor driver will then configure the guest
virtual machine using the data stored in the VIFConfig class.

When a new Nova talks to an old Neutron, it will obviously be receiving the
port binding data in the existing dict format. Nova will have to have some
compatibility code to be able to support comsumption of the data in this
format. Nova would likely convert the dict on the fly to the new object
model. The existing libvirt driver VIF plug/unplug methods would also need
to be turned into VIFPlug subclasses.  This way new Nova will be able to
deal with all pre-existing VIF types that old Neutron knows about, with no
loss in functionality.

When an old Nova talks to a new Neutron, Neutron will have to return the
data in the existing legacy port binding format. For this to work, there
needs to be a negotiation between Nova and Neutron to opt-in to use of the
new VIFConfig object model. With an explicit opt-in required, when an old
Nova talks to new Neutron, Neutron will know to return data in the legacy
format that Nova can still understand.  The obvious implication of this
is that any newly developed Neutron mechanisms that rely on the new
VIFCOnfig object model exclusively, will not work with legacy Nova
deployments. This is not considered to be a significant problem, as the
mis-match in Neutron/Nova versions is only a temporary problem as a cloud
undergoes a staged update from Kilo to Liberty

To aid in understanding how this changes from current design, it is helpful
to compare the relationships between the objects. Currently there is mostly
a 1:1 mapping between Neutron mechanisms, vif types, and virt driver plugins.
Thus each new Neutron mechanism has typically needed a new VIF type and
virt driver plugin.

In this new design, there will be the following relationships

 - VIF type <-> VIFConfig class - 1:1 - VIFConfig classes are direct
   representation of each VIF type - a VIF type is simply the name
   of the class used to represent the data.

 - Neutron mechanism <-> VIF type - M:N - A single mechanism can use
   one or more VIF types, a particular choice made at runtime based
   on usage scenario. Multiple mechanisms will be able to use the
   same VIF type

 - VIF type <-> VIF plugins - 1:M - a single VIF type can be used with
   multiple plugins. ie many mechanisms will use the same VIF type, but
   each supply their own plugin implementation for host OS setup

The split between VIF plugins and VIF types is key to the goal of
limiting the number of new VIF types that are created over time.


Alternatives
------------

1. Do nothing. Continue with the current approach where every new Neutron
   mechanism requires a change to Nova hypervisor VIF driver to support
   its vendor specific plug/unplug actions. This will make no one happy.


2. Return to the previous approach, where Nova allows loading of out
   of tree VIF driver plugins for libvirt. This is undesirable for
   a number of reasons.

   The task of configuring a libvirt guest consists of two halves
   commonly referred to as backend configuration (ie the host) and
   frontend configuration (ie what the guest sees). The frontend
   config is something that the libvirt driver needs to retain
   direct control over, in order to support various features that
   are common to all VIFs regardless of backend config.

   In addition the libvirt driver has a set of classes for representing
   the libvirt XML config of a guest, which need to be capable of
   representing any VIF config for the guest. These are considered part
   of the libvirt internal implementation and not a stable API.

   Thirdly, the libvirt VIF driver plugin API has changed in the past
   and may change again in the future, and the data passed into it is
   an ill-defined dict of values from the port binding.

   For these reasons there is a strong desire to not hand off the
   entire implementation of the current libvirt VIF driver class
   to an external 3rd party.


   That all said, this spec does in fact take things back to something
   that is pretty similar to this previous approach. The key differences
   and benefits of this spec, are that it defines a set of versioned
   objects to hold the data that is passed to the 3rd party VIFPlug
   implementation. The external VIFPlug implementation is only being
   responsible for the host OS setup tasks - ie the plug/unplug
   actions. The libvirt driver retains control over guest configuration
   The VIFPlug driver is isolated from the internal impl and API design
   of the libvirt hypervisor driver. The commonality is that the Neutron
   vendor has the ability to retain control of their plug/unplug tasks
   without Nova getting in the way.


3. Keep the current VIF binding approach, but include the name of an
   executable program (script) that Nova will invoke to perform the
   plug/unplug actions.

   This is approximately the same as the proposal in this spec, it is just
   substituting in-process execution of python code, for out of process
   execution of a (shell) script. In the case of scripts, the data from
   the VIF port bindings must be provided to the script, and the proposal
   was to use environment variables. This is moderately ok if the data
   is all scalar, but if there is as need to provide non-scalar
   structured data like dicts/lists, then the environment variable
   approach is very painful to work with.

   The VIF script approach also involves creation of some formal versioned
   objects for representing port binding data, but those objects live
   inside Nova. Since Neutron has the same need to represent the VIF
   port binding data, it is considered better if we can have an external
   python module which defines the versioned objects to represent the
   port binding data, that can be shared between both Nova and Neutron

   It is believed that by defining a formal set of versioned objects
   to represent the VIF port binding data, and a python abstract class
   for the plug/unplug actions, we achieve a strict, clean and easily
   extensible interface for the boudnary between Nova and Neutron,
   avoiding some of the problems inherant in serializing the data via
   environment variables. ie the VIFPlug subclasses will stil get to
   access the well defined VIFConfig class attributes, instead of
   having to parse environment variables.


4. As per this spec, but keep all the VIFConfig classes in Nova instead
   of creating a separate os-vif library. The main downside with this
   is that Neutron will ultimately need to create its own copy of the
   VIFConfig classes, and there will need to be an agreed serialization
   format between Nova and Neutron for the VIF port binding metadata
   passed over the REST API. By having the VIFConfig classes in a
   library that can be used by both Nova and Neutron directly, we ensure
   both apps have a unified object model and can leverage the standard
   oslo.versionedobject serialization format. This brings Neutron/Nova
   a well defined REST API data format this the data passed between them.

5. Move responsibility for VIF plug/unplug to Neutron. This would require
   that Neutron provide an agent to run on every compute node that takes
   care of the plug/unplug actions. This agent would have to have a plugin
   API so that each Neutron mechanism can provide its own logic for the
   plug/nuplug actions. In addition the agent would have to deal with
   staged upgrades where an old agent works with new Neutron or a new
   agent works with old Neutron. There would still need to be work done
   to formalize the VIF config data passed between Neutron and Nova for
   the purpose of configuring the guest instance. So this alternative is
   ultimately pretty similar to what is described in this spec. The current
   proposal can simply be thought of as providing this architecture, but
   with the agent actually built-in to Nova. Given the current impl of
   Neutron & Nova, leveraging Nova as the "agent" on the compute nodes is
   lower effort approach with no strong downsides.


Data model impact
-----------------

There is no change to the database data model.


REST API impact
---------------

This work requires the aforementioned spec to allow Nova to pass details
of its supported VIF types to Neutron:

  https://review.openstack.org/#/c/190917/

For existing "legacy" VIF types, the data format passed back by Neutron
will not change.

For the new "modern" VIF types, the data format passed back by Neutron
will use the oslo.versionedobjects serialization format, instead of just
serializing a plain python dict. In other words, the data will be the
result of the following API call

::

   jsons.dumps(cfg.obj_to_primitive())

where cfg is the VIFConfig versioned object. This JSON data is thus
formally specified and versioned, improving ability to evolve this
in future releases.

In terms of backwards compatibility there are the following scenarios
to consider

 - Old Neutron (Kilo), New Nova (Liberty)

   Nova adds extra info to the request telling Neutron what VIF
   types and plugins are supported. Neutron doesn't know about
   this so ignores it, and returns one of the legacy VIF types.
   Nova libvirt driver transforms this legacy VIF type into a
   modern VIF type, using one of its a built-in back-compat plugins.
   So there should be no loss in functionality compared to old
   Nova

 - New Neutron (Liberty), Old Nova (Kilo)

   Nova does not add any info to the request telling Neutron
   what VIF types are supported. Neutron assumes that Nova
   only supports the legacy VIF types and so returns data in
   that format. Neutron does not attempt to use the modern
   VIF types at all.

 - New Neutron (Liberty), New Nova (Liberty)

   Nova adds extra info to the request telling Neutron what VIF
   types and plugins are supported. The neutron mechanism looks
   at this and decides which VIF type + plugin it wishes to use
   for the port. Neutron passes back a serialized VIFConfig
   object instance. Nova libvirt directly uses its modern code
   path for VIF type handling


 - Even-newer Neutron (Mxxxxx), New-ish Nova (Liberty)

   Nova adds extra info to the request telling Neutron what VIF
   types and plugins are supported. Neutron sees that Nova only
   supports VIFConfigBridge version 1.0, but it has version 1.3.
   Neutron thus uses obj_make_compatible() to backlevel the
   object to version 1.0 before returning the VIF data to Nova.

 - New-ish Neutron (Liberty), Even-newer Nova (Mxxxx)

   Nova adds extra info to the request telling Neutron what VIF
   types and plugins are supported. Neutron only has version 1.0
   but Nova supports version 1.3. Nova can trivially handle version
   1.0, so Neutron can just return data in version 1.0 format
   and Nova just loads it and runs.


Security impact
---------------

The external VIFPlug classes provided by vendors will be able to run
arbitrary code on the compute nodes. This is little different in security
risk than the current situation where the libvirt VIF driver plug/unplug
method implementations run a fairly arbitrary set of commands on the
compute host. One difference though is that the Nova core team will no
longer be responsible for reviewing that code, as it will be maintained
exclusively by the Neutron mechanism vendor.

While it is obviously possible to vendors to add malicious code to
their plugin. This isn't a complete free for all though - the cloud
admin must have taken explicit action to install this plugin on the
compute node and have it registered appropriately via stevedore.
So this does not allow arbitrary code execution by Neutron.

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

When deploying new Neutron mechanisms, they will include a python module
which must be deployed on each compute host. This provides the host OS
plug/unplug logic that will be run when adding VIFs to a guest.

In other words, while currently a user deploying a mechanism would do

::

   pip install neutron-mech-wizzbangnet

on the networking hosts, in the new system they must also run

::

   pip install nova-vif-plugin-wizzbangnet

on any compute nodes that wish to integrate with this mechanism.

It is anticipated that the various vendor tools for deploying openstack
will be able to automate this extra requirement, so cloud admins will
not be appreciably impacted by this.

Developer impact
----------------

When QEMU/libvirt (or another hypervisor) invents a new way of configuring
virtual machine networking, it may be neccessary to define a new versioned
object in the os-vif library that is shared between Neutron and Nova. This
will involve defining a subclass of VIFConfig, and then implementing the
logic in the Nova libvirt driver to handle this new configuration type.
Based on historical frequency of such additions in QEMU, it is expected
that this will be a rare occurrance.

When a vendor wishes to implement a new Neutron mechanism, they will have
to provide an implementation of the VIFPlug class whose abstract interface
is defined in the os-vif library. This vendor specific implementation will
not need to be included in the os-vif library itself - it can be distributed
and deployed by the vendor themselves. This frees the vendor from having to
do a lock-step update to Nova to support their product.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  TBD

Other contributors:

  Daniel Berrange <berrange@redhat.com> irc:danpb
  Brent Eagles <beagles@redhat.com> irc: beagles
  Andreas Scheuring
  Maxime Leroy
  Jay Pipies irc: jaypipes

Work Items
----------

1. Create a new os-vif python module in openstack and/or stackforge

2. Implement the VIFConfig abstract base class as a versioned object
   using oslo.versionedobjects.

3. Agree on and define the minimal set of VIF configurations that
   need to be supported. This is approximately equal to the number
   of different libvirt XML configs, plus a few for other virt
   hypervisors

4. Create VIFConfig subclasses for each of the configs identified
   in step 3.

5. Define the VIFPlug abstract base class for Neutron mechanism
   vendors to implement

6. Extend Neutron such that it is able to ask mechansisms to return
   VIF port data in either the legacy dict format or as a VIFConfig
   object instance

7. Extend Nova/Neutron REST interface so that Nova is able to request
   use of the VIFConfig data format

8. Add code to Nova to convert the legacy dict format into the new
   style VIFConfig object format, for back compat with old Neutron

9. Convert the Neutron mechanisms to be able to use the new VIFConfig
   object model

10. Profit

Dependencies
============

The key dependency is to have collaboration between the Nova and
Neutron teams in setting up the new os-vif python project, and
defining the VIFConfig object model and VIFPlug interface.

There is also a dependancy in agreeing how to extend the REST
API in Neutron to allow Nova to request use of the new data format.
This is discussed in more detail in:

  https://review.openstack.org/#/c/190917/

Though some aspects of that might need updating to take account
of the proposals in this spec

Once those are done, the Nova and Neutron teams can progress on their
respective work items independently.

Testing
=======

The current gate CI system includes cover for some of the Neutron
mechanisms. Once both Neutron and Nova support the new design,
the current CI system will automatically start to test its
operation.

For Neutron mechanisms that are not covered by current CI, it is
expected that the respective vendors take on the task of testing
their own implementations, as is currently the case for 3rd party
CI.

Documentation Impact
====================

The primary documentation impact is not user facing. The docs required
will all be developer facing, so can be done as simple docs inside the
respective python projects.

There will be some specific release notes required to advise cloud admins
of considerations during upgrade. In particular when upgrading Nova it
will be desired to deploy one or more of the Nova VIF plugins to match
the Neutron mechanism(s) that they are currently using. If they fail to
deploy the plugin, then the Nova/Neutron negotiation should ensure that
Neutron continues to use the legacy VIF type, instead of switching to
the modern VIF type.

References
==========

The proposal to add a negotiation between Neuton and Nova for
vif port binding types. This is a pre-requisite for this spec

  https://review.openstack.org/#/c/190917/


The alternative proposal to introduce a VIF script to the existing
VIF port binding data. This spec obsoletes that.

  https://review.openstack.org/#/c/162468/

The alternative proposal to completely outsource hyervisor VIF driver
plugins to 3rd parties once again. This spec obsoletes that.

  https://review.openstack.org/#/c/191210/


Basic impl of library suggested by Jay Pipes

  https://github.com/jaypipes/os_vif


Variant of Jay's design, which more closely matches what is
described in this spec

  https://github.com/berrange/os_vif/tree/object-model

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Liberty
     - Introduced
