# Copyright (c) 2015 Ultimaker B.V.
# Cura is released under the terms of the LGPLv3 or higher.

from . import Nautilus
from . import NautilusDuet


from UM.i18n import i18nCatalog
catalog = i18nCatalog("cura")

def getMetaData():
    return {

    }

def register(app):
    return {"extension": [
        Nautilus.Nautilus(),
        NautilusDuet.NautilusDuet()
        ],
        "output_device":
        NautilusDuet.NautilusDuet(),
        "machine_action":
        NautilusDuet.NautilusDuet()
    }
