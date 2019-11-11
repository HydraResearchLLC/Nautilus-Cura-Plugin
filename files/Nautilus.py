####################################################################
# Hydra Research Nautilus plugin for Ultimaker Cura
# A plugin to install config files and Duet functionality
# for the Nautilus printer
#
# Written by Zach Rose
# Based on the Dremel 3D20 plugin written by Tim Schoenmackers
# and the DuetRRF Plugin by Thomas Kriechbaumer
# contains code from the GCodeWriter Plugin by Ultimaker
#
# the Dremel plugin source can be found here:
# https://github.com/timmehtimmeh/Cura-Dremel-3D20-Plugin
#
# the GCodeWriter plugin source can be found here:
# https://github.com/Ultimaker/Cura/tree/master/plugins/GCodeWriter
#
# the DuetRRFPlugin source can be found here:
# https://github.com/Kriechi/Cura-DuetRRFPlugin
#
# This plugin is released under the terms of the LGPLv3 or higher.
# The full text of the LGPLv3 License can be found here:
# https://github.com/HydraResearchLLC/Nautilus/blob/master/LICENSE
####################################################################

import os # for listdir
import platform # for platform.system
import os.path # for isfile and join and path
import sys
import zipfile
import shutil  # For deleting plugin directories;
import stat    # For setting file permissions correctly;
import re #For escaping characters in the settings.
import json
import copy
import struct
import time
import configparser
import urllib.request
import requests
import ssl
import json

from distutils.version import StrictVersion # for upgrade installations

from UM.i18n import i18nCatalog
from UM.Extension import Extension
from UM.Message import Message
from UM.Resources import Resources
from UM.Logger import Logger
from UM.Preferences import Preferences
from UM.Mesh.MeshWriter import MeshWriter
from UM.Settings.InstanceContainer import InstanceContainer
from UM.Qt.Duration import DurationFormat
from UM.Qt.Bindings.Theme import Theme
from UM.PluginRegistry import PluginRegistry
from . import NautilusDuet
from . import Upgrader
from cura.CuraApplication import CuraApplication

from PyQt5.QtWidgets import QApplication, QFileDialog
from PyQt5.QtGui import QPixmap, QScreen, QColor, qRgb, QImageReader, QImage, QDesktopServices
from PyQt5.QtCore import QByteArray, QBuffer, QIODevice, QRect, Qt, QSize, pyqtSlot, QObject, QUrl, pyqtProperty


catalog = i18nCatalog("cura")


