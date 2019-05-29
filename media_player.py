"""Support to interface with Sonos players. Extending Standard Sonos Component for static configuration"""
import pysonos.discovery as pysonosdiscover
import pysonos
import asyncio
import traceback
import threading

import homeassistant.components.sonos.media_player as sonosha

DEPENDENCIES = ('sonos',)

"""
Helper für Überwachung der LazySoCo bis zur Verwendung
"""
class LazySoCoHelper():
    def __init__(self):
        self._lock = threading.RLock()
        self.connectors = []
        self.connectors_toinit = []
        self.init_thread = None
        self.entity_added = threading.Event()

    def registerSoCo(self, soco):
        with self._lock:
            self.connectors.append(soco)
            self.connectors_toinit.append(soco)
            self.entity_added.set()
            self.check_initthread_running()

    def check_initthread_running(self):
        with self._lock:
            if not self.connectors_toinit or self.init_thread != None:
                return
            self.init_thread = threading.Thread(
                target=self._initthread, daemon=True)
            self.init_thread.start()

    def discover(self, callback):
        with self._lock:
            for soco in self.connectors:
                callback(soco)

    def _initthread(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        while True:
            connectors_toinit = []
            with self._lock:
                for connector in self.connectors_toinit:
                    if connector.is_lazy_connected():
                        self.connectors_toinit.remove(connector)
                    else:
                        connectors_toinit.append(connector)
                if not connectors_toinit:
                    self.init_thread = None
                    break
            self.entity_added.wait(timeout=30)
            self.entity_added.clear()
            loop = asyncio.get_event_loop()
            loop.run_until_complete(
                self._initconnectors(connectors_toinit, loop=loop))
        loop.close()

    async def _initconnectors(self, connectors_toinit, loop=None):
        futures = []
        for connector in connectors_toinit:
            futures.append(connector._initialize(loop))
        for future in futures:
            await future


helper = LazySoCoHelper()

SoCo = pysonos.SoCo

class NoneSubscription():
    def unsubscribe(self):
        pass


class LazyService():
    def subscribe(self, requested_timeout=None, auto_renew=False, event_queue=None):
        return NoneSubscription()


class LazyZoneGroupTopology(LazyService):
    def GetZoneGroupState(self, *args, **kwargs):
        return ""


class EmptyMusicLibrary():
    def get_sonos_favorites(self):
        return []


""" Helper Class for using pysonos lazy with home assistant"""


class LazySoCo(SoCo):
    def __init__(self, ip, zoneName):
        self._lazyuid = None
        self._inited = False
        self._lazyZoneName = zoneName
        self._ip = ip
        super().__init__(ip)
        helper.registerSoCo(self)

    async def _initialize(self, loop=None):
        connection = asyncio.open_connection(host=self._ip, port=1400, loop=loop)
        try:
            reader, writer = await asyncio.wait_for(connection, 3, loop=loop)
            writer.close()
            self._inited = True
        except (asyncio.TimeoutError, OSError) as e:
            return

    def is_lazy_connected(self):
        return self._inited

    @property
    def uid(self):
        if self._lazyuid is None:
            self._lazyuid = "lazy" + self.ip_address
        return self._lazyuid

    def get_speaker_info(self, refresh=False, timeout=None):
        if self._inited:
            return super().get_speaker_info(refresh=refresh, timeout=timeout)
        info = dict()
        info['zone_name'] = self._lazyZoneName
        info['model_name'] = "Sonos Lazy Connector"
        return info

    @property
    def shuffle(self):
        if self._inited:
            return super().shuffle
        return False

    @property
    def volume(self):
        if self._inited:
            return super().volume
        return 0

    @property
    def mute(self):
        if self._inited:
            return super().mute
        return True

    @property
    def night_mode(self):
        if self._inited:
            return super().night_mode
        return None

    @property
    def dialog_mode(self):
        if self._inited:
            return super().dialog_mode
        return None

    @property
    def music_library(self):
        if self._inited:
            return self._music_library
        return EmptyMusicLibrary()

    @music_library.setter
    def music_library(self, music_library):
        self._music_library = music_library
        music_library.contentDirectory = self._contentDirectory

    @property
    def avTransport(self):
        if self._inited:
            return self._avTransport
        return LazyService()

    @avTransport.setter
    def avTransport(self, avTransport):
        self._avTransport = avTransport

    @property
    def renderingControl(self):
        if self._inited:
            return self._renderingControl
        return LazyService()

    @renderingControl.setter
    def renderingControl(self, renderingControl):
        self._renderingControl = renderingControl

    # das darf nicht ignoriert werdne bzw. muss dann sehr sauber gewrapped werden.
    @property
    def zoneGroupTopology(self):
        if self._inited:
            return self._zoneGroupTopology
        return LazyZoneGroupTopology()

    @zoneGroupTopology.setter
    def zoneGroupTopology(self, zoneGroupTopology):
        self._zoneGroupTopology = zoneGroupTopology

    @property
    def contentDirectory(self):
        if self._inited:
            return self._contentDirectory
        return LazyService()

    @contentDirectory.setter
    def contentDirectory(self, contentDirectory):
        self._contentDirectory = contentDirectory

    @property
    def group(self):
        if self._inited:
            return super().group
        return None


pysonos.SoCo = LazySoCo


def static_discover_thread(callback,
                           timeout,
                           include_invisible,
                           interface_addr):
    global helper
    helper.discover(callback)


pysonosdiscover._discover_thread = static_discover_thread


class LazySonosEntity(sonosha.SonosEntity):
    def __init__(self, player):
        super().__init__(player)
        self._available = False
        pass

    def seen(self):
        if not self._player.is_lazy_connected():
            self._seen = 0
            return
        super().seen()


sonosha.SonosEntity = LazySonosEntity


async def async_setup_platform(hass,
                               config,
                               async_add_entities,
                               discovery_info=None):
    """Set up the Sonos platform.
    """
    try:
        for host in config['hosts']:
            LazySoCo(host['ip'], host['name'])
    except Exception as e:
        print(traceback.format_exc())
