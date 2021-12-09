import os.path
import datetime
import base64
import urllib
import json
from io import StringIO
from time import time, sleep
from typing import cast
from enum import Enum

from PyQt5 import QtNetwork
from PyQt5.QtNetwork import QNetworkReply

from PyQt5.QtCore import QFile, QUrl, QObject, QCoreApplication, QByteArray, QTimer, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtQml import QQmlComponent, QQmlContext

from cura.CuraApplication import CuraApplication

from UM.Application import Application
from UM.Logger import Logger
from UM.Message import Message
from UM.Mesh.MeshWriter import MeshWriter
from UM.PluginRegistry import PluginRegistry
from UM.OutputDevice.OutputDevice import OutputDevice
from UM.OutputDevice import OutputDeviceError
from UM.i18n import i18nCatalog
catalog = i18nCatalog("cura")


class OutputStage(Enum):
    ready = 0
    writing = 1

class HRNetworkDeviceType(Enum):
    upload = 0


class HRNetworkConfigureOutputDevice(OutputDevice):
    def __init__(self) -> None:
        super().__init__("hrnetwork-configure")
        self.setShortDescription("Send to Printer")
        self.setDescription("Add a Networked Printer")
        self.setPriority(5)

    def requestWrite(self, node, fileName=None, *args, **kwargs):
        msg = (
            "To configure your Hydra Research printer go to:\n"
            "→ Cura Preferences\n"
            "→ Printers\n"
            "→ activate and select your printer\n"
            "→ click on 'Connect via Network'\n"
            "→ enter printer connection information\n"
            "→ click 'Save Config'\n"
        )
        message = Message(
            msg,
            lifetime=0,
            title="Configure your connection in Cura Preferences!",
        )
        message.show()
        self.writeSuccess.emit(self)


