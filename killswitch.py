#!/usr/bin/python
#
# python-killswitch -- Convenient Functions for Managing Killswitches
#
# Copyright (C) 2009,2010,2011 Holger Macht <holger@homac.de>
#
# This file is released under the WTFPL (http://sam.zoy.org/wtfpl/)
#

"""python-killswitch provides a python module called killswitch. It
provides convenient function/methods for other applications to manage all
the killswitches found in the system.

Usually the first thing you do is:

  import killswitch

  k = killswitch.KillswitchManager()

Then you can make use of the methods like that:

  for ks in k.get_killswitches():
      print "Killswitch %d:" % I
      print "\tUDI: %s" % ks.udi()
      print "\tName: %s" % ks.name()
      print "\tType: %s" % ks.type()
      print "\tPower: %d" % ks.get_state()

python-killswitch supports both HAL and URfkill as backend.
"""

import dbus

_URFKILL_SERVICE="org.freedesktop.URfkill"
_URFKILL_PATH="/org/freedesktop/URfkill"

_HAL_SERVICE="org.freedesktop.Hal"
_HAL_MANAGER_PATH="/org/freedesktop/Hal/Manager"
_HAL_DEVICE_SERVICE="org.freedesktop.Hal.Device"
_HAL_MANAGER_SERVICE="org.freedesktop.Hal.Manager"

def _message(message):
    print "python-killswich: %s" % message

_dbus_is_set_up = 0
def _setup_dbus():
    global _dbus_is_set_up

    if not _dbus_is_set_up:
        from dbus.mainloop.glib import DBusGMainLoop

        dbus_loop = DBusGMainLoop()
        dbus.set_default_main_loop(dbus_loop)
        _dbus_is_set_up = 1

    return dbus.SystemBus()

def _have_urfkill():
    bus = _setup_dbus()

    if bus.name_has_owner(_URFKILL_SERVICE):
        return 1
    else:
        _message("URfkill not running, trying to start it...")

    try:
        manager = bus.get_object(_URFKILL_SERVICE, _URFKILL_PATH)
    except dbus.exceptions.DBusException, e:
        if e.get_dbus_name() == "org.freedesktop.DBus.Error.ServiceUnknown":
            _message("Service URfkill not available")
            return 0

    if bus.name_has_owner(_URFKILL_SERVICE):
        return 1

    return 0

def _have_hal():
    if _setup_dbus().name_has_owner(_HAL_SERVICE):
        return 1
    return 0

class Killswitch():
    "class representing one single killswitch object"
    def __init__(self, bus, udi=None, name=None, type=None, is_urfkill=0):
        """Initialize a new Killswitch object. Usually you should not need
        to create objects of this class because the KillswitchManager does
        it.
        bus: a properly initiated object to a D-Bus system bus
        udi: unique device itendifier
        name: a proper name for the killswitch
        type: a killswitch type, such as wlan, bluetooth, gps, wwan, etc."""

        if is_urfkill:
            self.k = _KillswitchUrfkill(bus, udi, name, type)
        else:
            self.k = _KillswitchHal(bus, udi, name, type)

    def name(self):
        "return the name of the killswitch"
        return self.k.name()

    def udi(self):
        "return the unique device identifier (udi) of the killswitch object"
        return self.k.udi()

    def type(self):
        "return the type of the killswitch object (bluetooth, wlan, etc...)"
        return self.k.type()

    def get_state(self):
        """returns the current state of the killswitch object.
        0: Killswitch is on, device is disabled via software
        1: Killswitch is off, device operational
        2: Killswitch is on, device disabled via hardware switch"""

        return self.k.get_state()

    def set_state(self, state):
        """sets the killswitch state, either to true or to false. true
        enables the killswitch, thus disables the device"""

        return self.k.set_state(state)

class _KillswitchAbstract():
    def __init__(self, bus, udi=None, name=None, type=None):
        self._bus = bus
        self.__name = name
        self.__type = type
        self.__udi = udi

    def name(self):
        return self.__name

    def udi(self):
        return self.__udi

    def type(self):
        return self.__type

class _KillswitchHal(_KillswitchAbstract):
    def __init__(self, bus, udi=None, name=None, type=None):
        _KillswitchAbstract.__init__(self, bus, udi, name, type)

        manager = self._bus.get_object(_HAL_SERVICE, udi)
        self.manager_interface = dbus.Interface(manager,
                                                dbus_interface='org.freedesktop.Hal.Device.KillSwitch')

    def get_state(self):
        return self.manager_interface.GetPower()

    def set_state(self, state):
        return self.manager_interface.SetPower(state)

