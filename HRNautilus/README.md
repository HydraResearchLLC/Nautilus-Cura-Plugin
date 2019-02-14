# HRNautilus3.6
Cura plugin for Nautilus printer v 3.6

The current file structure is essentially setup as Ultimaker wants the file structure for submission to the marketplace. We strongly recommend you download the plugin from the Cura marketplace as this will streamline the process for everyone.

If you wish to manually install for any reason, a properly packaged release can be found at !!INSERTLINKHERE!!

In order to generate a release manually the file structure should be set up as follows:

HRNautilus.curapackage (This is just a zip file with the extension renamed to .curapackage)  
 icon.png  
 LICENSE  
 package.json  
 -files  
  -plugins  
   -HRNautilus  
    plugin.json  
    __init__.py  
    HRNautilus.py  
    HRNautilusprefs.qml  
    HRNautilus.zip (This is a zip archive that contains config files)
