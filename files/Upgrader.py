
import configparser
import os
import zipfile

from UM.Resources import Resources
from UM.Logger import Logger

from . import Nautilus


class Upgrader:
    def __init__(self):
        super().__init__()

    def fileList(self,fileName):
        #This function lists the all files at the path fileName without file extension
        files = list()
        #Logger.log("i","This is the path: "+str(fileName))
        for (dirpath, dirnames, filenames) in os.walk(fileName):
            files += [os.path.basename(file).split('.',1)[0] for file in filenames]
            #[Logger.log("i","!@!@!"+os.path.basename(file).split('.',1)[0]) for file in filenames]
        return files

    def diffMaker(self):
        #This function fills sets with the currently installed materials,qualities, and Variants
        #Then it searches the newly installed zipfile and fills sets with the resources to be installed
        #Finally it removes all files found in both sets so the old set only contains deprecated resources
        oldVars = set(['hrn_X_250','hrn_X_400','hrn_X_800'])#set(self.fileList(os.path.join(Resources.getStoragePath(Resources.Resources),"variants","nautilus")))
        #Logger.log("i","Number of old variants: "+str(len(oldVars)))
        oldMats = set(self.fileList(os.path.join(Resources.getStoragePath(Resources.Resources), "materials","nautilusmat")))
        oldQuals = set(self.fileList(os.path.join(Resources.getStoragePath(Resources.Resources),"quality","hr_nautilus")))

        newMats = set()
        newQuals = set()
        newVars = set()

        path = os.path.dirname(os.path.realpath(__file__))
        zipdata = os.path.join(path,"Nautilus.zip")

        with zipfile.ZipFile(zipdata, "r") as zip_ref:
            for info in zip_ref.infolist():
                #Logger.log("i","!@!  "+str(info.filename))
                if info.filename.endswith("fdm_material"):
                    matName = os.path.basename(str(info.filename))
                    #Logger.log("i","input name: "+str(matName))
                    newMats.add(matName.split('.',1)[0])
                    #Logger.log("i","Finding new Materials: "+str(matName.split('.',1)[0]))
                elif info.filename.endswith("0.inst.cfg"):
                    varName = os.path.basename(str(info.filename))
                    newVars.add(varName.split('.',1)[0])
                    #Logger.log("i", "Finding New Variants: "+str(varName.split('.',1)[0]))
                elif info.filename.endswith(".cfg"):
                    qualName = os.path.basename(str(info.filename))
                    newQuals.add(qualName.split('.',1)[0])
                    #Logger.log("i", "Finding New Quality: "+str(os.path.basename(info.filename)))

        oldMats -= newMats
        oldVars -= newVars
        oldQuals -= newQuals
        Logger.log("i","Number of changed materials: "+str(len(oldMats)))
        Logger.log("i","Number of changed quality profiles: "+str(len(oldQuals)))
        Logger.log("i","Number of changed variants: "+str(len(oldVars)))
        return oldMats, oldVars, oldQuals

    def cachePatch(self,removedFiles,configCache):
        #this function takes in cached config files and looks for deprecated Resources
        #if one is found, it replaces it with the relevant empty value for that resource
        parser = configparser.ConfigParser()
        for config in configCache:
            parser.read(config)
            #Logger.log("i","the file is: "+str(config))
            section = 'containers'
            for key,val in parser.items(section):
                #Logger.log("i","Checking value: "+str(val))
                for removedFile in removedFiles:
                    #Logger.log("i","Looking for: '"+removedFile+"'!")
                    #Logger.log("i", "In: "+str(val)+"!")
                    #Logger.log("i", "And: "+str(key)+"!")
                    if str(removedFile) in str(val) or str(removedFile) is str(val):
                        #Logger.log("i","Removing: "+str(val))
                        #Logger.log("i", "From key: "+str(key))
                        if key == '1':
                            emptyval = 'empty_quality_changes'
                        elif key == '2':
                            emptyval = 'empty_quality'
                        elif key == '3':
                            emptyval = 'empty_material'
                        elif key == '4':
                            emptyval = 'hrn_X_400'
                        else:
                            emptyval = 'huh?'
                            Logger.log("i","We've replaced a setting we shouldn't've!")
                            Logger.log("i","It's "+str(val)+" in "+str(key))
                        parser[section][key]=emptyval
                        #Logger.log("i","Replacing with: "+emptyval)
                    else:
                        continue
            with open(config, 'w') as configfile:
                parser.write(configfile)
        return


    def configFixer(self):
        #This finds all the config cache files and runs the previous two functions
        dMats, dVars, dQuals = self.diffMaker()
        if len(dMats)>0 or len(dVars)>0 or len(dQuals)>0:
            truth = True
        path = Resources.getStoragePathForType(Resources.Resources)
        Logger.log("i","Cleaning cache")
        files = []
        for (dirpath, dirnames, filenames) in os.walk(path):
            for file in filenames:
                if "autilus" in file and "autilus" not in dirpath and file.endswith(".cfg"):
                    #Logger.log("i","!!!@"+os.path.join(dirpath,file))
                    files.append(os.path.join(dirpath,file))
        self.cachePatch(dMats,files)
        self.cachePatch(dQuals,files)
        self.cachePatch(dVars,files)
        return truth
