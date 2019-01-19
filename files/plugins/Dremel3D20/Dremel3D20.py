####################################################################
# Dremel Ideabuilder 3D20 plugin for Ultimaker Cura
# A plugin to enable Cura to write .g3drem files for
# the Dremel IdeaBuilder 3D20
#
# Written by Tim Schoenmackers
# Based on the GcodeWriter plugin written by Ultimaker
#
# the GcodeWriter plugin source can be found here:
# https://github.com/Ultimaker/Cura/tree/master/plugins/GCodeWriter
#
# This plugin is released under the terms of the LGPLv3 or higher.
# The full text of the LGPLv3 License can be found here:
# https://github.com/timmehtimmeh/Cura-Dremel-3D20-Plugin/blob/master/LICENSE
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

from cura.CuraApplication import CuraApplication
from cura.Machines.QualityManager import getMachineDefinitionIDForQualitySearch

from PyQt5.QtWidgets import QApplication, QFileDialog
from PyQt5.QtGui import QPixmap, QScreen, QColor, qRgb, QImageReader, QImage, QDesktopServices
from PyQt5.QtCore import QByteArray, QBuffer, QIODevice, QRect, Qt, QSize, pyqtSlot, QObject, QUrl, pyqtSlot

#from . import G3DremHeader

catalog = i18nCatalog("cura")


