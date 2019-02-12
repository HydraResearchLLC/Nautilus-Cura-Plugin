# Copyright (c) 2015 Ultimaker B.V.
# Cura is released under the terms of the LGPLv3 or higher.

from . import HRNautilus
from . import DuetRRFPlugin


from UM.i18n import i18nCatalog
catalog = i18nCatalog("cura")

def getMetaData():
    return {

    }

def register(app):
    return {"extension": [
        HRNautilus.HRNautilus(),
        DuetRRFPlugin.DuetRRFPlugin()
        ],
        "output_device":
        DuetRRFPlugin.DuetRRFPlugin()
    }
