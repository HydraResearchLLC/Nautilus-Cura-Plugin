import os
import tempfile
from distutils.dir_util import copy_tree
import zipfile
import shutil


path = os.getcwd()
plugpath = os.path.join(path,'plugin','files','plugins','Nautilus')
basepath = os.path.join(path,'plugin')
sourcepath = os.path.join(path,'Nautilus')
configpath = os.path.join(path,'resources')
resources = os.listdir(configpath)
resources.remove('.DS_Store')

def filer(filepath):
    try:
        os.makedirs(filepath)
    except OSError:
        print("error creating folders for path ", str(filepath))


filer(plugpath)

with tempfile.TemporaryDirectory() as directory:
    for folder in resources:
        file = os.path.join(configpath,folder)
        if os.path.basename(file) == 'definitions' or os.path.basename(file) == 'extruders' or os.path.basename(file) == 'meshes':
            copy_tree(file,directory)
        elif os.path.basename(file) == 'materials':
            filer(os.path.join(directory,'nautilusmat'))
            copy_tree(file,os.path.join(directory,'nautilusmat'))
        elif os.path.basename(file) == 'quality':
            filer(os.path.join(directory,'hr_nautilus'))
            copy_tree(file,os.path.join(directory,'hr_nautilus'))
        elif os.path.basename(file) == 'variants':
            filer(os.path.join(directory,'nautilus'))
            copy_tree(file,os.path.join(directory,'nautilus'))
    with zipfile.ZipFile('Nautilus.zip','w') as zipper:
        finres = os.listdir(directory)
        for res in finres:
            if res != '.DS_Store' and res != 'Icon\r':
                zipper.write(os.path.join(directory,res),res)
    zipper.close()
    shutil.copy2(os.path.join(path,'Nautilus.zip'),plugpath)
    os.remove(os.path.join(path,'Nautilus.zip'))

copy_tree(sourcepath,plugpath)
utils = ['icon.png','LICENSE','package.json']
for util in utils:
    shutil.copy2(os.path.join(path,util),basepath)

with zipfile.ZipFile('Nautilus.curapackage','w') as zf:
    pluginfiles = os.listdir(basepath)
    for item in pluginfiles:
        if item != '.DS_Store':
            zf.write(os.path.join(basepath,item),item)
zf.close()
shutil.rmtree(basepath)