class Dremel3D20(QObject, MeshWriter, Extension):
    # The version number of this plugin - please change this in all three of the following Locations:
    # 1) here
    # 2) plugin.json
    # 3) package.json
    version = "0.5.3"

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
        self.this_plugin_path=os.path.join(Resources.getStoragePath(Resources.Resources), "plugins","Dremel3D20","Dremel3D20")
        if not self._application.getPluginRegistry().isActivePlugin("Dremel3D20"):
            Logger.log("i", "Dremel3D20 Plugin is disabled")
            return #Plug-in is disabled.

        self._preferences_window = None

        self.local_meshes_path = None
        self.local_printer_def_path = None
        self.local_materials_path = None
        self.local_quality_path = None
        self.local_extruder_path = None
        self.local_variants_path = None
        Logger.log("i", "Dremel 3D20 Plugin setting up")
        self.local_meshes_path = os.path.join(Resources.getStoragePathForType(Resources.Resources), "meshes")
        self.local_printer_def_path = Resources.getStoragePath(Resources.DefinitionContainers)
        self.local_materials_path = os.path.join(Resources.getStoragePath(Resources.Resources), "materials")
        self.local_quality_path = os.path.join(Resources.getStoragePath(Resources.Resources), "quality")
        self.local_extruder_path = os.path.join(Resources.getStoragePath(Resources.Resources),"extruders")
        self.local_variants_path = os.path.join(Resources.getStoragePath(Resources.Resources), "variants")
        # Check to see if the user had installed the plugin in the main directory
        for fil in self.oldVersionInstalled():
            Logger.log("i", "Dremel 3D20 Plugin found files from previous install: " + fil)
            message = Message(catalog.i18nc("@info:status", "Old Dremel IdeaBuilder 3D20 files detected.  Please delete "+ fil))
            message.show()
            return False

        # if the plugin was never installed, then force installation
        if self._application.getPreferences().getValue("Dremel3D20/install_status") is None:
            self._application.getPreferences().addPreference("Dremel3D20/install_status", "unknown")

        # if something got messed up, force installation
        if not self.isInstalled() and self._application.getPreferences().getValue("Dremel3D20/install_status") is "installed":
            self._application.getPreferences().setValue("Dremel3D20/install_status", "unknown")

        # if it's installed, and it's listed as uninstalled, then change that to reflect the truth
        if self.isInstalled() and self._application.getPreferences().getValue("Dremel3D20/install_status") is "uninstalled":
            self._application.getPreferences().setValue("Dremel3D20/install_status", "installed")

        # if the version isn't the same, then force installation
        if self.isInstalled() and not self.versionsMatch():
            self._application.getPreferences().setValue("Dremel3D20/install_status", "unknown")

        # Check the preferences to see if the user uninstalled the files -
        # if so don't automatically install them
        if self._application.getPreferences().getValue("Dremel3D20/install_status") is "unknown":
            # if the user never installed the files, then automatically install it
            self.installPluginFiles()

        # check to see that the install succeeded - if so change the menu item options
        #if os.path.isfile(os.path.join(self.local_printer_def_path,"Dremel3D20.def.json")):
        #    Logger.log("i", "Dremel 3D20 Plugin adding menu item for uninstallation")
        #    self.addMenuItem(catalog.i18nc("@item:inmenu", "Uninstall Dremel3D20 Printer Files"), self.uninstallPluginFiles)
        #else:
        #    Logger.log("i", "Dremel 3D20 Plugin adding menu item for installation")
        #    self.addMenuItem(catalog.i18nc("@item:inmenu", "Install Dremel3D20 Printer"), self.installPluginFiles)

        self.addMenuItem(catalog.i18nc("@item:inmenu", "Preferences"), self.showPreferences)
        self.addMenuItem(catalog.i18nc("@item:inmenu", "Report Issue"), self.reportIssue)
        self.addMenuItem(catalog.i18nc("@item:inmenu", "Help "), self.showHelp)
        self.addMenuItem(catalog.i18nc("@item:inmenu", "Dremel Printer Plugin Version "+Dremel3D20.version), self.openPluginWebsite)

        # finally save the cura.cfg file
        self._application.getPreferences().writeToFile(Resources.getStoragePath(Resources.Preferences, self._application.getApplicationName() + ".cfg"))

    def createPreferencesWindow(self):
        path = os.path.join(PluginRegistry.getInstance().getPluginPath(self.getPluginId()), "Dremel3D20prefs.qml")
        Logger.log("i", "Creating Dremel3D20 preferences UI "+path)
        self._preferences_window = self._application.createQmlComponent(path, {"manager": self})

    def showPreferences(self):
        if self._preferences_window is None:
            self.createPreferencesWindow()
        self._preferences_window.show()

    def hidePreferences(self):
        if self._preferences_window is not None:
            self._preferences_window.hide()

    # function so that the preferences menu can open website the version
    @pyqtSlot()
    def openPluginWebsite(self):
        url = QUrl('https://github.com/timmehtimmeh/Cura-Dremel-3D20-Plugin/releases', QUrl.TolerantMode)
        if not QDesktopServices.openUrl(url):
            message = Message(catalog.i18nc("@info:status", "Dremel 3D20 plugin could not navigate to https://github.com/timmehtimmeh/Cura-Dremel-3D20-Plugin/releases"))
            message.show()
        return

    @pyqtSlot()
    def showHelp(self):
        url = os.path.join(PluginRegistry.getInstance().getPluginPath(self.getPluginId()), "README.pdf")
        Logger.log("i", "Dremel 3D20 Plugin opening help document: "+url)
        try:
            if not QDesktopServices.openUrl(QUrl("file:///"+url, QUrl.TolerantMode)):
                message = Message(catalog.i18nc("@info:status", "Dremel 3D20 plugin could not open help document.\n Please download it from here: https://github.com/timmehtimmeh/Cura-Dremel-3D20-Plugin/raw/cura-3.4/README.pdf"))
                message.show()
        except:
            message = Message(catalog.i18nc("@info:status", "Dremel 3D20 plugin could not open help document.\n Please download it from here: https://github.com/timmehtimmeh/Cura-Dremel-3D20-Plugin/raw/cura-3.4/README.pdf"))
            message.show()
        return

    @pyqtSlot()
    def reportIssue(self):
        Logger.log("i", "Dremel 3D20 Plugin opening issue page: https://github.com/timmehtimmeh/Cura-Dremel-3D20-Plugin/issues/new")
        try:
            if not QDesktopServices.openUrl(QUrl("https://github.com/timmehtimmeh/Cura-Dremel-3D20-Plugin/issues/new")):
                message = Message(catalog.i18nc("@info:status", "Dremel 3D20 plugin could not open https://github.com/timmehtimmeh/Cura-Dremel-3D20-Plugin/issues/new please navigate to the page and report an issue"))
                message.show()
        except:
            message = Message(catalog.i18nc("@info:status", "Dremel 3D20 plugin could not open https://github.com/timmehtimmeh/Cura-Dremel-3D20-Plugin/issues/new please navigate to the page and report an issue"))
            message.show()
        return


    def oldVersionInstalled(self):
        cura_dir=os.path.dirname(os.path.realpath(sys.argv[0]))
        dremelDefinitionFile=os.path.join(cura_dir,"resources","definitions","hydra_research_nautilus.def.json")
        dremelExtruderFile=os.path.join(cura_dir,"resources","definitions","hydra_research_nautilus_extruder.def.json")
        oldPluginPath=os.path.join(cura_dir,"resources","plugins","DremelGCodeWriter")
        dremelMaterialFolder=os.path.join(cura_dir,"resources","materials","nautilusmat")
        dremelQualityFolder=os.path.join(cura_dir,"resources","quality","dremel_3d20")
        dremelVariantsFolder=os.path.join(cura_dir,"resources","variants","nautilus")
        ret = []
        if os.path.isfile(dremelDefinitionFile):
            ret.append(dremelDefinitionFile)
        if os.path.isfile(dremelExtruderFile):
            ret.append(dremelExtruderFile)
        if os.path.isfile(dremelMaterialFolder):
            ret.append(dremelMaterialFolder)
        if os.path.isdir(dremelQualityFolder):
            ret.append(dremelQualityFolder)
        if os.path.isdir(oldPluginPath):
            ret.append(oldPluginPath)
        if os.path.isdir(dremelVariantsFolder):
            ret.append(dremelVariantsFolder)
        return ret

    # returns true if the versions match and false if they don't
    def versionsMatch(self):
        # get the currently installed plugin version number
        if self._application.getPreferences().getValue("Dremel3D20/curr_version") is None:
            self._application.getPreferences().addPreference("Dremel3D20/curr_version", "0.0.0")

        installedVersion = self._application.getPreferences().getValue("Dremel3D20/curr_version")

        if StrictVersion(installedVersion) == StrictVersion(Dremel3D20.version):
            # if the version numbers match, then return true
            Logger.log("i", "Dremel 3D20 Plugin versions match: "+installedVersion+" matches "+Dremel3D20.version)
            return True
        else:
            Logger.log("i", "Dremel 3D20 Plugin installed version: " +installedVersion+ " doesn't match this version: "+Dremel3D20.version)
            return False


    # check to see if the plugin files are all installed
    def isInstalled(self):
        dremel3D20DefFile = os.path.join(self.local_printer_def_path,"hydra_research_nautilus.def.json")
        dremelExtruderDefFile = os.path.join(self.local_extruder_path,"hydra_research_nautilus_extruder.def.json")
        dremelMatDir = os.path.join(self.local_materials_path,"nautilusmat")
        dremelQualityDir = os.path.join(self.local_quality_path,"dremel_3d20")
        dremelVariantsDir = os.path.join(self.local_quality_path,"nautilus")

        # if some files are missing then return that this plugin as not installed
        if not os.path.isfile(dremel3D20DefFile):
            Logger.log("i", "Dremel 3D20 Plugin dremel definition file is NOT installed ")
            return False
        if not os.path.isfile(dremelExtruderDefFile):
            Logger.log("i", "Dremel 3D20 Plugin dremel extruder file is NOT installed ")
            return False
        if not os.path.isfile(dremelMatDir):
            Logger.log("i", "Dremel 3D20 Plugin dremel PLA file is NOT installed ")
            return False
        if not os.path.isdir(dremelQualityDir):
            Logger.log("i", "Dremel 3D20 Plugin dremel quality files are NOT installed ")
            return False
        if not os.path.isdir(dremelVariantsDir):
            Logger.log("i", "Variant files are NOT installed ")
            return False

        # if everything is there, return True
        Logger.log("i", "Dremel 3D20 Plugin all files ARE installed")
        return True

    # install based on preference checkbox
    @pyqtSlot(bool)
    def changePluginInstallStatus(self, bInstallFiles):
        if bInstallFiles and not self.isInstalled():
            self.installPluginFiles()
        elif not bInstallFiles and self.isInstalled():
            self.uninstallPluginFiles()


    # Install the plugin files.
    def installPluginFiles(self):
        Logger.log("i", "Dremel 3D20 Plugin installing printer files")

        try:
            restartRequired = False
            zipdata = os.path.join(self.this_plugin_path,"Dremel3D20.zip")
            #zipdata = os.path.join(self._application.getPluginRegistry().getPluginPath(self.getPluginId()), "Dremel3D20.zip")
            with zipfile.ZipFile(zipdata, "r") as zip_ref:
                for info in zip_ref.infolist():
                    Logger.log("i", "Dremel 3D20 Plugin: found in zipfile: " + info.filename )
                    folder = None
                    if info.filename == "hydra_research_nautilus.def.json":
                        folder = self.local_printer_def_path
                    if info.filename == "hydra_research_nautilus_extruder.def.json":
                        folder = self.local_extruder_path
                    elif info.filename.endswith("fdm_material"):
                        folder = self.local_materials_path
                    elif info.filename.endswith("5.inst.cfg"):
                        folder = self.local_variants_path
                        Logger.log("i", "Finding Variants 1")
                    elif info.filename.endswith("0.inst.cfg"):
                        folder = self.local_variants_path
                        Logger.log("i", "Finding Variants 2")
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
                        Logger.log("i", "Dremel 3D20 Plugin installing " + info.filename + " to " + extracted_path)
                        restartRequired = True

            if restartRequired and self.isInstalled():
                # only show the message if the user called this after having already uninstalled
                if self._application.getPreferences().getValue("Dremel3D20/install_status") is not "unknown":
                    message = Message(catalog.i18nc("@info:status", "Dremel 3D20 files have been installed.  Please restart Cura to complete installation"))
                    message.show()
                # either way, the files are now installed, so set the prefrences value
                self._application.getPreferences().setValue("Dremel3D20/install_status", "installed")
                self._application.getPreferences().setValue("Dremel3D20/curr_version",Dremel3D20.version)
                Logger.log("i", "Dremel 3D20 Plugin is now installed - Please restart ")
                self._application.getPreferences().writeToFile(Resources.getStoragePath(Resources.Preferences, self._application.getApplicationName() + ".cfg"))

        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Dremel 3D20 Plugin while installing the files")
            message = Message(catalog.i18nc("@info:status", "Dremel 3D20 Plugin experienced an error installing the files"))
            message.show()




    # Uninstall the plugin files.
    def uninstallPluginFiles(self):
        Logger.log("i", "Dremel 3D20 Plugin uninstalling plugin files")
        restartRequired = False
        # remove the printer definition file
        try:
            dremel3D20DefFile = os.path.join(self.local_printer_def_path,"hydra_research_nautilus.def.json")
            if os.path.isfile(dremel3D20DefFile):
                Logger.log("i", "Dremel 3D20 Plugin removing printer definition from " + dremel3D20DefFile)
                os.remove(dremel3D20DefFile)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Dremel 3D20 Plugin while uninstalling files")

        # remove the extruder definition file
        try:
            dremel3D20ExtruderFile = os.path.join(self.local_printer_def_path,"hydra_research_nautilus_extruder.def.json")
            if os.path.isfile(dremel3D20ExtruderFile):
                Logger.log("i", "Dremel 3D20 Plugin removing extruder definition from " + dremel3D20ExtruderFile)
                os.remove(dremel3D20ExtruderFile)
                restartRequired = True
        except: # Installing a new plug-in should never crash the application.
            Logger.logException("d", "An exception occurred in Dremel 3D20 Plugin while uninstalling files")

        # remove the pla material file
        try:
            dremelPLAfile = os.path.join(self.local_materials_path,"nautilusmat")
            if os.path.isfile(dremelPLAfile):
                Logger.log("i", "Dremel 3D20 Plugin removing dremel pla file from " + dremelPLAfile)
                shutil.rmtree(dremelPLAfile)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Dremel 3D20 Plugin while uninstalling files")

        # remove the extruder file
        try:
            dremelExtruder = os.path.join(self.local_extruder_path,"hydra_research_nautilus_extruder.def.json")
            if os.path.isfile(dremelExtruder):
                Logger.log("i", "Dremel 3D20 Plugin removing dremel extruder file from " + dremelExtruder)
                os.remove(dremelExtruder)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Dremel 3D20 Plugin while uninstalling files")

        # remove the platform file (on windows this doesn't work because it needs admin rights)
        try:
            dremelSTLfile = os.path.join(self.local_meshes_path,"hydra_research_nautilus_platform.stl")
            if os.path.isfile(dremelSTLfile):
                Logger.log("i", "Dremel 3D20 Plugin removing dremel stl file from " + dremelSTLfile)
                os.remove(dremelSTLfile)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Dremel 3D20 Plugin while uninstalling files")

        # remove the folder containing the quality files
        try:
            dremelQualityDir = os.path.join(self.local_quality_path,"dremel_3d20")
            if os.path.isdir(dremelQualityDir):
                Logger.log("i", "Dremel 3D20 Plugin removing dremel quality files from " + dremelQualityDir)
                shutil.rmtree(dremelQualityDir)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Dremel 3D20 Plugin while uninstalling files")

        #remove the folder containing the variant Files
        try:
            dremelVariantsDir = os.path.join(self.local_variants_path,"nautilus")
            if os.path.isdir(dremelVariantsDir):
                Logger.log("i", "Dremel 3D20 Plugin removing dremel variants files from " + dremelVariantsDir)
                shutil.rmtree(dremelVariantsDir)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Dremel 3D20 Plugin while uninstalling files")

        # prompt the user to restart
        if restartRequired:
            self._application.getPreferences().setValue("Dremel3D20/install_status", "uninstalled")
            self._application.getPreferences().writeToFile(Resources.getStoragePath(Resources.Preferences, self._application.getApplicationName() + ".cfg"))
            message = Message(catalog.i18nc("@info:status", "Dremel 3D20 files have been uninstalled.  Please restart Cura to complete uninstallation"))
            message.show()
