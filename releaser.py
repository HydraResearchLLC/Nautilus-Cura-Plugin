import os
import tempfile
from distutils.dir_util import copy_tree
import zipfile
import shutil


path = os.getcwd()
pluginPath = os.path.join(path,'plugin','files','plugins','Nautilus')
basePath = os.path.join(path,'plugin')
sourcePath = os.path.join(path,'Nautilus')
resourcePath = os.path.join(path,'resources')
resourceList = os.listdir(resourcePath)
resourceList.remove('.DS_Store')
resourceContainer = 'Nautilus.zip'
pluginName = 'Nautilus.curapackage'
matContainer = 'nautilusmat'
qualContainer = 'hr_nautilus'
varContainer = 'nautilus'

filer(pluginPath)

def filer(filepath):
    try:
        os.makedirs(filepath)
    except OSError:
        print("error creating folders for path ", str(filepath))

#Create the resources zipfile in the appropriate structure for the plugin
with tempfile.TemporaryDirectory() as directory:
    for folder in resourceList:
        #sort through resources
        file = os.path.join(resourcePath, folder)
        if os.path.basename(file) == 'definitions' or os.path.basename(file) == 'extruders' or os.path.basename(file) == 'meshes':
            copy_tree(file, directory)
        elif os.path.basename(file) == 'materials':
            filer(os.path.join(directory, matContainer))
            copy_tree(file,os.path.join(directory, matContainer))
        elif os.path.basename(file) == 'quality':
            filer(os.path.join(directory, qualContainer))
            copy_tree(file,os.path.join(directory, qualContainer))
        elif os.path.basename(file) == 'variants':
            filer(os.path.join(directory, varContainer))
            copy_tree(file, os.path.join(directory, varContainer))

    #Zip the resources excluding useless OSX files, this could be adapted to
    #exclude useless files from other operating systems
    with zipfile.ZipFile(resourceContainer, 'w') as zipper:
        finres = os.listdir(directory)
        for res in finres:
            if res != '.DS_Store' and res != 'Icon\r':
                zipper.write(os.path.join(directory, res), res)
    zipper.close()
    shutil.copy2(os.path.join(path, resourceContainer), pluginPath)
    os.remove(os.path.join(path, resourceContainer))

#include the necessary files from the root path
copy_tree(sourcePath, pluginPath)
utils = ['icon.png', 'LICENSE', 'package.json']
for util in utils:
    shutil.copy2(os.path.join(path,util),basePath)

#zip the file as a .curapackage so it's ready to go
with zipfile.ZipFile(pluginName, 'w') as zf:
    pluginFiles = os.listdir(basePath)
    for item in pluginFiles:
        if item != '.DS_Store':
            zf.write(os.path.join(basePath, item), item)
zf.close()
shutil.rmtree(basePath)
