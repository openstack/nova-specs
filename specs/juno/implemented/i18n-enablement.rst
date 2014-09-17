..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
i18n Enablement for Nova
==========================================

https://blueprints.launchpad.net/nova/+spec/i18n-enablement

This BluePrint/Spec proposes completing the enablement of i18n
(internationalization) support for Nova by turning on the "lazy" translation
support from Oslo i18n and updating Nova to adhere to the restrictions this
adds to translatable strings.

Internationalization implementation has been an on-going effort in OpenStack
during recent releases.  The original blueprint for the Oslo support was
included in Havana:
https://blueprints.launchpad.net/oslo/+spec/delayed-message-translation

Blueprints for this support in Nova have been approved and worked on in
previous releases
(https://blueprints.launchpad.net/nova/+spec/user-locale-api).
During the Icehouse release, the foundational support for internationalization
was merged into Nova.  Specifically the update of Oslo's gettextutils and the
pre-existing work of explicitly importing '_' from gettextutils.

To finalize this work in Juno we need to enable the "lazy" translation
provided in gettextutils and change how messages are manipulated.  Enablement
of lazy translation will allow end users to not only have logs produced in
multiple languages, but adds the ability for REST API messages to also be
returned in the language chosen by the user.  This functionality is important
to support the use of OpenStack by the international community.


Problem description
===================

Today all users of Nova must agree on a common locale to use to translate
messages.  This is because messages are translated when they are created.
There is a need for different Nova users to be able to use different
translations simultaneously.

Proposed change
===============

This proposal is to use the i18n support provided as part of Oslo in order
to enable "lazy" translation of messages.  This support, instead of
immediately translating the messages, creates a Message object which
holds the message and replacement text until the message can be translated
using the locale associated with the Accept-Language Header from the
user request.

The code changes will be done as a series of patches that culminate in a
patch that adds a call to 'gettextutils.enable_lazy()' in
nova/cmd/__init__.py.

A few prepratory patches will be required due to the limitations of the
i18n support:

* The Message class does not support str(), so use of str() on translatable
  messages must be removed.  The most common case being when it is used on an
  exception that is being put into another translatable message or logged.
  This is due to the requirement by logging in Python 2.6 that str() return
  a UnicodeError.
* The Message class does not support concatenation of translatable messages,
  so concatenation of translatable messages must be replaced with formatting.
  This is due to the complexity caused by trying to concatenate two
  independent Message instances potentially with overlapping replacement keys.
  There are very few of these and the use of formatting allows for better
  translation by translators.

Alternatives
------------

None.

Data model impact
-----------------

None.

REST API impact
---------------

There is no additional changes to the REST API other than the fact
that the change enables the user to specify the language they
wish REST API responses to be returned in using the Accept-Language
option.

Security impact
---------------

None.

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

Once merged this feature is immediately available to users.


Developer impact
----------------

The developer impacts have already been in place for some time.  Developers
have been using _() around messages that need translation.

Note, however, that with the relatively new policy of not translating debug
log messages, concatenating strings and exceptions will need care since the
strings have to be cast to unicode. See https://review.openstack.org/#/c/78095/
for examples. Cleaning this up is listed in the Work Items section.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <jecarey@us.ibm.com>

Work Items
----------

I am planning to implement this as three patches in this order:

* Remove concatenations of translatable messages
* Remove use of str() on translatable messages
* Add enable_lazy to nova/cmd/__init__.py
* Investigate and add hacking checks to catch i18n unfriendly practices

Dependencies
============

None.

* Note that gettextutil was synced with the latest oslo-incubator via
  commit 185e4562df47a101cf41d1e66d75de2644c78022.


Testing
=======

* There will be a tempest test added for Nova that will ensure that
  lazy translation is working properly.

* Hacking checks will be investigated and added for failures caused when
  enabling lazy translation.

  * For example the changes in https://review.openstack.org/#/c/78095/ and
    https://review.openstack.org/#/c/78096/ which includes using str()
    (or six.text_type) on an exception used as replacement text.


Documentation Impact
====================

None.


References
==========

* Mailing list discussion initiated by FFE rejected request for adding i18n to
  Icehouse:
  https://www.mail-archive.com/openstack-dev@lists.openstack.org/msg18617.html
* Accept-Language header: http://www.w3.org/International/questions/qa-accept-lang-locale
