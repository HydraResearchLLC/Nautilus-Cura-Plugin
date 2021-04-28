#
# This script generates a .curapackage and a properly zipped resources folder
# for the Nautilus plugin

import os
import tempfile
from distutils.dir_util import copy_tree
import zipfile
import shutil


path = os.path.dirname(os.path.realpath(__file__))
resourceContainer = os.path.join(path,'Nautilus.zip')
releaseZip = os.path.join(path,'NautilusRelease.zip')
pluginName = 'Nautilus'
matContainer = 'nautilusmat'
qualContainer = 'nautilusquals'
intentContainer = 'nautilusintent'
varContainer = 'nautilusvars'
setvisContainer = 'hrn_settings'
pluginPath = os.path.join('files','plugins',pluginName)
ultimakerReleasePath = os.path.join(path, pluginName)
sourcePath = os.path.join(path,'files')
resourcePath = os.path.join(path,'resources')
resourceList = os.listdir(resourcePath)
try:
    resourceList.remove('.DS_Store')
except:
    pass

def filer(filePath):
    try:
        os.makedirs(filePath)
    except OSError:
        print("error creating folders for path ", str(filePath))

def fileList(fileName):
    files = list()
    for (dirpath, dirnames, filenames) in os.walk(fileName):
        files += [os.path.join(dirpath, file) for file in filenames]
    return files

print("Do you want intent profiles? y or n ")
flag = str(input())

# Create the resources temp directory in the appropriate structure for the plugin
with tempfile.TemporaryDirectory() as configDirectory:
    # Create the plugin temp directory
    with tempfile.TemporaryDirectory() as pluginDirectory:
        filer(os.path.join(pluginDirectory, pluginPath))
        # Build Resources zip
        for folder in resourceList:
            # sort through resources: definitions, extruders, meshes,
            # materials, quality, and variants
            file = os.path.join(resourcePath, folder)
            singletons = ['definitions', 'extruders', 'meshes']
            if os.path.basename(file) in singletons:
                copy_tree(file, configDirectory)
            elif os.path.basename(file) == 'materials':
                filer(os.path.join(configDirectory, matContainer))
                matList = fileList(file)
                mats = (mat for mat in matList if mat.endswith('.fdm_material'))
                for mat in mats:
                    shutil.copy(mat, os.path.join(configDirectory, matContainer))
            elif os.path.basename(file) == 'quality':
                filer(os.path.join(configDirectory, qualContainer))
                qualList = fileList(file)
                quals = (qual for qual in qualList if qual.endswith('.inst.cfg'))
                for qual in quals:
                    shutil.copy(qual, os.path.join(configDirectory, qualContainer))
            elif os.path.basename(file) == 'variants':
                filer(os.path.join(configDirectory, varContainer))
                varList = fileList(file)
                vars = (var for var in varList if var.endswith('.inst.cfg'))
                for var in vars:
                    shutil.copy(var, os.path.join(configDirectory, varContainer))
            elif os.path.basename(file) == 'setting_visibility':
                filer(os.path.join(configDirectory, setvisContainer))
                setvisList = fileList(file)
                settings = (set for set in setvisList if set.endswith('.cfg'))
                for set in settings:
                    shutil.copy(set,os.path.join(configDirectory, setvisContainer))
            elif os.path.basename(file) == 'intent':
                if "y" in flag:
                    filer(os.path.join(configDirectory,intentContainer))
                    intentList = fileList(file)
                    intents = (intent for intent in intentList if intent.endswith('.inst.cfg'))
                    for intent in intents:
                        shutil.copy(intent,os.path.join(configDirectory,intentContainer))
                elif "n" in flag:
                    print("No intents ")
                else:
                    print("something went wrong, neither flag occured")



        # Zip the resources excluding useless OSX files, this could be adapted to
        # exclude useless files from other operating systems
        with zipfile.ZipFile(resourceContainer, 'w') as zipper:
            finalResources = fileList(configDirectory)
            for res in finalResources:
                if res != '.DS_Store' and 'Icon' not in res:
                    zipper.write(os.path.join(configDirectory, res), os.path.relpath(res,configDirectory))
        zipper.close()
        #!!change V line to call resource zip something different
        shutil.copy(resourceContainer, os.path.join(pluginDirectory,pluginPath))
        filer(ultimakerReleasePath)
        shutil.copy(resourceContainer, ultimakerReleasePath)


        # include the necessary files from the root path
        copy_tree(sourcePath, os.path.join(pluginDirectory,pluginPath))
        copy_tree(sourcePath, ultimakerReleasePath)
        utils = ['icon.png', 'LICENSE', 'package.json']
        for util in utils:
            shutil.copy(os.path.join(path, util), pluginDirectory)

        # zip the file as a .curapackage so it's ready to go
        with zipfile.ZipFile(os.path.join(path, pluginName+'.curapackage'), 'w') as zf:
            pluginFiles = fileList(pluginDirectory)
            # add everything relevant
            for item in pluginFiles:
                if '.DS_Store' not in item:
                    zf.write(os.path.join(pluginDirectory, item), os.path.relpath(item, pluginDirectory))
                    shutil.copy(item,ultimakerReleasePath)
        zf.close()
        print("Update version numbers before release!")

        #file for release zip
        with zipfile.ZipFile(releaseZip,'w') as zippee:
            releaseFiles = fileList(ultimakerReleasePath)
            for item in releaseFiles:
                if '.DS_Store' not in item:
                    zippee.write(os.path.join(ultimakerReleasePath,item),os.path.relpath(item,ultimakerReleasePath))
        zippee.close()

        #shutil.rmtree(ultimakerReleasePath)
