####################################################################
# Hydra Research Nautilus plugin for Ultimaker Cura
# A plugin to install config files and Duet functionality
# for the Nautilus printer
#
# Written by Zach Rose
# This section is based on the DuetRRF Plugin by Thomas Kriechbaumer
#
# the DuetRRF plugin source can be found here:
# https://github.com/Kriechi/Cura-DuetRRFPlugin
#
# This plugin is released under the terms of the LGPLv3 or higher.
# The full text of the LGPLv3 License can be found here:
# https://github.com/HydraResearchLLC/Nautilus/blob/master/LICENSE
####################################################################

import re
import os.path
import json
from distutils.version import StrictVersion

from PyQt5.QtCore import QObject, QUrl, QTimer, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt5.QtQml import QQmlComponent, QQmlContext

from UM.Message import Message
from UM.Logger import Logger

from UM.Resources import Resources
from UM.Extension import Extension
from UM.PluginRegistry import PluginRegistry
from UM.OutputDevice.OutputDevicePlugin import OutputDevicePlugin

from . import NautilusOutputDevice
from UM.i18n import i18nCatalog
catalog = i18nCatalog("cura")

from cura.CuraApplication import CuraApplication
from cura.MachineAction import MachineAction


class NautilusDuet(MachineAction, QObject, Extension, OutputDevicePlugin):
    def __init__(self, parent=None):
        super().__init__("NautilusConnections", catalog.i18nc("@action", "Connect via Network"))

        self._qml_url = os.path.join(Resources.getStoragePath(Resources.Resources), "plugins","Nautilus","Nautilus",'qml','NautilusAction.qml')
        self._dialogs = {}
        self._dialogView = None

        CuraApplication.getInstance().getPreferences().addPreference("Nautilus/instances", json.dumps({}))
        self._instances = json.loads(CuraApplication.getInstance().getPreferences().getValue("Nautilus/instances"))
        Logger.log('d','bigmoney')


    def start(self):
        manager = self.getOutputDeviceManager()
        for name, instance in self._instances.items():
            manager.addOutputDevice(NautilusOutputDevice.NautilusOutputDevice(name, instance["url"], instance["duet_password"], instance["http_user"], instance["http_password"], instance["firmware_version"], device_type=NautilusOutputDevice.DeviceType.upload))
            #QTimer.singleShot(15000, NautilusOutputDevice.NautilusOutputDevice(name, instance["url"], instance["duet_password"], instance["http_user"], instance["http_password"], device_type=NautilusOutputDevice.DeviceType.upload).updateCheck)

    def stop(self):
        manager = self.getOutputDeviceManager()
        for name in self._instances.keys():
            manager.removeOutputDevice(name + "-upload")

    def _createDialog(self, qml):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'qml', qml)
        dialog = CuraApplication.getInstance().createQmlComponent(path, {"manager": self})
        return dialog

    def _showDialog(self, qml):
        if not qml in self._dialogs:
            self._dialogs[qml] = self._createDialog(qml)
        self._dialogs[qml].show()

    def showSettingsDialog(self):
        self._showDialog("NautilusDuet.qml")

    def statusCheck(self, name):
        if name in self._instances.keys():
            return NautilusOutputDevice.NautilusOutputDevice(name, self._instances[name]["url"], self._instances[name]["duet_password"], self._instances[name]["http_user"], self._instances[name]["http_password"], self._instances[name]["firmware_version"], device_type=NautilusOutputDevice.DeviceType.upload).checkPrinterStatus()

    serverListChanged = pyqtSignal()
    @pyqtProperty("QVariantList", notify=serverListChanged)
    def serverList(self):
        return list(self._instances.keys())

    @pyqtSlot(str)
    def updateButton(self, name):
        Logger.log('i','we go!')
        if name in self._instances.keys():
            NautilusOutputDevice.NautilusOutputDevice(name, self._instances[name]["url"], self._instances[name]["duet_password"], self._instances[name]["http_user"], self._instances[name]["http_password"], self._instances[name]["firmware_version"], device_type=NautilusOutputDevice.DeviceType.upload).beginUpdate(None, None)
        return None

    @pyqtSlot(str)
    def updateFirmwareCheck(self,name):
        if name in self._instances.keys():
            NautilusOutputDevice.NautilusOutputDevice(name, self._instances[name]["url"], self._instances[name]["duet_password"], self._instances[name]["http_user"], self._instances[name]["http_password"], self._instances[name]["firmware_version"], device_type=NautilusOutputDevice.DeviceType.upload).updateCheck()
        else:
            message = Message(catalog.i18nc("@info:status", "Error finding \"{}\" to update firmware").format(name))
            message.show()
        return None


    @pyqtSlot(str, result=str)
    def instanceUrl(self, name):
        if name in self._instances.keys():
            return self._instances[name]["url"]
        return None

    @pyqtSlot(str, result=str)
    def instanceDuetPassword(self, name):
        if name in self._instances.keys():
            return self._instances[name]["duet_password"]
        return None

    @pyqtSlot(str, result=str)
    def instanceHTTPUser(self, name):
        if name in self._instances.keys():
            return self._instances[name]["http_user"]
        return None

    @pyqtSlot(str, result=str)
    def instanceHTTPPassword(self, name):
        if name in self._instances.keys():
            return self._instances[name]["http_password"]
        return None

    @pyqtSlot(str, result=str)
    def instanceFirmwareVersion(self, name):
        if name in self._instances.keys():
            return self._instances[name]["firmware_version"]

    @pyqtSlot(str, str, str, str, str, str, str)
    def saveInstance(self, oldName, name, url, duet_password, http_user, http_password, firmware_version):
        if oldName:
            # this is a edit operation, delete the old instance before saving the new one
            self.removeInstance(oldName)

        if not url.endswith('/'):
            url += '/'

        self._instances[name] = {
            "url": url,
            "duet_password": duet_password,
            "http_user": http_user,
            "http_password": http_password,
            "firmware_version": firmware_version
        }
        manager = self.getOutputDeviceManager()
        manager.addOutputDevice(NautilusOutputDevice.NautilusOutputDevice(name, url, duet_password, http_user, http_password, firmware_version, device_type=NautilusOutputDevice.DeviceType.upload))
        CuraApplication.getInstance().getPreferences().setValue("Nautilus/instances", json.dumps(self._instances))
        self.serverListChanged.emit()
        Logger.log("d", "Instance saved: " + name)

    @pyqtSlot(str)
    def removeInstance(self, name):
        manager = self.getOutputDeviceManager()
        manager.removeOutputDevice(name + "-upload")
        del self._instances[name]
        CuraApplication.getInstance().getPreferences().setValue("Nautilus/instances", json.dumps(self._instances))
        self.serverListChanged.emit()
        Logger.log("d", "Instance removed: " + name)

    @pyqtSlot(str, str, result = bool)
    def validName(self, oldName, newName):
        if not newName:
            # empty string isn't allowed
            return False
        if oldName == newName:
            # if name hasn't changed, it is not a duplicate
            return True

        # duplicates not allowed
        return (not newName in self._instances.keys())

    @pyqtSlot(str, str, result = bool)
    def validUrl(self, oldName, newUrl):
        if newUrl.startswith('\\\\'):
            # no UNC paths
            return False
        if not re.match('^https?://.', newUrl):
            # missing https?://
            return False
        if '@' in newUrl:
            # @ is probably HTTP basic auth, which is a separate setting
            return False

        return True

    @pyqtSlot(str, result = str)
    def needsUpdate(self, name):
        if name in self._instances.keys():
            Logger.log('i','returning: '+str(name))
            firmVersion = CuraApplication.getInstance().getPreferences().getValue("Nautilus/configversion")
            if StrictVersion(self._instances[name]["firmware_version"])<StrictVersion(firmVersion):
                return "Version "+firmVersion+" available!"
            else:
                return "Up-to-Date"
        else:
            return "Something's odd"

    def thingsChanged(self):
        self.serverListChanged.emit()