class Nautilus(QObject, MeshWriter, Extension):
    # The version number of this plugin - please change this in all three of the following Locations:
    # 1) here
    # 2) plugin.json
    # 3) package.json
    version = "1.1.0"

    ##  Dictionary that defines how characters are escaped when embedded in
    #   g-code.
    #
    #   Note that the keys of this dictionary are regex strings. The values are
    #   not.
    escape_characters = {
        re.escape("\\"): "\\\\",  # The escape character.
        re.escape("\n"): "\\n",   # Newlines. They break off the comment.
        re.escape("\r"): "\\r"    # Carriage return. Windows users may need this for visualisation in their editors.
    }

    def __init__(self):
        super().__init__()
        self._application = CuraApplication.getInstance()
        self._setting_keyword = ";SETTING_"
        #self._application.initializationFinished.connect(self._onInitialized)
        #def _onInitialized(self):
        self.this_plugin_path=os.path.join(Resources.getStoragePath(Resources.Resources), "plugins","Nautilus","Nautilus")
        self._preferences_window = None
        self._guides = None

        self.local_meshes_path = None
        self.local_printer_def_path = None
        self.local_materials_path = None
        self.local_quality_path = None
        self.local_extruder_path = None
        self.local_variants_path = None
        self.local_setvis_path = None
        self.local_global_dir = None
        self.local_intent_path = None
        Logger.log("i", "Nautilus Plugin setting up")
        self.local_meshes_path = os.path.join(Resources.getStoragePathForType(Resources.Resources), "meshes")
        self.local_printer_def_path = Resources.getStoragePath(Resources.DefinitionContainers)#os.path.join(Resources.getStoragePath(Resources.Resources),"definitions")
        self.local_materials_path = os.path.join(Resources.getStoragePath(Resources.Resources), "materials")
        self.local_quality_path = os.path.join(Resources.getStoragePath(Resources.Resources), "quality")
        self.local_extruder_path = os.path.join(Resources.getStoragePath(Resources.Resources),"extruders")
        self.local_variants_path = os.path.join(Resources.getStoragePath(Resources.Resources), "variants")
        self.local_setvis_path = os.path.join(Resources.getStoragePath(Resources.Resources), "setting_visibility")
        self.local_global_dir = os.path.join(Resources.getStoragePath(Resources.Resources),"machine_instances")
        self.local_intent_path = os.path.join(Resources.getStoragePath(Resources.Resources),"intent")
        self.setvers = self._application.getPreferences().getValue("metadata/setting_version")
        self.gitUrl = 'https://api.github.com/repos/HydraResearchLLC/Nautilus-Configuration-Macros/releases/latest'
        self.fullJson = json.loads(requests.get(self.gitUrl).text)


        # if the plugin was never installed, then force installation
        if self._application.getPreferences().getValue("Nautilus/install_status") is None:
            self._application.getPreferences().addPreference("Nautilus/install_status", "unknown")
            Logger.log("i","1")

        if self._application.getPreferences().getValue("Nautilus/configversion") is None:
            Logger.log("i","reseting config version")
            self._application.getPreferences().addPreference("Nautilus/configversion","1.0.0")

        # if something got messed up, force installation
        if not self.isInstalled() and self._application.getPreferences().getValue("Nautilus/install_status") is "installed":
            self._application.getPreferences().setValue("Nautilus/install_status", "unknown")
            Logger.log("i","2")

        # if it's installed, and it's listed as uninstalled, then change that to reflect the truth
        if self.isInstalled() and self._application.getPreferences().getValue("Nautilus/install_status") is "uninstalled":
            self._application.getPreferences().setValue("Nautilus/install_status", "installed")
            Logger.log("i","3")

        # if the version isn't the same, then force installation
        if not self.versionsMatch():
            self._application.getPreferences().setValue("Nautilus/install_status", "unknown")
            Logger.log("i","4")

        # Check the preferences to see if the user uninstalled the files -
        # if so don't automatically install them
        if self._application.getPreferences().getValue("Nautilus/install_status") is "unknown":
            # if the user never installed the files, then automatically install it
            Logger.log("i","5")
            self.installPluginFiles()

        if not self.configVersionsMatch():
            self.messageMaker()
            Logger.log("i","time for a config update!")


            #This is the signal for machines changing
        CuraApplication.getInstance().globalContainerStackChanged.connect(self.updateMachineName)
        Duet=NautilusDuet.NautilusDuet()
        self.addMenuItem(catalog.i18nc("@item:inmenu","Nautilus Connections"), Duet.showSettingsDialog)
        self.addMenuItem(catalog.i18nc("@item:inmenu", "Resources and Guides"), self.showGuides)
        self.addMenuItem(catalog.i18nc("@item:inmenu", "Preferences"), self.showPreferences)

        # finally save the cura.cfg file
        self._application.getPreferences().writeToFile(Resources.getStoragePath(Resources.Preferences, self._application.getApplicationName() + ".cfg"))


    def createPreferencesWindow(self):
        path = os.path.join(PluginRegistry.getInstance().getPluginPath(self.getPluginId()), "qml", "Nautilusprefs.qml")
        Logger.log("i", "Creating Nautilus preferences UI "+path)
        self._preferences_window = self._application.createQmlComponent(path, {"manager": self})

    def showPreferences(self):
        if self._preferences_window is None:
            self.createPreferencesWindow()
            statuss=self._application.getPreferences().getValue("Nautilus/install_status")
        self._preferences_window.show()

    def createGuidesWindow(self):
        path = os.path.join(PluginRegistry.getInstance().getPluginPath(self.getPluginId()), "qml", "Nautilusguides.qml")
        Logger.log("i", "Creating Nautilus guides UI "+path)
        self._guides = self._application.createQmlComponent(path, {"manager": self})

    def showGuides(self):
        if self._guides is None:
            self.createGuidesWindow()
        self._guides.show()

    def hidePreferences(self):
        if self._preferences_window is not None:
            self._preferences_window.hide()

            #This is the function
    def updateMachineName(self):
        self.MachineName = CuraApplication.getInstance().getMachineManager().activeMachine.definition.name
        #Logger.log("i", "updating this machine to "+self.MachineName)
        if "Nautilus" in self.MachineName:
            NautilusDuet.NautilusDuet().start()
        elif self.MachineName != None:
            NautilusDuet.NautilusDuet().stop()



    # function so that the preferences menu can open website the version
    @pyqtSlot()
    def openPluginWebsite(self):
        url = QUrl('https://github.com/HydraResearchLLC/Nautilus/releases', QUrl.TolerantMode)
        if not QDesktopServices.openUrl(url):
            message = Message(catalog.i18nc("@info:status", "Nautilus plugin could not navigate to https://github.com/HydraResearchLLC/Nautilus.6/releases"))
            message.show()
        return

    @pyqtSlot()
    def showHelp(self):
        Logger.log("i", "Nautilus Plugin opening help page: https://www.hydraresearch3d.com/resources/")
        try:
            if not QDesktopServices.openUrl(QUrl("https://www.hydraresearch3d.com/resources/")):
                message = Message(catalog.i18nc("@info:status", "Nautilus plugin could not open https://www.hydraresearch3d.com/resources/ please navigate to the page for assistance"))
                message.show()
        except:
            message = Message(catalog.i18nc("@info:status", "Nautilus plugin could not open https://www.hydraresearch3d.com/resources/ please navigate to the page for assistance"))
            message.show()
        return

    @pyqtSlot()
    def reportIssue(self):
        Logger.log("i", "Nautilus Plugin opening issue page: https://github.com/HydraResearchLLC/Nautilus/issues/new")
        try:
            if not QDesktopServices.openUrl(QUrl("https://github.com/HydraResearchLLC/Nautilus/issues/new")):
                message = Message(catalog.i18nc("@info:status", "Nautilus plugin could not open https://github.com/HydraResearchLLC/Nautilus/issues/new please navigate to the page and report an issue"))
                message.show()
        except:
            message = Message(catalog.i18nc("@info:status", "Nautilus plugin could not open https://github.com/HydraResearchLLC/Nautilus/issues/new please navigate to the page and report an issue"))
            message.show()
        return

    @pyqtSlot()
    def openQualityGuide(self):
        url = QUrl('https://www.hydraresearch3d.com/print-quality-troubleshooting', QUrl.TolerantMode)
        if not QDesktopServices.openUrl(url):
            message = Message(catalog.i18nc("@info:status", "Nautilus plugin could not navigate to https://www.hydraresearch3d.com/print-quality-troubleshooting"))
            message.show()
        return

    @pyqtSlot()
    def openDesignGuide(self):
        url = QUrl('https://www.hydraresearch3d.com/design-rules', QUrl.TolerantMode)
        if not QDesktopServices.openUrl(url):
            message = Message(catalog.i18nc("@info:status", "Nautilus plugin could not navigate to https://www.hydraresearch3d.com/design-rules"))
            message.show()
        return

    @pyqtSlot()
    def openSlicingGuide(self):
        url = QUrl('https://www.hydraresearch3d.com/advanced-slicing-guide', QUrl.TolerantMode)
        if not QDesktopServices.openUrl(url):
            message = Message(catalog.i18nc("@info:status", "Nautilus plugin could not navigate to https://www.hydraresearch3d.com/advanced-slicing-guide"))
            message.show()
        return

    @pyqtSlot()
    def openMaterialGuide(self):
        url = QUrl('https://www.hydraresearch3d.com/material-guide', QUrl.TolerantMode)
        if not QDesktopServices.openUrl(url):
            message = Message(catalog.i18nc("@info:status", "Nautilus plugin could not navigate to https://www.hydraresearch3d.com/material-guide"))
            message.show()
        return

    @pyqtSlot()
    def openUserManual(self):
        url = QUrl('https://www.hydraresearch3d.com/nautilus-resources', QUrl.TolerantMode)
        if not QDesktopServices.openUrl(url):
            message = Message(catalog.i18nc("@info:status", "Nautilus plugin could not navigate to https://www.hydraresearch3d.com/nautilus-resources"))
            message.show()
        return

    @pyqtProperty(str)
    def getVersion(self):
        numba = Nautilus.version
        Logger.log("i","Nailed it!"+numba)
        return str(numba)

    # returns true if the versions match and false if they don't
    def versionsMatch(self):
        # get the currently installed plugin version number
        if self._application.getPreferences().getValue("Nautilus/curr_version") is None:
            self._application.getPreferences().addPreference("Nautilus/curr_version", "0.0.0")

        installedVersion = self._application.getPreferences().getValue("Nautilus/curr_version")

        if StrictVersion(installedVersion) == StrictVersion(Nautilus.version):
            # if the version numbers match, then return true
            Logger.log("i", "Nautilus Plugin versions match: "+installedVersion+" matches "+Nautilus.version)
            return True
        else:
            Logger.log("i", "Nautilus Plugin installed version: " +installedVersion+ " doesn't match this version: "+Nautilus.version)
            return False

    def messageMaker(self):
        message=Message(catalog.i18nc("@info:status", "New features are available for your Nautilus! It is recommended to update the firmware on your printer."), 0)
        message.addAction("download_config", catalog.i18nc("@action:button", "How to update"), "globe", catalog.i18nc("@info:tooltip", "Open website to download new firmware"))
        message.actionTriggered.connect(self._onMessageActionTriggered)
        message.show()

    def _onMessageActionTriggered(self,message,action):
        url = QUrl('https://www.hydraresearch3d.com/nautilus-resources', QUrl.TolerantMode)
        if not QDesktopServices.openUrl(url):
            message = Message(catalog.i18nc("@info:status", "Nautilus plugin could not navigate to https://www.hydraresearch3d.com/nautilus-resources"))
            message.show()
        return

    def configVersionsMatch(self):
        newVersion = str(json.dumps(self.fullJson['tag_name'])).replace("\"","")
        installedVersion = str(self._application.getPreferences().getValue("Nautilus/configversion")).replace("\"","")
        Logger.log("i","Here we go. have "+installedVersion + "git has " + newVersion)
        if StrictVersion(installedVersion) == StrictVersion(newVersion):
            Logger.log("i","Some stuff, it's chill. have "+installedVersion + "git has " + newVersion)
            return True
        else:
            Logger.log("i","No Bueno " + newVersion + " have " + installedVersion)
            self._application.getPreferences().setValue("Nautilus/configversion",newVersion)
            return False


    # check to see if the plugin files are all installed
    def isInstalled(self):
        HRNautilusDefFile = os.path.join(self.local_printer_def_path,"hydra_research_nautilus.def.json")
        nautilusExtruderDefFile = os.path.join(self.local_extruder_path,"hydra_research_nautilus_extruder.def.json")
        nautilusMatDir = os.path.join(self.local_materials_path,"nautilusmat")
        nautilusQualityDir = os.path.join(self.local_quality_path,"nautilusquals")
        nautilusIntentDir = os.path.join(self.local_intent_path,"nautilusintent")
        nautilusVariantsDir = os.path.join(self.local_variants_path,"nautilusvars")
        nautilusSettingVisDir = os.path.join(self.local_setvis_path,'hrn_settings')
        sstatus = 0
        # if some files are missing then return that this plugin as not installed
        if not os.path.isfile(HRNautilusDefFile):
            Logger.log("i", "Nautilus definition file is NOT installed ")
            sstatus += 1
            return False
        if not os.path.isfile(nautilusExtruderDefFile):
            Logger.log("i", "Nautilus extruder file is NOT installed ")
            sstatus += 1
            return False
        if not os.path.isdir(nautilusMatDir):
            Logger.log("i", "Nautilus material files are NOT installed ")
            sstatus += 1
            return False
        if not os.path.isdir(nautilusQualityDir):
            Logger.log("i", "Nautilus quality files are NOT installed ")
            sstatus += 1
            return False
        if not os.path.isdir(nautilusIntentDir):
            Logger.log("i", "Nautilus intent files are NOT installed ")
            sstatus += 1
            return False
        if not os.path.isdir(nautilusVariantsDir):
            Logger.log("i", "Nautilus variant files are NOT installed ")
            sstatus += 1
            return False
        if not os.path.isdir(nautilusSettingVisDir):
            Logger.log("i","Nautilus setting visibility file is NOT installed")
            sstatus += 1
            return False

        # if everything is there, return True
        if sstatus < 1:
            Logger.log("i", "Nautilus Plugin all files ARE installed")
            self._application.getPreferences().setValue("Nautilus/install_status", "installed")
            return True

    # install based on preference checkbox
    @pyqtSlot(bool)
    def changePluginInstallStatus(self, bInstallFiles):
        if bInstallFiles and not self.isInstalled():
            self.installPluginFiles()
            message = Message(catalog.i18nc("@info:status", "Nautilus config files have been installed. Restart cura to complete installation"))
            message.show()
        elif self.isInstalled():
            Logger.log("i","Uninstalling")
            self.uninstallPluginFiles(False)

    def setCurrency(self):
        testitem = str(self._application.getPreferences().getValue("cura/currency"))
        Logger.log("i","it is "+testitem)
        if self._application.getPreferences().getValue("cura/currency") is None:
            Logger.log("i","check me out")
            self._application.getPreferences().addPreference("cura/currency","$")
            self._application.getPreferences().setValue("cura/currency","$")
        else:
            self._application.getPreferences().setValue("cura/currency","$")
        self._application.getPreferences().writeToFile(Resources.getStoragePath(Resources.Preferences, self._application.getApplicationName() + ".cfg"))

    # Install the plugin files.
    def installPluginFiles(self):
        self.setCurrency()
        Logger.log("i", "Nautilus Plugin installing printer files")
        upper = Upgrader.Upgrader()
        value = upper.configFixer()
        intentNames = ['engineering.inst.cfg','visual.inst.cfg','quick.inst.cfg']
        if value:
            Logger.log("i","uninstall that shit")
            self.uninstallPluginFiles(value)
        try:
            restartRequired = False
            zipdata = os.path.join(self.this_plugin_path,"Nautilus.zip")
            Logger.log("i","Nautilus Plugin installing from: " + zipdata)

            with zipfile.ZipFile(zipdata, "r") as zip_ref:
                for info in zip_ref.infolist():
                    Logger.log("i", "Nautilus Plugin: found in zipfile: " + info.filename )
                    folder = None
                    flag = False
                    if info.filename == "hydra_research_nautilus.def.json" or info.filename == "hrfdmprinter.def.json" or info.filename == "hrfdmextruder.def.json":
                        folder = self.local_printer_def_path
                    elif info.filename == "hydra_research_excluded_materials.json":
                        folder = self.local_printer_def_path
                        flag = True
                    elif info.filename == "hydra_research_nautilus_extruder.def.json":
                        folder = self.local_extruder_path
                    elif info.filename.endswith("nautilus.cfg"):
                        folder = self.local_setvis_path
                    elif info.filename.endswith("fdm_material"):
                        folder = self.local_materials_path
                    elif info.filename.endswith("0.inst.cfg"):
                        folder = self.local_variants_path
                        Logger.log("i", "Finding Variants")
                    elif any(info.filename.endswith(name) for name in intentNames):
                        folder = self.local_intent_path
                        Logger.log("i", "Finding Intent")
                    elif info.filename.endswith(".cfg"):
                        folder = self.local_quality_path
                        Logger.log("i", "Finding Quality")
                    elif info.filename.endswith(".stl"):
                        folder = self.local_meshes_path
                        if not os.path.exists(folder): #Cura doesn't create this by itself. We may have to.
                            os.mkdir(folder)

                    if flag == True: #create the excluded materials file on install so all native Cura materials are blocked
                        cura_dir=os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])),"resources","materials")
                        materiallist = os.listdir(cura_dir)
                        #print(materiallist)
                        with zip_ref.open(info,'r') as f:
                            data = f.read()
                            obj=json.loads(data.decode('utf-8'))
                            entry = {}
                            obj['metadata']['exclude_materials'] = str(materiallist)
                            Logger.log("i", "Nautilus Plugin installing excluded materials to " + folder)
                            with open(os.path.join(folder,'hydra_research_excluded_materials.def.json'),'w') as g:
                                g.write(json.dumps(obj,indent=4))
                                g.close()
                            f.close()
                        folder = None
                    if folder is not None:
                        extracted_path = zip_ref.extract(info.filename, path = folder)
                        permissions = os.stat(extracted_path).st_mode
                        os.chmod(extracted_path, permissions | stat.S_IEXEC) #Make these files executable.
                        Logger.log("i", "Nautilus Plugin installing " + info.filename + " to " + extracted_path)
                         #update variant version numbers on install, Cura blocks out of date variants from appearing
                        if folder is self.local_variants_path:
                            Logger.log("i", "The variant is " + extracted_path)
                            config = configparser.ConfigParser()
                            config.read(extracted_path)
                            Logger.log("i", "The sections are " + str(config.sections()))
                            config['metadata']['setting_version']=self.setvers
                            with open(extracted_path,'w') as configfile:
                                config.write(configfile)


                        restartRequired = True

            if restartRequired and self.isInstalled():
                # either way, the files are now installed, so set the prefrences value
                self._application.getPreferences().setValue("Nautilus/install_status", "installed")
                self._application.getPreferences().setValue("Nautilus/curr_version",Nautilus.version)
                Logger.log("i", "Nautilus Plugin is now installed - Please restart ")
                self._application.getPreferences().writeToFile(Resources.getStoragePath(Resources.Preferences, self._application.getApplicationName() + ".cfg"))

        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Nautilus Plugin while installing the files")
            message = Message(catalog.i18nc("@info:status", "Nautilus Plugin experienced an error installing the files"))
            message.show()




    # Uninstall the plugin files.
    def uninstallPluginFiles(self, quiet):
        Logger.log("i", "Nautilus Plugin uninstalling plugin files")
        restartRequired = False
        # remove the printer definition file
        try:
            HRNautilusDefFile = os.path.join(self.local_printer_def_path,"hydra_research_nautilus.def.json")
            if os.path.isfile(HRNautilusDefFile):
                Logger.log("i", "Nautilus Plugin removing printer definition from " + HRNautilusDefFile)
                os.remove(HRNautilusDefFile)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Nautilus Plugin while uninstalling files")

        #remove the hrfdmprinter file
        try:
            HRFDMFile = os.path.join(self.local_printer_def_path,"hrfdmprinter.def.json")
            if os.path.isfile(HRFDMFile):
                Logger.log("i", "Nautilus Plugin removing hrfdmprinter from " + HRFDMFile)
                os.remove(HRFDMFile)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Nautilus Plugin while uninstalling files")

        #remove the hydra_research_excluded_materials file
        try:
            HRExludedMaterialsFile = os.path.join(self.local_printer_def_path,"hydra_research_excluded_materials.def.json")
            if os.path.isfile(HRExludedMaterialsFile):
                Logger.log("i", "Nautilus Plugin removing excluded materials from " + HRExludedMaterialsFile)
                os.remove(HRExludedMaterialsFile)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Nautilus Plugin while uninstalling files")

        # remove the extruder definition file
        try:
            HRNautilusExtruderFile = os.path.join(self.local_printer_def_path,"hydra_research_nautilus_extruder.def.json")
            if os.path.isfile(HRNautilusExtruderFile):
                Logger.log("i", "Nautilus Plugin removing extruder definition from " + HRNautilusExtruderFile)
                os.remove(HRNautilusExtruderFile)
                restartRequired = True
        except: # Installing a new plug-in should never crash the application.
            Logger.logException("d", "An exception occurred in Nautilus Plugin while uninstalling files")

        # remove the hrfdmextruder file
        try:
            HRFDMExtruderFile = os.path.join(self.local_printer_def_path,"hrfdmextruder.def.json")
            if os.path.isfile(HRFDMExtruderFile):
                Logger.log("i", "Nautilus Plugin removing extruder definition from " + HRFDMExtruderFile)
                os.remove(HRFDMExtruderFile)
                restartRequired = True
        except: # Installing a new plug-in should never crash the application.
            Logger.logException("d", "An exception occurred in Nautilus Plugin while uninstalling files")

        # remove the material directory
        try:
            nautilusmatDir = os.path.join(self.local_materials_path,"nautilusmat")
            if os.path.isdir(nautilusmatDir):
                Logger.log("i", "Nautilus Plugin removing material files from " + nautilusmatDir)
                shutil.rmtree(nautilusmatDir)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Nautilus Plugin while uninstalling files")

        # remove the setting visibility directory
        try:
            nautilussetvisDir = os.path.join(self.local_setvis_path,"hrn_settings")
            if os.path.isdir(nautilussetvisDir):
                Logger.log("i", "Nautilus Plugin removing material files from " + nautilussetvisDir)
                shutil.rmtree(nautilussetvisDir)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Nautilus Plugin while uninstalling files")

        # remove the extruder file
        try:
            nautilusExtruder = os.path.join(self.local_extruder_path,"hydra_research_nautilus_extruder.def.json")
            if os.path.isfile(nautilusExtruder):
                Logger.log("i", "Nautilus Plugin removing extruder file from " + nautilusExtruder)
                os.remove(nautilusExtruder)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Nautilus Plugin while uninstalling files")

        # remove the platform file (on windows this doesn't work because it needs admin rights)
        try:
            nautilusSTLfile = os.path.join(self.local_meshes_path,"hydra_research_nautilus_platform.stl")
            if os.path.isfile(nautilusSTLfile):
                Logger.log("i", "Nautilus Plugin removing stl file from " + nautilusSTLfile)
                os.remove(nautilusSTLfile)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Nautilus Plugin while uninstalling files")

        # remove the folder containing the quality files
        try:
            nautilusQualityDir = os.path.join(self.local_quality_path,"nautilusquals")
            if os.path.isdir(nautilusQualityDir):
                Logger.log("i", "Nautilus Plugin removing quality files from " + nautilusQualityDir)
                shutil.rmtree(nautilusQualityDir)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Nautilus Plugin while uninstalling files")

        #remove the folder containing the intent files
        try:
            nautilusIntentDir = os.path.join(self.local_intent_path,"nautilusintent")
            if os.path.isdir(nautilusIntentDir):
                Logger.log("i", "Nautilus Plugin removing intent files from " + nautilusIntentDir)
                shutil.rmtree(nautilusIntentDir)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Nautilus Plugin while uninstalling files")

        #remove the folder containing the variant Files
        try:
            nautilusVariantsDir = os.path.join(self.local_variants_path,"nautilusvars")
            if os.path.isdir(nautilusVariantsDir):
                Logger.log("i", "Nautilus Plugin removing variants files from " + nautilusVariantsDir)
                shutil.rmtree(nautilusVariantsDir)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Nautilus Plugin while uninstalling files")

        #remove the setting visibility file
        try:
            nautilusSettingVisDir = os.path.join(self.local_setvis_path,"hrn_settings")
            if os.path.isfile(nautilusSettingVisDir):
                Logger.log("i", "Nautilus Plugin removing setting visibility files from" +nautilusSettingVisDir)
                shutil.rmtree(nautilusSettingVisDir)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d","An exception occurred in Nautilus Plugin while uninstalling files")

        # prompt the user to restart
        if restartRequired and quiet == False:
            if os.path.isfile(os.path.join(self.local_global_dir,"Hydra+Research+Nautilus.global.cfg")):
                message = Message(catalog.i18nc("@info:status","You have at least one Nautilus added into Cura. Remove it from your Preferences menu before restarting to avoid an error!"))
                message.show()
            self._application.getPreferences().setValue("Nautilus/install_status", "uninstalled")
            self._application.getPreferences().writeToFile(Resources.getStoragePath(Resources.Preferences, self._application.getApplicationName() + ".cfg"))
            message = Message(catalog.i18nc("@info:status", "Nautilus files have been uninstalled, please restart Cura to complete uninstallation."))
            message.show()