class HRNetworkOutputDevice(OutputDevice):
    def __init__(self, settings, device_type):
        self._name_id = "hrnetwork-{}".format(device_type.name)
        super().__init__(self._name_id)

        self._url = settings["url"]
        self._printer_password = settings["printer_password"]
        self._http_user = settings["http_user"]
        self._http_password = settings["http_password"]

        self.application = CuraApplication.getInstance()
        global_container_stack = self.application.getGlobalContainerStack()
        self._name = global_container_stack.getName()

        self._device_type = device_type
        if device_type == HRNetworkDeviceType.upload:
            description = catalog.i18nc("@action:button", "Send to {0}").format(self._name)
            Logger.log('i', 'upload button is for '+self._name)
            priority = 10
        else:
            Logger.log("e", "Device Type is not upload")
            assert False

        self.setShortDescription(description)
        self.setDescription(description)
        self.setPriority(priority)

        self._stage = OutputStage.ready
        self._device_type = device_type
        self._stream = None
        self._message = None

        self._use_rrf_http_api = True # by default we try to connect to the RRF HTTP API via rr_connect

        Logger.log("d",
            "New {} HRNetworkOutputDevice created | URL: {} | Printer password: {} | HTTP Basic Auth: user:{}, password:{}".format(
            self._name_id,
            self._url,
            "set" if self._printer_password else "<empty>",
            self._http_user if self._http_user else "<empty>",
            "set" if self._http_password else "<empty>",
        ))

        self._resetState()

    def _timestamp(self):
        return ("time", datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))

    def _send(self, command, query=None, next_stage=None, data=None, on_error=None, method='POST'):
        url = self._url + command

        if not query:
            query = dict()
        enc_query = urllib.parse.urlencode(query, quote_via=urllib.parse.quote)
        if enc_query:
            url += '?' + enc_query

        headers = {
            'User-Agent': 'Cura Plugin Hydra Research',
            'Accept': 'application/json, text/javascript',
            'Connection': 'keep-alive',
        }

        if self._http_user and self._http_password:
            auth = "{}:{}".format(self._http_user, self._http_password).encode()
            headers['Authorization'] = 'Basic ' + base64.b64encode(auth)

        if data:
            headers['Content-Type'] = 'application/octet-stream'
            if method == 'PUT':
                self.application.getHttpRequestManager().put(
                    url,
                    headers,
                    data,
                    callback=next_stage,
                    error_callback=on_error if on_error else self._onNetworkError,
                    upload_progress_callback=self._onUploadProgress,
                )
            else:
                self.application.getHttpRequestManager().post(
                    url,
                    headers,
                    data,
                    callback=next_stage,
                    error_callback=on_error if on_error else self._onNetworkError,
                    upload_progress_callback=self._onUploadProgress,
                )
        else:
            self.application.getHttpRequestManager().get(
                url,
                headers,
                callback=next_stage,
                error_callback=on_error if on_error else self._onNetworkError,
            )

    def requestWrite(self, node, fileName=None, *args, **kwargs):
        if self._stage != OutputStage.ready:
            raise OutputDeviceError.DeviceBusyError()

        if fileName:
            Logger.log('d', 'given fn is '+fileName)
            fileName = self.nameMaker()
        else:
            fileName = "%s" % Application.getInstance().getPrintInformation().jobName
        self._fileName = fileName

        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qml', 'UploadFilename.qml')
        self._dialog = CuraApplication.getInstance().createQmlComponent(path, {"manager": self})
        self._dialog.textChanged.connect(self.onFilenameChanged)
        self._dialog.accepted.connect(self.onFilenameAccepted)
        self._dialog.show()
        self._dialog.findChild(QObject, "nameField").setProperty('text', self._fileName)
        self._dialog.findChild(QObject, "nameField").select(0, self.nameLen)
        self._dialog.findChild(QObject, "nameField").setProperty('focus', True)

    def nameMaker(self):
        base = Application.getInstance().getPrintInformation().baseName
        Logger.log('d','base is '+ base)
        try:
            mat1 = Application.getInstance().getExtruderManager().getActiveExtruderStacks()[0].getProperty("material_name","value")
            mat2 = Application.getInstance().getExtruderManager().getActiveExtruderStacks()[1].getProperty("material_name","value")
            mat = mat1+"+"+mat2
        except:
            mat = Application.getInstance().getExtruderManager().getActiveExtruderStacks()[0].getProperty("material_name","value")

        noz = str(Application.getInstance().getExtruderManager().getActiveExtruderStacks()[0].getProperty("machine_nozzle_size","value"))
        suffix = "-" +  mat + "-" + noz
        #layerheight = Application.getInstance().getExtruderManager().getActiveExtruderStacks()[0].getProperty("material_name","value")#str(Application.getInstance().getMachineManager().activeMachine.getProperty("material_name", "value"))
        forbidden_characters = "\"'´`<>()[]?*\,;:&%#$!"
        for forbidden_character in forbidden_characters:
            if forbidden_character in suffix:
                suffix.replace(forbidden_character,"")
            if forbidden_character in base:
                base.replace(forbidden_character,"")
        self.nameLen = len(base) if len(base)<25-(len(mat)+len(noz)+2) else 25-(len(mat)+len(noz)+2)
        fileName = base[0:self.nameLen] + suffix
        Logger.log('d',"fn is "+str(len(fileName))+" characters long")
        return fileName

    def onFilenameChanged(self):
        fileName = self._dialog.findChild(QObject, "nameField").property('text').strip()

        forbidden_characters = "\"'´`<>()[]?*\,;:&%#$!"
        for forbidden_character in forbidden_characters:
            if forbidden_character in fileName:
                self._dialog.setProperty('validName', False)
                self._dialog.setProperty('validationError', 'Filename cannot contain {}'.format(forbidden_characters))
                return

        if fileName == '.' or fileName == '..':
            self._dialog.setProperty('validName', False)
            self._dialog.setProperty('validationError', 'Filename cannot be "." or ".."')
            return

        self._dialog.setProperty('validName', len(fileName) > 0)
        self._dialog.setProperty('validationError', 'Filename too short')

    def onFilenameAccepted(self):
        self._fileName = self._dialog.findChild(QObject, "nameField").property('text').strip()
        if not self._fileName.endswith('gcode'):
            self._fileName += '.gcode'
        Logger.log("d", "Filename set to: " + self._fileName)

        self._dialog.deleteLater()

        # create the temp file for the gcode
        self._stream = StringIO()
        self._stage = OutputStage.writing
        self.writeStarted.emit(self)

        # show a progress message
        self._message = Message(catalog.i18nc("@info:progress", "Uploading to {}...").format(self._name), 0, False, -1)
        self._message.show()

        Logger.log("d", "Loading gcode...")

        # get the g-code through the GCodeWrite plugin
        # this serializes the actual scene and should produce the same output as "Save to File"
        gcode_writer = cast(MeshWriter, PluginRegistry.getInstance().getPluginObject("GCodeWriter"))
        success = gcode_writer.write(self._stream, None)
        if not success:
            Logger.log("e", "GCodeWrite failed.")
            return

        # start
        Logger.log("d", "Connecting...")
        self._send('rr_connect',
            query=[("password", self._printer_password), self._timestamp()],
            next_stage=self.onUploadReady,
            on_error=self._check_duet3_sbc,
        )

    def _check_duet3_sbc(self, reply, error):
        Logger.log("d", "rr_connect failed with error " + str(error))
        if error == QNetworkReply.ContentNotFoundError:
            Logger.log("d", "error indicates Duet3+SBC - let's try the DuetSoftwareFramework API instead...")
            self._use_rrf_http_api = False  # let's try the newer DuetSoftwareFramework for Duet3+SBC API instead
            self._send('machine/status',
                next_stage=self.onUploadReady
            )
        else:
            self._onNetworkError(reply, error)

    def onUploadReady(self, reply):
        if self._stage != OutputStage.writing:
            return
        if reply.error() != QNetworkReply.NoError:
            Logger.log("d", "Stopping due to reply error: " + reply.error())
            return

        Logger.log("d", "Uploading...")

        self._stream.seek(0)
        self._postData = QByteArray()
        self._postData.append(self._stream.getvalue().encode())

        if self._use_rrf_http_api:
            self._send('rr_upload',
                query=[("name", "0:/gcodes/" + self._fileName), self._timestamp()],
                next_stage=self.onUploadDone,
                data=self._postData,
            )
        else:
            self._send('machine/file/gcodes/' + self._fileName,
                next_stage=self.onUploadDone,
                data=self._postData,
                method='PUT',
            )

    def onUploadDone(self, reply):
        if self._stage != OutputStage.writing:
            return
        if reply.error() != QNetworkReply.NoError:
            Logger.log("d", "Stopping due to reply error: " + reply.error())
            return

        Logger.log("d", "Upload done")

        self._stream.close()
        self._stream = None

        if self._device_type == HRNetworkDeviceType.upload:
            if self._use_rrf_http_api:
                self._send('rr_disconnect')
            if self._message:
                self._message.hide()
                self._message = None

            text = "Uploaded file {} to {}.".format(os.path.basename(self._fileName), self._name)
            self._message = Message(catalog.i18nc("@info:status", text), 0, False)
            self._message.addAction("open_browser", catalog.i18nc("@action:button", "Open Browser"), "globe", catalog.i18nc("@info:tooltip", "Open browser to DuetWebControl."))
            self._message.actionTriggered.connect(self._onMessageActionTriggered)
            self._message.show()

            self.writeSuccess.emit(self)
            self._resetState()
        else:
            Logger.log("e", "Device Type is not upload!!")

    def onReadyToPrint(self):
        if self._stage != OutputStage.writing:
            return

        Logger.log("d", "Ready to print")

        gcode = 'M32 "0:/gcodes/' + self._fileName + '"'
        Logger.log("d", "Sending gcode:" + gcode)
        if self._use_rrf_http_api:
            self._send('rr_gcode',
                query=[("gcode", gcode)],
                next_stage=self.onPrintStarted,
            )
        else:
            self._send('machine/code',
                data=gcode.encode(),
                next_stage=self.onPrintStarted,
            )

    def onPrintStarted(self, reply):
        if self._stage != OutputStage.writing:
            return
        if reply.error() != QNetworkReply.NoError:
            Logger.log("d", "Stopping due to reply error: " + reply.error())
            return

        Logger.log("d", "Print started")

        if self._use_rrf_http_api:
            self._send('rr_disconnect')
        if self._message:
            self._message.hide()
            self._message = None

        text = "Print started on {} with file {}.".format(self._name, self._fileName)
        self._message = Message(catalog.i18nc("@info:status", text), 0, False)
        self._message.addAction("open_browser", catalog.i18nc("@action:button", "Open Browser"), "globe", catalog.i18nc("@info:tooltip", "Open browser to DuetWebControl."))
        self._message.actionTriggered.connect(self._onMessageActionTriggered)
        self._message.show()

        self.writeSuccess.emit(self)
        self._resetState()

    def onSimulationPrintStarted(self, reply):
        if self._stage != OutputStage.writing:
            return
        if reply.error() != QNetworkReply.NoError:
            Logger.log("d", "Stopping due to reply error: " + reply.error())
            return

        Logger.log("d", "Simulation print started for file " + self._fileName)

        # give it some to start the simulation
        QTimer.singleShot(2000, self.onCheckStatus)

    def onCheckStatus(self):
        if self._stage != OutputStage.writing:
            return

        Logger.log("d", "Checking status...")

        if self._use_rrf_http_api:
            self._send('rr_status',
                query=[("type", "3")],
                next_stage=self.onStatusReceived,
            )
        else:
            self._send('machine/status',
                next_stage=self.onStatusReceived,
            )

    def onStatusReceived(self, reply):
        if self._stage != OutputStage.writing:
            return
        if reply.error() != QNetworkReply.NoError:
            Logger.log("d", "Stopping due to reply error: " + reply.error())
            return

        Logger.log("d", "Status received - decoding...")
        reply_body = bytes(reply.readAll()).decode()
        Logger.log("d", "Status: " + reply_body)

        status = json.loads(reply_body)
        if self._use_rrf_http_api:
            # RRF 1.21RC2 and earlier used P while simulating
            # RRF 1.21RC3 and later uses M while simulating
            busy = status["status"] in ['P', 'M']
        else:
            busy = status["result"]["state"]["status"] == 'simulating'

        if busy:
            # still simulating
            if self._message and "fractionPrinted" in status:
                self._message.setProgress(float(status["fractionPrinted"]))
            QTimer.singleShot(1000, self.onCheckStatus)
        else:
            Logger.log("d", "Simulation print finished")

            gcode='M37'
            Logger.log("d", "Sending gcode:" + gcode)
            if self._use_rrf_http_api:
                self._send('rr_gcode',
                    query=[("gcode", gcode)],
                    next_stage=self.onM37Reported,
                )
            else:
                self._send('machine/code',
                    data=gcode.encode(),
                    next_stage=self.onReported,
                )
    def onM37Reported(self, reply):
        if self._stage != OutputStage.writing:
            return
        if reply.error() != QNetworkReply.NoError:
            Logger.log("d", "Stopping due to reply error: " + reply.error())
            return

        Logger.log("d", "M37 finished - let's get it's reply...")
        reply_body = bytes(reply.readAll()).decode().strip()
        Logger.log("d", "M37 gcode reply | " + reply_body)

        self._send('rr_reply',
            next_stage=self.onReported,
        )

    def onReported(self, reply):
        if self._stage != OutputStage.writing:
            return
        if reply.error() != QNetworkReply.NoError:
            Logger.log("d", "Stopping due to reply error: " + reply.error())
            return

        Logger.log("d", "Simulation status received - decoding...")
        reply_body = bytes(reply.readAll()).decode().strip()
        Logger.log("d", "Reported | " + reply_body)

        if self._message:
            self._message.hide()
            self._message = None

        text = "Simulation finished on {}:\n\n{}".format(self._name, reply_body)
        self._message = Message(catalog.i18nc("@info:status", text), 0, False)
        self._message.addAction("open_browser", catalog.i18nc("@action:button", "Open Browser"), "globe", catalog.i18nc("@info:tooltip", "Open browser to DuetWebControl."))
        self._message.actionTriggered.connect(self._onMessageActionTriggered)
        self._message.show()

        if self._use_rrf_http_api:
            self._send('rr_disconnect')
        self.writeSuccess.emit(self)
        self._resetState()

    def _onProgress(self, progress):
        if self._message:
            self._message.setProgress(progress)
        self.writeProgress.emit(self, progress)

    def _resetState(self):
        Logger.log("d", "called")
        if self._stream:
            self._stream.close()
        self._stream = None
        self._stage = OutputStage.ready
        self._fileName = None

    def _onMessageActionTriggered(self, message, action):
        if action == "open_browser":
            QDesktopServices.openUrl(QUrl(self._url))
            if self._message:
                self._message.hide()
                self._message = None

    def _onUploadProgress(self, bytesSent, bytesTotal):
        if bytesTotal > 0:
            self._onProgress(int(bytesSent * 100 / bytesTotal))

    def _onNetworkError(self, reply, error):
        # https://doc.qt.io/qt-5/qnetworkreply.html#NetworkError-enum
        Logger.log("e", repr(error))
        if self._message:
            self._message.hide()
            self._message = None

        errorString = ''
        if reply:
            errorString = reply.errorString()

        message = Message(catalog.i18nc("@info:status", "Network error {} on {}: {}").format(error, self._name, errorString), 0, False)
        message.show()

        self.writeError.emit(self)
        self._resetState()
