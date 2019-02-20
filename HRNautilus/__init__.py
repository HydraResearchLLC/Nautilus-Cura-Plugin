from . import HRNautilus
from . import NautilusDuet

def getMetaData():
    return {}

def register(app):
    return {"extension": [
        HRNautilus.HRNautilus(),
        NautilusDuet.NautilusDuet()
        ],
        "output_device":
        NautilusDuet.NautilusDuet()
    }
