#
# This script generates a .curapackage and a properly zipped resources folder
# for the Nautilus plugin

import os
import tempfile
from distutils.dir_util import copy_tree
import zipfile
import shutil


path = os.getcwd()
pluginPath = os.path.join('files','plugins','Nautilus')
sourcePath = os.path.join(path,'Nautilus')
resourcePath = os.path.join(path,'resources')
resourceList = os.listdir(resourcePath)
try:
    resourceList.remove('.DS_Store')
except:
    pass
resourceContainer = 'Nautilus.zip'
pluginName = 'Nautilus.curapackage'
matContainer = 'nautilusmat'
qualContainer = 'hr_nautilus'
varContainer = 'nautilus'

def filer(filepath):
    try:
        os.makedirs(filepath)
    except OSError:
        print("error creating folders for path ", str(filepath))

# Create the resources zipfile in the appropriate structure for the plugin
with tempfile.TemporaryDirectory() as configDirectory:
    with tempfile.TemporaryDirectory() as pluginDirectory:
        filer(os.path.join(pluginDirectory, pluginPath))
        for folder in resourceList:
            # sort through resources: definitions, extruders, meshes,
            # materials, quality, and variants
            file = os.path.join(resourcePath, folder)
            singletons = ['definitions', 'extruders', 'meshes']
            if os.path.basename(file) in singletons:
                copy_tree(file, configDirectory)
            elif os.path.basename(file) == 'materials':
                filer(os.path.join(configDirectory, matContainer))
                copy_tree(file,os.path.join(configDirectory, matContainer))
            elif os.path.basename(file) == 'quality':
                filer(os.path.join(configDirectory, qualContainer))
                copy_tree(file,os.path.join(configDirectory, qualContainer))
            elif os.path.basename(file) == 'variants':
                filer(os.path.join(configDirectory, varContainer))
                copy_tree(file, os.path.join(configDirectory, varContainer))

        # Zip the resources excluding useless OSX files, this could be adapted to
        # exclude useless files from other operating systems
        with zipfile.ZipFile(resourceContainer, 'w') as zipper:
            finres = os.listdir(configDirectory)
            for res in finres:
                if res != '.DS_Store' and res != 'Icon\r':
                    zipper.write(os.path.join(configDirectory, res), res)
        zipper.close()
        shutil.copy(resourceContainer, os.path.join(pluginDirectory,pluginPath))


        # include the necessary files from the root path
        copy_tree(sourcePath, os.path.join(pluginDirectory,pluginPath))
        utils = ['icon.png', 'LICENSE', 'package.json']
        for util in utils:
            shutil.copy(os.path.join(path, util), pluginDirectory)

        # zip the file as a .curapackage so it's ready to go
        with zipfile.ZipFile(pluginName, 'w') as zf:
            pluginFiles = list()
            for (dirpath, dirnames, filenames) in os.walk(pluginDirectory):
                pluginFiles += [os.path.join(dirpath, file) for file in filenames]

            for item in pluginFiles:
                if '.DS_Store' not in item:
                    zf.write(os.path.join(pluginDirectory, item), os.path.relpath(item, pluginDirectory))
        zf.close()
