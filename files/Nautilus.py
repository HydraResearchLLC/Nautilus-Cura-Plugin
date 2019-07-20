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
    version = "1.0.1"

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

        self.local_meshes_path = None
        self.local_printer_def_path = None
        self.local_materials_path = None
        self.local_quality_path = None
        self.local_extruder_path = None
        self.local_variants_path = None
        self.local_setvis_path = None
        self.local_global_dir = None
        Logger.log("i", "Nautilus Plugin setting up")
        self.local_meshes_path = os.path.join(Resources.getStoragePathForType(Resources.Resources), "meshes")
        self.local_printer_def_path = Resources.getStoragePath(Resources.DefinitionContainers)#os.path.join(Resources.getStoragePath(Resources.Resources),"definitions")
        self.local_materials_path = os.path.join(Resources.getStoragePath(Resources.Resources), "materials")
        self.local_quality_path = os.path.join(Resources.getStoragePath(Resources.Resources), "quality")
        self.local_extruder_path = os.path.join(Resources.getStoragePath(Resources.Resources),"extruders")
        self.local_variants_path = os.path.join(Resources.getStoragePath(Resources.Resources), "variants")
        self.local_setvis_path = os.path.join(Resources.getStoragePath(Resources.Resources), "setting_visibility")
        self.local_global_dir = os.path.join(Resources.getStoragePath(Resources.Resources),"machine_instances")
        # Check to see if the user had installed the plugin in the main directory
        """for fil in self.oldVersionInstalled():
            Logger.log("i", "Nautilus Plugin found files from previous install: " + fil)
            message = Message(catalog.i18nc("@info:status", "Old Nautilus files detected.  Please delete "+ fil))
            message.show()"""

        # if the plugin was never installed, then force installation
        if self._application.getPreferences().getValue("Nautilus/install_status") is None:
            self._application.getPreferences().addPreference("Nautilus/install_status", "unknown")
            Logger.log("i","1")

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



        Duet=NautilusDuet.NautilusDuet()
        self.addMenuItem(catalog.i18nc("@item:inmenu","Nautilus Connections"), Duet.showSettingsDialog)
        self.addMenuItem(catalog.i18nc("@item:inmenu", "Preferences"), self.showPreferences)

        # finally save the cura.cfg file
        self._application.getPreferences().writeToFile(Resources.getStoragePath(Resources.Preferences, self._application.getApplicationName() + ".cfg"))

    def createPreferencesWindow(self):
        path = os.path.join(PluginRegistry.getInstance().getPluginPath(self.getPluginId()), "Nautilusprefs.qml")
        Logger.log("i", "Creating Nautilus preferences UI "+path)
        self._preferences_window = self._application.createQmlComponent(path, {"manager": self})

    def showPreferences(self):
        if self._preferences_window is None:
            self.createPreferencesWindow()
            statuss=self._application.getPreferences().getValue("Nautilus/install_status")
        self._preferences_window.show()

    def hidePreferences(self):
        if self._preferences_window is not None:
            self._preferences_window.hide()

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

    @pyqtProperty(str)
    def getVersion(self):
        numba = Nautilus.version
        Logger.log("i","Nailed it!"+numba)
        return str(numba)

    def oldVersionInstalled(self):
        cura_dir=Resources.getStoragePathForType(Resources.Resources)
        Logger.log("i", "The Nautilus plugin for cura_dir is: " +str(cura_dir))
        nautilusDefinitionFile=os.path.join(cura_dir,"definitions","hydra_research_nautilus.def.json")
        nautilusExtruderFile=os.path.join(cura_dir,"extruders","hydra_research_nautilus_extruder.def.json")
        oldPluginPath=os.path.join(cura_dir,"plugins","Nautilus")
        nautilusMaterialFolder=os.path.join(cura_dir,"materials","nautilusmat")
        nautilusQualityFolder=os.path.join(cura_dir,"quality","nautilusquals")
        nautilusVariantsFolder=os.path.join(cura_dir,"variants","nautilusvars")
        nautilusSetVisFolder=os.path.join(cura_dir,"setting_visibility","hrn_settings")
        ret = []
        if os.path.isfile(nautilusDefinitionFile):
            ret.append(nautilusDefinitionFile)
        if os.path.isfile(nautilusExtruderFile):
            ret.append(nautilusExtruderFile)
        if os.path.isfile(nautilusMaterialFolder):
            ret.append(nautilusMaterialFolder)
        if os.path.isdir(nautilusQualityFolder):
            ret.append(nautilusQualityFolder)
        if os.path.isdir(oldPluginPath):
            ret.append(oldPluginPath)
        if os.path.isdir(nautilusVariantsFolder):
            ret.append(nautilusVariantsFolder)
        if os.path.isfile(nautilusSetVisFolder):
            ret.append(nautilusSetVisFile)
        Logger.log("i", "Nautilus Plugin found files from previous install: " + str(ret))
        return ret

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


    # check to see if the plugin files are all installed
    def isInstalled(self):
        HRNautilusDefFile = os.path.join(self.local_printer_def_path,"hydra_research_nautilus.def.json")
        nautilusExtruderDefFile = os.path.join(self.local_extruder_path,"hydra_research_nautilus_extruder.def.json")
        nautilusMatDir = os.path.join(self.local_materials_path,"nautilusmat")
        nautilusQualityDir = os.path.join(self.local_quality_path,"nautilusquals")
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


    # Install the plugin files.
    def installPluginFiles(self):
        Logger.log("i", "Nautilus Plugin installing printer files")
        upper = Upgrader.Upgrader()
        value = upper.configFixer()
        if value:
            self.uninstallPluginFiles(value)
        try:
            restartRequired = False
            zipdata = os.path.join(self.this_plugin_path,"Nautilus.zip")
            Logger.log("i","Nautilus Plugin installing from: " + zipdata)

            with zipfile.ZipFile(zipdata, "r") as zip_ref:
                for info in zip_ref.infolist():
                    Logger.log("i", "Nautilus Plugin: found in zipfile: " + info.filename )
                    folder = None
                    if info.filename == "hydra_research_nautilus.def.json":
                        folder = self.local_printer_def_path
                    elif info.filename == "hydra_research_nautilus_extruder.def.json":
                        folder = self.local_extruder_path
                    elif info.filename.endswith("nautilus.cfg"):
                        folder = self.local_setvis_path
                    elif info.filename.endswith("fdm_material"):
                        folder = self.local_materials_path
                    elif info.filename.endswith("0.inst.cfg"):
                        folder = self.local_variants_path
                        Logger.log("i", "Finding Variants")
                    elif info.filename.endswith(".cfg"):
                        folder = self.local_quality_path
                        Logger.log("i", "Finding Quality")
                    elif info.filename.endswith(".stl"):
                        folder = self.local_meshes_path
                        if not os.path.exists(folder): #Cura doesn't create this by itself. We may have to.
                            os.mkdir(folder)

                    if folder is not None:
                        extracted_path = zip_ref.extract(info.filename, path = folder)
                        permissions = os.stat(extracted_path).st_mode
                        os.chmod(extracted_path, permissions | stat.S_IEXEC) #Make these files executable.
                        Logger.log("i", "Nautilus Plugin installing " + info.filename + " to " + extracted_path)
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

        # remove the extruder definition file
        try:
            HRNautilusExtruderFile = os.path.join(self.local_printer_def_path,"hydra_research_nautilus_extruder.def.json")
            if os.path.isfile(HRNautilusExtruderFile):
                Logger.log("i", "Nautilus Plugin removing extruder definition from " + HRNautilusExtruderFile)
                os.remove(HRNautilusExtruderFile)
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
            nautilusQualityDir = os.path.join(self.local_quality_path,"hr_nautilus")
            if os.path.isdir(nautilusQualityDir):
                Logger.log("i", "Nautilus Plugin removing quality files from " + nautilusQualityDir)
                shutil.rmtree(nautilusQualityDir)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Nautilus Plugin while uninstalling files")

        #remove the folder containing the variant Files
        try:
            nautilusVariantsDir = os.path.join(self.local_variants_path,"nautilus")
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
