# Copyright (c) 2015 Ultimaker B.V.
# Cura is released under the terms of the LGPLv3 or higher.

import os
import json
from UM.Logger import Logger

from . import Nautilus, HRNetworkPlugin, HRNetworkAction, NautilusUpdate


from UM.i18n import i18nCatalog
catalog = i18nCatalog("cura")

def getMetaData():
    return {

    }


def register(app):
    plugin_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugin.json")
    try:
        with open(plugin_file_path) as plugin_file:
            plugin_info = json.load(plugin_file)
            Logger.log("d", "HydraResearchPlugin version: {}".format(plugin_info["version"]))
    except:
        Logger.log("w", "HydraResearchPlugin failed to get version information!")

    return {
        "extension": [Nautilus.Nautilus(), HRNetworkPlugin.HRNetworkPlugin()],
        "output_device": [HRNetworkPlugin.HRNetworkPlugin(), NautilusUpdate.NautilusUpdate()],
        "machine_action": [HRNetworkAction.HRNetworkAction()]
    }
