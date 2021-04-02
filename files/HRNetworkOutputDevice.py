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
        self.setShortDescription("HRNetwork Plugin")
        self.setDescription("Configure Hydra Research Printer...")
        self.setPriority(0)

    def requestWrite(self, node, fileName=None, *args, **kwargs):
        msg = (
            "To configure your Hydra Research printer go to:\n"
            "→ Cura Preferences\n"
            "→ Printers\n"
            "→ activate and select your printer\n"
            "→ click on 'Connect via Network'\n"
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
            description = catalog.i18nc("@action:button", "Upload to {0}").format(self._name)
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
            fileName = self.nameMaker() + '.gcode'
        else:
            fileName = "%s.gcode" % Application.getInstance().getPrintInformation().jobName
        self._fileName = fileName

        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qml', 'UploadFilename.qml')
        self._dialog = CuraApplication.getInstance().createQmlComponent(path, {"manager": self})
        self._dialog.textChanged.connect(self.onFilenameChanged)
        self._dialog.accepted.connect(self.onFilenameAccepted)
        self._dialog.show()
        self._dialog.findChild(QObject, "nameField").setProperty('text', self._fileName)
        self._dialog.findChild(QObject, "nameField").select(0, len(self._fileName) - 6)
        self._dialog.findChild(QObject, "nameField").setProperty('focus', True)

    def nameMaker(self):
        base = Application.getInstance().getPrintInformation().baseName
        Logger.log('d','base is '+ base)

        mat = str(Application.getInstance().getPrintInformation().materialNames)[2:-2]

        noz = Application.getInstance().getExtruderManager().getActiveExtruderStacks()[0].variant.getName()
        layerheight = str(int(Application.getInstance().getMachineManager().activeMachine.getProperty("layer_height", "value")*1000)) + 'um'
        fileName = base[0:14] + " - " +  mat + " - " + noz + " - " + layerheight
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
        if not self._fileName.endswith('.gcode') and '.' not in self._fileName:
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

        message = Message(catalog.i18nc("@info:status", "There was a network error: {} {}").format(error, errorString), 0, False)
        message.show()

        self.writeError.emit(self)
        self._resetState()

    def fileLister(self, url, dir):
      try:
          self.macRequest = QtNetwork.QNetworkRequest(QUrl(url + 'rr_filelist?dir=' + dir))
          self.macRequest.setRawHeader(b'User-Agent', b'Cura Plugin Nautilus')
          self.macRequest.setRawHeader(b'Accept', b'application/json, text/javascript')
          self.macRequest.setRawHeader(b'Connection', b'keep-alive')

          #self.gitRequest.setRawHeader(b"User-Agent", b"Mozilla/5.0 (Windows; U; Windows NT 6.0; en-US; rv:1.9.1.7) Gecko/20091221 Firefox/3.5.7 (.NET CLR 3.5.30729)")
          self.macroReply = self._qnam.get(self.macRequest)
          loop = QEventLoop()
          self.macroReply.finished.connect(loop.quit)
          loop.exec_()
          reply_body = bytes(self.macroReply.readAll()).decode()
          Logger.log("d", self._name_id + " | Status received | "+reply_body)
          return reply_body

      except:
          Logger.log("i","couldn't connect to the printer: "+str(traceback.format_exc()))
          return '0'

    def fileStructer(self,url,dir):
      fileStr = self.fileLister(url,dir)
      if fileStr == '0':
          return
      try:
          filelist = json.loads(fileStr)['files']
      except:
          filelist = {}

      for macs in filelist:
          if macs['type'] == 'f':
              self._macStruct.append(dir+'/'+macs['name'])
              self.updProg+=1
              self._onConfigUpdateProgress(self.updProg)
          elif macs['type'] == 'd':
              direc = dir + '/' + macs['name']
              self._dirStruct.append(direc)
              self.fileStructer(url,direc)
          else:
              Logger.log('i',"what in tarnation")
      Logger.log("i",'big done!')

    def beginUpdate(self, message, action):
      if message:
          message.hide()
      self._send('connect', [("password", self._printer_password), self._timestamp()])
      loop = QEventLoop()
      getTimer = QTimer()
      self._reply.finished.connect(loop.quit)
      loop.exec_()
      if self._reply:
          self.onConnected()
      else:
          Logger.log('d','no reply item')
          self._onTimeout()

    def onConnected(self):
      self._send('status', [("type", '3')])
      loop = QEventLoop()
      self._reply.finished.connect(loop.quit)
      loop.exec_()
      reply_body = bytes(self._reply.readAll()).decode()
      Logger.log("d", str(len(reply_body)) + " | The reply is: | " + reply_body)
      if len(reply_body)==0:
          self._onTimeout()
      else:
          status = json.loads(reply_body)["status"]
          if 'i' in status.lower():
              Logger.log('d', 'update under normal conditions. Status: '+status)
              self._send('gcode', [("gcode", 'M291 P\"Do not power off your printer or close Cura until updates complete\" R\"Update Alert\" S0 T0')])
              #self.githubRequest()
          else:
              message = Message(catalog.i18nc("@info:status","{} is busy, unable to update").format(self._name))
              message.show()

    def checkPrinterStatus(self):
      self._send('status', [("type", '3')])
      loop = QEventLoop()
      self._reply.finished.connect(loop.quit)
      getTimer.singleShot(3000, loop.quit)
      loop.exec_()
      reply_body = bytes(self._reply.readAll()).decode()
      Logger.log("d", str(len(reply_body)) + " | The reply is: | " + reply_body)
      if len(reply_body)==0:
          self._onTimeout()
          return False
      else:
          status = json.loads(reply_body)["status"]
          if 'i' in status.lower():
              return True
          else:
              return False

    """
    def githubRequest(self):
      #self.writeError.connect(self.updateError())
      self._progress = Message(catalog.i18nc("@info:progress", "Do not power off printer or close Cura until updates complete \n Updating {} \n").format(self._name), 0, False, 1)
      self._progress.show()
      self._warning = Message(catalog.i18nc("@info:status","Do not power off printer or close Cura until updates complete"), 0, False)
      self._warning.show()
      Logger.log('i','query github')
      self._stage = OutputStage.ready

      try:
          #self.nam = QtNetwork.QNetworkAccessManager()
          self.gitRequest = QtNetwork.QNetworkRequest(QUrl(self.gitUrl))
          debugstatement = self.gitRequest.url().toString()
          Logger.log('i','debug: '+debugstatement)
          #self.gitRequest.setRawHeader(b"User-Agent", b"Mozilla/5.0 (Windows; U; Windows NT 6.0; en-US; rv:1.9.1.7) Gecko/20091221 Firefox/3.5.7 (.NET CLR 3.5.30729)")
          self.gitReply = self._qnam.get(self.gitRequest)
          loop = QEventLoop()
          self.gitReply.finished.connect(loop.quit)
          loop.exec_()
          response = bytes(self.gitReply.readAll()).decode()

          Logger.log('i','123 '+str(len(response)))
          #self._qnam.finished.connect(self.githubDownload())
          macroUrl = json.loads(response)['assets'][1]['browser_download_url']
          configUrl = json.loads(response)['assets'][0]['browser_download_url']
          Logger.log("i",'gettin macros from '+str(macroUrl))
          resp = requests.get(macroUrl, self.path, allow_redirects=True)
          self.updProg = 0
          open(os.path.join(self.path,'Nautilus_macros.zip'), 'wb').write(resp.content)
          self.deleteMacros()
          #don't forget this
          respo = requests.get(configUrl, self.path, allow_redirects=True)
          open(os.path.join(self.path,'Nautilus_config.zip'),'wb').write(respo.content)
          Logger.log("i",'gettin config from '+str(configUrl))
          self.updateConfig(configUrl)
          self.updateComplete()
      except:
          Logger.log("i","somethings goofed! "+str(traceback.format_exc()))

    """
    def deleteMacros(self):
      if self._stage != OutputStage.ready:
          raise OutputDeviceError.DeviceBusyError()
      self.fileStructer(self._url, 'macros')
      Logger.log('i', 'Macs: '+ str(self._macStruct))
      Logger.log('i', 'Dirs: '+str(self._dirStruct))
      for mac in self._macStruct:
          Logger.log('i','1')
          self._send('delete',[('name',"0:/"+mac),self._timestamp()], self.onMacroDeleted)
          sleep(.1)
      for dir in self._dirStruct:
          Logger.log('i','1')
          self._send('delete',[('name',"0:/"+dir),self._timestamp()], self.onMacroDeleted)
          sleep(.1)
      self.updateMacros()

    def updateMacros(self):
      self._stage = OutputStage.writing
      self.writeStarted.emit(self)

      zipdata = os.path.join(self.path,'Nautilus_macros.zip')
      with zipfile.ZipFile(zipdata, "r") as zip_ref:
          with tempfile.TemporaryDirectory() as folder:
              for info in zip_ref.infolist():
                  self.updProg+=1
                  self._onConfigUpdateProgress(self.updProg)
                  extracted_path = zip_ref.extract(info.filename, path = folder)
                  permissions = os.stat(extracted_path).st_mode
                  os.chmod(extracted_path, permissions | stat.S_IEXEC)
                  Logger.log('i',"extracting and uploading "+info.filename)
                  #Logger.log('i',"relative to: "+str(folder))
                  with open(extracted_path, 'r') as fileobj:
                      self._fileName = info.filename
                      self.macData = fileobj.read()
                      self.onMacDataReady()
                      sleep(.25)
                      self.macData = None

    def onMacDataReady(self):
      # create the temp file for the macro
      self._streamer = StringIO()
      self._stage = OutputStage.writing
      self.writeStarted.emit(self)

      # show a progress message
      #self._message = Message(catalog.i18nc("@info:progress", "Sending to {}").format(self._name), 0, False, -1)
      #self._message.show()

      try:
          self._streamer.write(self.macData)
      except:
          Logger.log("e", "Macro write failed.")
          return

      # start
      Logger.log("d", self._name_id + " | Connecting...")
      self._send('connect', [("password", self._duet_password), self._timestamp()], self.macroUpload())

    def macroUpload(self):
      Logger.log('i','time to upload the macro')
      #if self._stage != OutputStage.writing:
      #    return

      Logger.log("d", self._name_id + " | Uploading... | "+str(self._fileName))
      self._streamer.seek(0)
      self._posterData = QByteArray()
      self._posterData.append(self._streamer.getvalue().encode())
      self._send('upload', [("name", "0:/macros/" + self._fileName), self._timestamp()], self.onMacUploadDone(), self._posterData)
      loop = QEventLoop()
      self._reply.finished.connect(loop.quit)
      loop.exec()

    def updateConfig(self, url):
      self._stage = OutputStage.ready
      self.writeStarted.emit(self)

      #unpack zip as in update Macros
      zipdata = os.path.join(self.path,'Nautilus_config.zip')
      with zipfile.ZipFile(zipdata, "r") as zip_ref:
          with tempfile.TemporaryDirectory() as folder:
              for info in zip_ref.infolist():
                  self.updProg+=1
                  self._onConfigUpdateProgress(self.updProg)
                  extracted_path = zip_ref.extract(info.filename, path = folder)
                  Logger.log('i',"extracting and uploading "+info.filename)
                  with open(extracted_path, 'rb') as fileobj:
                      if info.filename.endswith('bin'):
                          Logger.log('i','bin files: '+info.filename)
                          #change firmware filename to Duet2CombinedFirmware.bin
                          if 'firmware' in info.filename.lower():
                              Logger.log("i","Firm bin: "+info.filename)
                              self._fileName = 'Duet2CombinedFirmware.bin'
                              self.configData = fileobj.read()
                              self.onSysDataReady()
                              self.configData = None
                          #change DWC filename to DuetWiFiServer.bin
                          elif 'server' in info.filename.lower():
                              Logger.log("i","dwc bin: "+info.filename)
                              self._fileName = 'DuetWiFiServer.bin'
                              self.configData = fileobj.read()
                              self.onSysDataReady()
                              self.configData = None
                              #self._send('upload', [("name", "0:/sys/Duet2WiFiServer.bin"), self._timestamp()], self.onUpdateDone, fileobj) #write onUpdateDone
                          else:
                              Logger.log("i","uploading iap"+info.filename)
                              self._fileName = info.filename
                              self.configData = fileobj.read()
                              self.onSysDataReady()
                              self.configData = None

                      elif info.filename.endswith('.g'):
                          Logger.log('i','uploading gcode file: '+info.filename)
                          self._fileName = info.filename
                          self.configData = fileobj.read()
                          self.onSysDataReady()
                          self.configData = None

                      elif info.filename.endswith('.gz') or info.filename.endswith('.json') or info.filename.startswith('css') or info.filename.startswith('json') or info.filename.startswith('fonts'):
                          Logger.log('i','uploading www file: '+info.filename)
                          self._fileName = info.filename
                          self.configData = fileobj.read()
                          self.onWwwDataReady()
                          self.configData = None

                      else:
                          Logger.log('d', 'misc files: '+info.filename)
      self.firmwareInstall()

    def firmwareInstall(self):
      self._stage = OutputStage.writing
      #FIX THIS
      self._send('gcode', [("gcode", 'M997 S0:1:2')])
      sleep(.1)
      self._stage = OutputStage.ready

    def initFlag(self):
      Logger.log('i','flag init')
      self.updateFlag = 1


    def onSysDataReady(self):
      self._streamer = BytesIO()
      self._stage = OutputStage.writing
      self.writeStarted.emit(self)

      try:
          self._streamer.write(self.configData)
      except:
          Logger.log('e', 'bin write failed: ' +str(traceback.format_exc()))

      Logger.log("d", self._name_id + " | Connecting...")
      self._send('connect', [("password", self._duet_password), self._timestamp()], self.sysUpload())

    def sysUpload(self):
      self._streamer.seek(0)
      self._posterData = QByteArray()
      self._posterData.append(self._streamer.getvalue())
      self._send('upload', [("name", "0:/sys/"+self._fileName), self._timestamp()], self.onMacUploadDone(), self._posterData) #write onUpdateDone
      loop = QEventLoop()
      self._reply.finished.connect(loop.quit)
      loop.exec()
      #copy config.json, .gz files, css/fonts/js directories to /www
      #put .bins and everything not in /www in /sys
      #send M997

    def onWwwDataReady(self):
      self._streamer = BytesIO()
      self._stage = OutputStage.writing
      self.writeStarted.emit(self)

      try:
          self._streamer.write(self.configData)
      except:
          Logger.log('e', 'www write failed: ' +str(traceback.format_exc()))

      Logger.log("d", self._name_id + " | Connecting...")
      self._send('connect', [("password", self._duet_password), self._timestamp()], self.wwwUpload())

    def wwwUpload(self):
      self._streamer.seek(0)
      self._posterData = QByteArray()
      self._posterData.append(self._streamer.getvalue())
      self._send('upload', [("name", "0:/www/"+self._fileName), self._timestamp()], self.onMacUploadDone(), self._posterData) #write onUpdateDone
      loop = QEventLoop()
      self._reply.finished.connect(loop.quit)
      loop.exec()

    def onUpdateDone(self):
      Logger.log('i',"update done")

    def onMacroDeleted(self):
      Logger.log('i',"macro deleted")

    def onMacUploadDone(self):
      Logger.log('i','cleaning up!')
      #self._streamer.close()
      #self.streamer = None
      self._cleanupRequest()

    def updateComplete(self):
      self._message = Message(catalog.i18nc("@info:progress", "Update Complete! Printer restarting..."))
      self._message.show()
      self._warning.hide()
      self._warning = None
      self._progress.hide()
      self._progress = None
      #QTimer.singleShot(15000, self.updateCheck)

    def updateError(self, errorCode):
      Logger.log("e", "updateError: %s", repr(errorCode))
      self._message = Message(catalog.i18nc("@info:status","There was an error updating {}").format(self._name))
      self._message.show()
    """
    def updateCheck(self):
      self.Nauti.checkGit()
      self._send('download', [("name", "0:/private/firmware_version")])
      loop = QEventLoop()
      getTimer = QTimer()
      self._reply.finished.connect(loop.quit)
      getTimer.singleShot(8000, loop.quit)
      loop.exec()
      if self._reply:
          reply_body = bytes(self._reply.readAll()).decode().strip()
          if len(reply_body)>0:
              newestVersion = CuraApplication.getInstance().getPreferences().getValue("Nautilus/configversion")
              if StrictVersion(newestVersion)>StrictVersion(reply_body):
                  #CuraApplication.getInstance().getPreferences().addPreference("Nautilus/uptodate","no")
                  self._onUpdateRequired()
                  NautilusUpdate.NautilusUpdate().thingsChanged()
              #self._testmess = Message(catalog.i18nc("@info:status","{} has firmware version: {}").format(self._name,reply_body))
              #self._testmess.show()
              else:
                  Logger.log('i', str(self._name) + " is up to date"+str(self.updateFlag))
                  #CuraApplication.getInstance().getPreferences().addPreference("Nautilus/uptodate","yes")
                  NautilusDuet.NautilusDuet().saveInstance(self._name, self._name, self._url, self._duet_password, self._http_user, self._http_password, reply_body)
                  sleep(.5)
                  NautilusUpdate.NautilusUpdate().thingsChanged()
                  if self.updateFlag == 0:
                      mess = Message(catalog.i18nc("@info:status",'Nautilus is up to date!'))
                      mess.show()
          else:
              Logger.log('i','timeout error')
              if self.updateFlag == 0:
                  self._onTimeout()
      else:
          Logger.log('i','unknown error')
    """