class _KillswitchUrfkill(_KillswitchAbstract):
    def __init__(self, bus, udi=None, name=None, type=None):
        _KillswitchAbstract.__init__(self, bus, udi, name, type)

        manager = self._bus.get_object(_URFKILL_SERVICE, _URFKILL_PATH)
        self.manager_interface = dbus.Interface(manager, dbus_interface=_URFKILL_SERVICE)

    def get_state(self):
        return not self.manager_interface.GetKillswitch(self.udi())[2]

    def set_state(self, state):
        if state == 1:
            return self.manager_interface.UnblockIdx(self.udi())
        elif state == 0:
            return self.manager_interface.BlockIdx(self.udi())
        else:
            _message("Unknown state")

class KillswitchManager():
    """Base class providing convenient function to keep track of the state
    of all the killswitches in the system"""

    def __init__(self):
        if _have_urfkill():
            _message("Using URfkill")
            self.k = _KillswitchManagerUrfkill();
        elif _have_hal():
            _message("Using HAL")
            self.k = _KillswitchManagerHal();
        else:
            _message("Neither urfkill nor HAL found, bailing out...")

    def set_state_changed_cb(self, cb):
        """Set the callback function which is called as soon as a
        killswitch changes its state.  See the get_state() function of the
        Killswitch class for the exact values"""
        
        self.k.set_state_changed_cb(cb)

    def get_killswitches(self):
        "Returns an array of all killswitches (Killswitch objects) which are found"
        return self.k._switches

    def enable_all(self):
        "Enable all killswitches at once"
        for ks in self.k._switches:
            ks.set_state(1)

    def disable_all(self):
        "Disable all killswitches at once"
        for ks in self.k._switches:
            ks.set_state(0)

    def set_killswitch_added_cb(self, cb):
        """Set the callback function which is called when a new killswitch
        is found. A new Killswitch object will be passed to the callback
        function"""
        self.k.set_killswitch_added_cb(cb)

    def set_killswitch_removed_cb(self, cb):
        """Set the callback function which is called when a killswitch
        vanishes. The Killswitch object which was removed will be passed
        to the callback function"""
        self.k.set_killswitch_removed_cb(cb)

class _KillswitchManagerAbstract():
    def __init__(self):
        """Initialize the connection to a backend daemon and update the list
        of killswitches found in the system"""

        self._bus = _setup_dbus()
        self._switches = []
        self._state_changed_cb = None
        self._killswitch_added_cb = None
        self._killswitch_removed_cb = None

    def set_state_changed_cb(self, cb):
        self._state_changed_cb = cb

    def set_killswitch_added_cb(self, cb):
        self._killswitch_added_cb = cb

    def set_killswitch_removed_cb(self, cb):
        self._killswitch_removed_cb = cb

class _KillswitchManagerUrfkill(_KillswitchManagerAbstract):
    def __init__(self):
        """Initialize the connection to the URfkill daemon and update the list
        of killswitches found in the system"""

        _KillswitchManagerAbstract.__init__(self)

        for ks in self.__get_killswitches():
            ks = Killswitch(self._bus, ks[0], ks[5], self.__get_name_for_type(ks[1]), 1); 
            name = ks.name()
            _message("found ks with name %s and type %s" % (name, ks.type()))
            self._switches.append(ks)

        self._bus.add_signal_receiver(self.__killswitch_modified_cb,
                                      "RfkillChanged",
                                      _URFKILL_SERVICE, _URFKILL_SERVICE, _URFKILL_PATH)
        self._bus.add_signal_receiver(self.__killswitch_added_cb,
                                      "RfkillAdded",
                                      _URFKILL_SERVICE, _URFKILL_SERVICE, _URFKILL_PATH)
        self._bus.add_signal_receiver(self.__killswitch_removed_cb,
                                      "RfkillRemoved",
                                      _URFKILL_SERVICE, _URFKILL_SERVICE, _URFKILL_PATH)

    def __get_killswitches(self):
        manager = self._bus.get_object(_URFKILL_SERVICE, _URFKILL_PATH)
        iface = dbus.Interface(manager, dbus_interface=_URFKILL_SERVICE)

        return iface.GetAll()
                         
    def __killswitch_modified_cb(self, index, type, state, soft, hard, name):
        for item in self._switches:
            if index == item.udi():
                state = item.get_state()
                _message("new state of %s is %s" % (item.udi(), state))
                self._state_changed_cb(item, state)

    def __killswitch_added_cb(self, index, type, state, soft, hard, name):
        for item in self._switches:
            if index == item.udi():
                _message("killswitch already in list")
                return

        ks = Killswitch(self._bus, index, name, self.__get_name_for_type(type), 1); 
        name = ks.name()
        type = ks.type()

        _message("adding %s with name %s and type %s" % (index, name, self.__get_name_for_type(type)))

        self._switches.append(ks)
        self._killswitch_added_cb(ks)

    def __killswitch_removed_cb(self, index):
        for item in self._switches:
            if index == item.udi():
                _message("removing killswitch %s" % item.udi())
                self._killswitch_removed_cb(item)
                self._switches.remove(item)

    def __get_name_for_type(self, type):
            if type == 0:
                return "type all"
            elif type == 1:
                return "wlan"
            elif type == 2:
                return "bluetooth"
            elif type == 3:
                return "uwb"
            elif type == 4:
                return "wimax"
            elif type == 5:
                return "wwan"
            elif type == 6:
                return "gps"
            elif type == 7:
                return "fm"
            else:
                return "unknown type"

