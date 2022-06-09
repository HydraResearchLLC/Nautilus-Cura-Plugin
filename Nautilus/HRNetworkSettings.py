import json

from UM.Logger import Logger

from cura.CuraApplication import CuraApplication

HRNETWORK_SETTINGS = "Nautilus/printers"

def _load_prefs():
    application = CuraApplication.getInstance()
    global_container_stack = application.getGlobalContainerStack()
    if not global_container_stack:
        Logger.log('e', 'no global container stack')
        return {}, None
    printer_id = global_container_stack.getId()
    p = application.getPreferences()
    s = json.loads(p.getValue(HRNETWORK_SETTINGS))
    return s, printer_id

def init_settings():
    application = CuraApplication.getInstance()
    p = application.getPreferences()
    p.addPreference(HRNETWORK_SETTINGS, json.dumps({}))

def get_config():
    s, printer_id = _load_prefs()
    if printer_id in s:
        return s[printer_id]
    return {}

def save_config(url, printer_password, http_user, http_password):
    s, printer_id = _load_prefs()
    Logger.log('d','saving printer '+printer_id)
    s[printer_id] = {
            "url": url,
            "printer_password": printer_password,
            "http_user": http_user,
            "http_password": http_password,
        }
    application = CuraApplication.getInstance()
    p = application.getPreferences()
    p.setValue(HRNETWORK_SETTINGS, json.dumps(s))
    return s

def delete_config(printer_id=None):
    s, active_printer_id = _load_prefs()
    if not printer_id:
        printer_id = active_printer_id
    if printer_id in s:
        del s[printer_id]
        application = CuraApplication.getInstance()
        p = application.getPreferences()
        p.setValue(HRNETWORK_SETTINGS, json.dumps(s))
        return True
    return False
