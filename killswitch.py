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
"""

import dbus

class Killswitch:
    "class representing one single killswitch object"
    def __init__(self, bus, udi=None, name=None, type=None):
        """Initialize a new Killswitch object. Usually you should not need
        to create objects of this class because the KillswitchManager does
        it.
        bus: a properly initiated object to a D-Bus system bus
        udi: unique device itendifier (HAL)
        name: name returned by the HAL killswitch.name property
        type: type returned by the HAL killswitch.type property (wlan, bluetooth, etc.)"""
        self.bus = bus
        self.__name = name
        self.__type = type
        self.__udi = udi

    def name(self):
        "return the name of the killswitch"
        return self.__name

    def udi(self):
        "return the unique device identifier (udi) of the killswitch object"
        return self.__udi

    def type(self):
        "return the type of the killswitch object (bluetooth, wlan, etc...)"
        return self.__type

    def get_state(self):
        "returns the current state of the killswitch object"
        manager = self.bus.get_object('org.freedesktop.Hal',
                                      self.udi())
        manager_interface = dbus.Interface(manager,
                                           dbus_interface='org.freedesktop.Hal.Device.KillSwitch')
        return manager_interface.GetPower()
        
    def set_state(self, state):
        "sets the killswitch state, either to true or to false"
        manager = self.bus.get_object('org.freedesktop.Hal',
                                      self.udi())
        manager_interface = dbus.Interface(manager,
                                           dbus_interface='org.freedesktop.Hal.Device.KillSwitch')
        return manager_interface.SetPower(state)        


class _Hal():
    "handling communication with the HAL daemon"
    def __init__(self):
        from dbus.mainloop.glib import DBusGMainLoop

        dbus_loop = DBusGMainLoop()
        dbus.set_default_main_loop(dbus_loop)
        self.bus = dbus.SystemBus()

        self.hal_manager = self.bus.get_object('org.freedesktop.Hal',
                                               '/org/freedesktop/Hal/Manager')

        self.hal_manager_iface = dbus.Interface(self.hal_manager,
                                                dbus_interface='org.freedesktop.Hal.Manager')

    def _hal_get_property(self, udi, key):
        manager = self.bus.get_object('org.freedesktop.Hal',
                                      udi)
        iface = dbus.Interface(manager,
                               dbus_interface='org.freedesktop.Hal.Device')
        if not iface.PropertyExists(key):
            return False
        return iface.GetProperty(key)

    def _hal_has_capability(self, udi, capability):
        manager = self.bus.get_object('org.freedesktop.Hal',
                                      udi)
        iface = dbus.Interface(manager,
                               dbus_interface='org.freedesktop.Hal.Device')
        return iface.QueryCapability(capability)

    def _hal_get_killswitches(self):
        return self.hal_manager_iface.FindDeviceByCapability("killswitch")

class KillswitchManager(_Hal):
    """Base class providing convenient function to keep track of the state
    of all the killswitches in the system"""
    def __init__(self):
        """Initialize the connection to the HAL daemon and update the list
        of killswitches found in the system"""
        _Hal.__init__(self)
        self.__switches = []
        self.__state_changed_cb = None
        self.__killswitch_added_cb = None
        self.__killswitch_removed_cb = None

        for udi in self._hal_get_killswitches():
            name = self._hal_get_property(udi, "killswitch.name")
            if name == False:
                continue

            type = self._hal_get_property(udi, "killswitch.type")

            self.__switches.append(Killswitch(self.bus, udi, name, type))

            self.bus.add_signal_receiver(self.__property_modified_cb,
                                               "PropertyModified",
                                               "org.freedesktop.Hal.Device",
                                               "org.freedesktop.Hal",
                                               udi, path_keyword="path")

        self.bus.add_signal_receiver(self.__device_added_cb,
                                           "DeviceAdded",
                                           "org.freedesktop.Hal.Manager",
                                           "org.freedesktop.Hal",
                                           "/org/freedesktop/Hal/Manager")
        self.bus.add_signal_receiver(self.__device_removed_cb,
                                           "DeviceRemoved",
                                           "org.freedesktop.Hal.Manager",
                                           "org.freedesktop.Hal",
                                           "/org/freedesktop/Hal/Manager")
                         
    def __property_modified_cb(self, num_changes, change_list, path):
        for item in self.__switches:
            if path == item.udi():
                state = item.get_state()
                self.__state_changed_cb(item, state)

    def __device_added_cb(self, path):
        if self._hal_has_capability(path, "killswitch"):
            print "new killswitch %s  " % (path)
            name = self._hal_get_property(path, "killswitch.name")
            if name == False:
                print "Killswitch has no killswitch.name"
                return
            type = self._hal_get_property(path, "killswitch.type")
            print "adding %s with name %s and type %s" % (path, name, type)
            ks = Killswitch(path, name, type)
            self.__switches.append(ks)
            self.__killswitch_added_cb(ks)

    def __device_removed_cb(self, path):
        for item in self.__switches:
            if path == item.udi:
                print "removing killswitch %s" % item.udi
                self.__killswitch_removed_cb(item)
                self.__switches.remove(item)

    def get_killswitches(self):
        "Returns an array of all killswitches (Killswitch objects) which are found"
        return self.__switches

    def set_state_changed_cb(self, cb):
        "Set the callback function which is called as soon as a killswitch changes its state"
        self.__state_changed_cb = cb

    def set_killswitch_added_cb(self, cb):
        """Set the callback function which is called when a new killswitch
        is found. A new Killswitch object will be passed to the callback
        function"""
        self.__killsiwtch_added_cb = cb

    def set_killswitch_removed_cb(self, cb):
        """Set the callback function which is called when a killswitch
        vanishes. The Killswitch object which was removed will be passed
        to the callback function"""
        self.__killswitch_removed_cb = cb

    def enable_all(self):
        "Enable all killswitches at once"
        for ks in self.__switches:
            ks.set_state(1)

    def disable_all(self):
        "Disable all killswitches at once"
        for ks in self.__switches:
            ks.set_state(0)