class _KillswitchManagerHal(_KillswitchManagerAbstract):
    def __init__(self):
        """Initialize the connection to the HAL daemon and update the list
        of killswitches found in the system"""

        _KillswitchManagerAbstract.__init__(self)

        for udi in self.__hal_get_killswitches():
            name = self.__hal_get_property(udi, "killswitch.name")
            if name == False:
                name = self.__hal_get_property(udi, "info.product")
                if name == False:
                    _message("Killswitch has no killswitch.name nor a info.product")
                    continue

            type = self.__hal_get_property(udi, "killswitch.type")

            self._switches.append(Killswitch(self._bus, udi, name, type, 0))

            self._bus.add_signal_receiver(self.__property_modified_cb,
                                               "PropertyModified",
                                               _HAL_DEVICE_SERVICE,
                                               _HAL_SERVICE,
                                               udi, path_keyword="path")

        self._bus.add_signal_receiver(self.__device_added_cb,
                                           "DeviceAdded",
                                           _HAL_MANAGER_SERVICE,
                                           _HAL_SERVICE,
                                           _HAL_MANAGER_PATH)
        self._bus.add_signal_receiver(self.__device_removed_cb,
                                           "DeviceRemoved",
                                           _HAL_MANAGER_SERVICE,
                                           _HAL_SERVICE,
                                           _HAL_MANAGER_PATH)

        _message("name: %s" % self._switches)
                         
    def __property_modified_cb(self, num_changes, change_list, path):
        for item in self._switches:
            if path == item.udi():
                state = item.get_state()
                self._state_changed_cb(item, state)

    def __device_added_cb(self, path):
        if self.__hal_has_capability(path, "killswitch"):
            for item in self._switches:
                if path == item.udi():
                    _message("killswitch already in list")
                    return
            
            name = self.__hal_get_property(path, "killswitch.name")
            if name == False:
                name = self.__hal_get_property(path, "info.product")
                if name == False:
                    _message("Killswitch has no killswitch.name nor a info.product")
                    return

            _message("new killswitch %s  " % (path))

            type = self.__hal_get_property(path, "killswitch.type")
            _message("adding %s with name %s and type %s" % (path, name, type))
            ks = Killswitch(self._bus, path, name, type, 0)
            self._switches.append(ks)
            self._killswitch_added_cb(ks)

    def __device_removed_cb(self, path):
        for item in self._switches:
            if path == item.udi():
                _message("removing killswitch %s" % item.udi())
                self._killswitch_removed_cb(item)
                self._switches.remove(item)

    def __hal_get_property(self, udi, key):
        manager = self._bus.get_object(_HAL_SERVICE, udi)
        iface = dbus.Interface(manager,
                               dbus_interface=_HAL_DEVICE_SERVICE)
        if not iface.PropertyExists(key):
            return False
        return iface.GetProperty(key)

    def __hal_has_capability(self, udi, capability):
        manager = self._bus.get_object(_HAL_SERVICE, udi)
        iface = dbus.Interface(manager,
                               dbus_interface=_HAL_DEVICE_SERVICE)
        return iface.QueryCapability(capability)

    def __hal_get_killswitches(self):
        manager = self._bus.get_object(_HAL_SERVICE, _HAL_MANAGER_PATH)

        iface = dbus.Interface(manager,
                               dbus_interface=_HAL_MANAGER_SERVICE)

        return iface.FindDeviceByCapability("killswitch")
