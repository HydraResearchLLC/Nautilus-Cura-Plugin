import re
import os.path
import json
from distutils.version import StrictVersion
from time import sleep

from PyQt5.QtCore import QObject, QUrl, QTimer, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt5.QtQml import QQmlComponent, QQmlContext

from UM.Message import Message
from UM.Logger import Logger

from UM.Resources import Resources
from UM.Extension import Extension
from UM.PluginRegistry import PluginRegistry
from UM.OutputDevice.OutputDevicePlugin import OutputDevicePlugin

from . import HRNetworkOutputDevice
from . import HRNetworkPlugin
from UM.i18n import i18nCatalog
catalog = i18nCatalog("cura")

from cura.CuraApplication import CuraApplication
from cura.MachineAction import MachineAction

class NautilusUpdate(MachineAction, QObject):#, Extension, OutputDevicePlugin):
    def __init__(self, parent=None):
        super().__init__("NautilusUpdate", catalog.i18nc("@action", "Update Firmware"))
        self._qml_url = os.path.join(Resources.getStoragePath(Resources.Resources), "plugins","Nautilus","Nautilus",'qml','NautilusUpdate.qml')
        self.updatePrinter = ''
        Logger.log('i','jkll')
        CuraApplication.getInstance().getPreferences().addPreference("Nautilus/instances", json.dumps({}))
        self._instances = json.loads(CuraApplication.getInstance().getPreferences().getValue("Nautilus/instances"))
        #self.firmwareListChanged.connect(self.instanceFirmwareVersionString)
        #self.firmwareListChanged.connect(self.needsUpdateString)

    firmwareListChanged = pyqtSignal()
    @pyqtProperty("QVariantList", notify=firmwareListChanged)
    def serverList(self):
        #bigguy = json.loads(CuraApplication.getInstance().getPreferences().getValue("Nautilus/instances"))
        self.data = list(self._instances.keys())
        #Logger.log('i','This is the guy: '+str(data))
        self._instances = json.loads(CuraApplication.getInstance().getPreferences().getValue("Nautilus/instances"))
        return self.data

    def thingsChanged(self):
        self.firmwareListChanged.emit()
        #path = os.path.join(PluginRegistry.getInstance().getPluginPath(self.getPluginId()), "qml", "NautilusUpdate.qml")
        #Logger.log("i", "Creating Nautilus preferences UI ")
        #self._application.createQmlComponent(path, {"manager": self}).show()
        HRNetworkPlugin.HRNetworkPlugin().thingsChanged()

    @pyqtSlot(str)
    def setUpdatePrinter(self, name):
        self.updatePrinter = name

    @pyqtSlot()
    def updateConfirm(self):
        Logger.log('i','updateconfirm')
        if self.updatePrinter in self._instances.keys():
            HRNetworkPlugin.HRNetworkPlugin().updateButton(self.updatePrinter)
        else:
            mess = Message("@info","There was an error!")
            mess.show()

    @pyqtSlot()
    def firmwareCheck(self):
        for name in self._instances.keys():
            HRNetworkPlugin.HRNetworkPlugin().updateFirmwareCheck(name)
        sleep(.5)
        self.firmwareListChanged.emit()
        #HRNetworkPlugin.HRNetworkPlugin().thingsChanged()

    @pyqtSlot(str, result=str)
    def instanceUrl(self, name):
        if name in self._instances.keys():
            index = len(self._instances[name]["url"])-1
            return self._instances[name]["url"][7:index]
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

    @pyqtSlot(str, result=str)
    def needsUpdate(self, name):
        if name in self._instances.keys():
            Logger.log('i','returning: '+str(name))
            firmVersion = CuraApplication.getInstance().getPreferences().getValue("Nautilus/configversion")
            if StrictVersion(self._instances[name]["firmware_version"])<StrictVersion(firmVersion):
                return firmVersion+" available!"
            else:
                return "Up-to-Date"
        else:
            return "Something's odd"

    @pyqtSlot(str)
    def setZipPath(self, path):
        Logger.log('d','received path: '+str(path))

    @pyqtSlot(str, result=bool)
    def validPath(self,path):
        path = path[7:]
        Logger.log('d','received path: '+str(path))
        if os.path.exists(path):
            Logger.log('d','Valid!')
            return True
        else:
            Logger.log('d','Invalid!')
            return False

    @pyqtSlot(str, result = bool)
    def statusCheck(self, name):
        if len(name)<1:
            name = self.data[0]
        Logger.log('d','were gettin '+str(name))
        try:
            return HRNetworkPlugin.HRNetworkPlugin().statusCheck(name)
        except:
            return False

"""

    @pyqtSlot(str, result=str)
    def instanceFirmwareVersion(self, name):
        return self.instanceFirmwareVersionString(name)

    @pyqtSlot(str, result=str)
    def needsUpdate(self, name):
        return self.needsUpdateString(name)
"""
