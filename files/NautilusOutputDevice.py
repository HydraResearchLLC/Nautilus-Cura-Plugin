import os
import datetime
import base64
import urllib
import json
from io import StringIO, BytesIO
from time import time, sleep
from typing import cast
import requests
import zipfile
import tempfile
import traceback
import stat

from distutils.version import StrictVersion

from PyQt5 import QtNetwork
from PyQt5.QtCore import QFile, QUrl, QObject, QCoreApplication, QByteArray, QTimer, QEventLoop, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtQml import QQmlComponent, QQmlContext

from UM.Application import Application
from UM.Logger import Logger
from UM.Message import Message
from UM.Mesh.MeshWriter import MeshWriter
from UM.PluginRegistry import PluginRegistry
from UM.OutputDevice.OutputDevice import OutputDevice
from UM.OutputDevice import OutputDeviceError
from UM.Resources import Resources

from . import Nautilus
from . import NautilusDuet
from . import NautilusUpdate

from UM.i18n import i18nCatalog
catalog = i18nCatalog("cura")

from cura.CuraApplication import CuraApplication
from cura.MachineAction import MachineAction


from enum import Enum
class OutputStage(Enum):
    ready = 0
    writing = 1

class DeviceType(Enum):

    upload = 2


class NautilusOutputDevice(OutputDevice):
    def __init__(self, name, url, duet_password, http_user, http_password, firmware_version, device_type):
        self._device_type = device_type
        if device_type == DeviceType.upload:
            description = catalog.i18nc("@action:button", "Send to {0}").format(name)
            name_id = name + "-upload"
            priority = 10
        else:
            assert False

        super().__init__(name_id)
        self.setShortDescription(description)
        self.setDescription(description)
        self.setPriority(priority)

        self._stage = OutputStage.ready
        self._name = name
        self._name_id = name_id
        self._device_type = device_type
        self._url = url
        self._duet_password = duet_password
        self._http_user = http_user
        self._http_password = http_password
        self._firmware_version = firmware_version
        self.gitUrl = 'https://api.github.com/repos/HydraResearchLLC/Nautilus-Configuration-Macros/releases/latest'
        self.path = os.path.join(Resources.getStoragePath(Resources.Resources), "plugins","Nautilus","Nautilus")
        #RESOLVE FLAG ISSUE
        self.Nauti = Nautilus.Nautilus()



        Logger.log("d", self._name_id + " | New Nautilus Connected")
        Logger.log("d", self._name_id + " | URL: " + self._url)
        Logger.log("d", self._name_id + " | Nautilus password: " + ("set." if self._duet_password else "empty."))
        Logger.log("d", self._name_id + " | HTTP Basic Auth user: " + ("set." if self._http_user else "empty."))
        Logger.log("d", self._name_id + " | HTTP Basic Auth password: " + ("set." if self._http_password else "empty."))

        self._qnam = QtNetwork.QNetworkAccessManager()

        self._stream = None
        self._cleanupRequest()


        self._warning = None
        self._message = None
        self._progress = None
        self.updateFlag = 0
        self._macStruct = []
        self._dirStruct = []

        #QTimer.singleShot(28000, self.initFlag)
        #QTimer.singleShot(30000, self.updateCheck)



    def _timestamp(self):
        return ("time", datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))

    def _send(self, command, query=None, next_stage=None, data=None):
        enc_query = urllib.parse.urlencode(query or dict())

        if enc_query:
            Logger.log("i",str(enc_query))
            command += '?' + enc_query

        self._request = QtNetwork.QNetworkRequest(QUrl(self._url + "rr_" + command))
        self._request.setRawHeader(b'User-Agent', b'Cura Plugin Nautilus')
        self._request.setRawHeader(b'Accept', b'application/json, text/javascript')
        self._request.setRawHeader(b'Connection', b'keep-alive')

        if self._http_user and self._http_password:
            self._request.setRawHeader(b'Authorization', b'Basic ' + base64.b64encode("{}:{}".format(self._http_user, self._http_password).encode()))

        if data:
            Logger.log("i","species: "+str(type(data)))
            #Logger.log('i','size: '+ str(data))
            self._request.setRawHeader(b'Content-Type', b'application/octet-stream')
            self._reply = self._qnam.post(self._request, data)
            self._reply.uploadProgress.connect(self._onUploadProgress)
        else:
            self._reply = self._qnam.get(self._request)

        if next_stage:
            Logger.log('i','nextstage! ')
            self._reply.finished.connect(next_stage)

        self._reply.error.connect(self._onNetworkError)

    def nameMaker(self):
        base = Application.getInstance().getPrintInformation().baseName

        mat = str(Application.getInstance().getPrintInformation().materialNames)[2:-2]

        noz = Application.getInstance().getExtruderManager().getActiveExtruderStacks()[0].variant.getName()
        layerheight = str(int(Application.getInstance().getMachineManager().activeMachine.getProperty("layer_height", "value")*1000)) + 'um'
        fileName = base + " - " +  mat + " - " + noz + " - " + layerheight
        return fileName

    def requestWrite(self, node, fileName=None, *args, **kwargs):
        if self._stage != OutputStage.ready:
            raise OutputDeviceError.DeviceBusyError()

        if fileName:
            fileName = self.nameMaker() + '.gcode'
        else:
            fileName = "%s.gcode" % Application.getInstance().getPrintInformation().jobName
        self._fileName = fileName
        self._baseLength = len(Application.getInstance().getPrintInformation().baseName)
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qml', 'UploadFilename.qml')
        self._dialog = CuraApplication.getInstance().createQmlComponent(path, {"manager": self})
        self._dialog.textChanged.connect(self.onFilenameChanged)
        self._dialog.accepted.connect(self.onFilenameAccepted)
        self._dialog.show()
        self._dialog.findChild(QObject, "nameField").setProperty('text', self._fileName)
        self._dialog.findChild(QObject, "nameField").select(0, self._baseLength)
        self._dialog.findChild(QObject, "nameField").setProperty('focus', True)

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
        self._send('connect', [("password", self._duet_password), self._timestamp()])
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
        QTimer.singleShot(15000, self.updateCheck)

    def updateError(self, errorCode):
        Logger.log("e", "updateError: %s", repr(errorCode))
        self._message = Message(catalog.i18nc("@info:status","There was an error updating {}").format(self._name))
        self._message.show()

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

    def onFilenameChanged(self):
        fileName = self._dialog.findChild(QObject, "nameField").property('text')
        self._dialog.setProperty('validName', len(fileName) > 0)

    def onFilenameAccepted(self):
        self._fileName = self._dialog.findChild(QObject, "nameField").property('text')
        if not self._fileName.endswith('.gcode') and '.' not in self._fileName:
            self._fileName += '.gcode'
        Logger.log("d", self._name_id + " | Filename set to: " + self._fileName)

        self._dialog.deleteLater()

        # create the temp file for the gcode
        self._stream = StringIO()
        self._stage = OutputStage.writing
        self.writeStarted.emit(self)

        # show a progress message
        self._message = Message(catalog.i18nc("@info:progress", "Sending to {}").format(self._name), 0, False, -1)
        self._message.show()

        Logger.log("d", self._name_id + " | Loading gcode...")

        # get the g-code through the GCodeWrite plugin
        # this serializes the actual scene and should produce the same output as "Save to File"
        gcode_writer = cast(MeshWriter, PluginRegistry.getInstance().getPluginObject("GCodeWriter"))
        success = gcode_writer.write(self._stream, None)
        if not success:
            Logger.log("e", "GCodeWrite failed.")
            return

        # start
        Logger.log("d", self._name_id + " | Connecting...")
        self._send('connect', [("password", self._duet_password), self._timestamp()], self.onUploadReady)

    def onUploadReady(self):
        if self._stage != OutputStage.writing:
            return

        Logger.log("d", self._name_id + " | Uploading...")
        self._stream.seek(0)
        self._postData = QByteArray()
        self._postData.append(self._stream.getvalue().encode())
        self._send('upload', [("name", "0:/gcodes/" + self._fileName), self._timestamp()], self.onUploadDone, self._postData)

    def onUploadDone(self):
        if self._stage != OutputStage.writing:
            return

        Logger.log("d", self._name_id + " | Upload done")

        self._stream.close()
        self.stream = None

        if self._device_type == DeviceType.upload:
            self._send('disconnect')
            if self._message:
                self._message.hide()
            text = "Uploaded file {} to {}.".format(os.path.basename(self._fileName), self._name)
            self._message = Message(catalog.i18nc("@info:status", text), 0, False)
            self._message.addAction("open_browser", catalog.i18nc("@action:button", "Open Browser"), "globe", catalog.i18nc("@info:tooltip", "Open browser to DuetWebControl."))
            self._message.actionTriggered.connect(self._onMessageActionTriggered)
            self._message.show()

            self.writeSuccess.emit(self)
            self._cleanupRequest()
            self.updateCheck()

    def _onUpdateProgress(self,progress):
        if self._progress:
            self._progress.setProgress(progress)
        self.writeProgress.emit(self, progress)

    def _onProgress(self, progress):
        if self._message:
            self._message.setProgress(progress)
        self.writeProgress.emit(self, progress)

    def _cleanupRequest(self):
        self._reply = None
        self._request = None
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

    def _onConfigUpdateProgress(self, fileNumber):
        Logger.log('d',str(fileNumber)+' is the progress')
        self._onUpdateProgress(int(fileNumber))

    def _onUploadProgress(self, bytesSent, bytesTotal):
        if bytesTotal > 0:
            self._onProgress(int(bytesSent * 100 / bytesTotal))

    def _onNetworkError(self, errorCode):
        Logger.log("e", "_onNetworkError: %s", repr(errorCode))

        if self._message:
            self._message.hide()
        self._message = None
        if self._warning:
            self._warning.hide()
        self._warning = None
        if self._progress:
            self._progress.hide()
        self._progress = None

        if self._reply:
            errorString = self._reply.errorString()
            Logger.log("e", "Network Error: "+str(errorString))
        else:
            errorString = ''


        if '99' in repr(errorCode):
            if self.updateFlag==0:
                self._unknownError()
            #Unknown Error
            Logger.log('e','unkown error')
        elif '203' in repr(errorCode):
            #File DNE
            Logger.log('e','file DNE')
            if 'firmware' in str(errorString).lower():
                self._onUpdateRequired()
            elif self.updateFlag==0:
                Logger.log('e','unknown '+str(errorString))
                self._unknownError()
        elif '4' in repr(errorCode):
            if self.updateFlag==0:
                self._onTimeout()
            #Timed Out
            Logger.log('e','connection timed out')
        elif '3' in repr(errorCode):
            Logger.log('i','couldn\'t find host')
            if self.updateFlag==0:
                self._notFound()
        else:
            Logger.log('e',"unknown error! code: "+str(errorCode)+"mess: "+str(errorString))
            message = Message(catalog.i18nc("@info:status", "There was a network error: {} {}").format(errorCode, errorString), 0, False)
            message.show()

        self.writeError.emit(self)
        self._cleanupRequest()

    def _unknownError(self):
        message = Message(catalog.i18nc("@info:status", "Unable to connect to {}, there was an unknown error").format(self._name), 0, False)
        message.show()

    def _notFound(self):
        message = Message(catalog.i18nc("@info:status", "Unable to connect to {}, the IP address is invalid or does not exist").format(self._name), 0, False)
        message.show()

    def _onTimeout(self):
        message = Message(catalog.i18nc("@info:status", "Unable to check for updates, Cura cannot connect to {}").format(self._name), 0, False)
        message.show()

    def _onUpdateRequired(self):
        #NautilusUpdate.NautilusUpdate().thingsChanged()
        message=Message(catalog.i18nc("@info:status", "New features are available for {}! It is recommended to update the firmware on your printer.").format(self._name), 0)
        message.addAction("download_config", catalog.i18nc("@action:button", "Update Firmware"), "globe", catalog.i18nc("@info:tooltip", "Automatically download and install the latest firmware"))
        message.actionTriggered.connect(self.beginUpdate)
        message.show()

"""
FUNCTION GRAVEYARD

    def onStatusReceived(self):
        if self._stage != OutputStage.writing:
            return

        reply_body = bytes(self._reply.readAll()).decode()
        Logger.log("d", self._name_id + " | Status received | " + reply_body)

        status = json.loads(reply_body)
        if status["status"] in ['P', 'M'] :
            # still simulating
            # RRF 1.21RC2 and earlier used P while simulating
            # RRF 1.21RC3 and later uses M while simulating
            if self._message and "fractionPrinted" in status:
                self._message.setProgress(float(status["fractionPrinted"]))
            QTimer.singleShot(5000, self.onCheckStatus)
        else:
            Logger.log("d", self._name_id + " | Simulation print finished")
            self._send('reply', [], self.onReported)

    def onReported(self):
        if self._stage != OutputStage.writing:
            return

        reply_body = bytes(self._reply.readAll()).decode().strip()
        Logger.log("d", self._name_id + " | Reported | " + reply_body)

        if self._message:
            self._message.hide()

        text = "Simulation finished on {}:\n\n{}".format(self._name, reply_body)
        self._message = Message(catalog.i18nc("@info:status", text), 0, False)
        self._message.addAction("open_browser", catalog.i18nc("@action:button", "Open Browser"), "globe", catalog.i18nc("@info:tooltip", "Open browser to DuetWebControl."))
        self._message.actionTriggered.connect(self._onMessageActionTriggered)
        self._message.show()

        self._send('disconnect')
        self.writeSuccess.emit(self)
        self._cleanupRequest()

    def onCheckStatus(self):
        if self._stage != OutputStage.writing:
            return

        Logger.log("d", self._name_id + " | Checking status...")

        self._send('status', [("type", "3")], self.onStatusReceived)

    def onReadyToPrint(self):
        if self._stage != OutputStage.writing:
            return

        Logger.log("d", self._name_id + " | Ready to print")
        self._send('gcode', [("gcode", 'M32 "0:/gcodes/' + self._fileName + '"')], self.onPrintStarted)

    def onPrintStarted(self):
        if self._stage != OutputStage.writing:
            return

        Logger.log("d", self._name_id + " | Print started")

        self._send('disconnect')
        if self._message:
            self._message.hide()
        text = "Print started on {} with file {}".format(self._name, self._fileName)
        self._message = Message(catalog.i18nc("@info:status", text), 0, False)
        self._message.addAction("open_browser", catalog.i18nc("@action:button", "Open Browser"), "globe", catalog.i18nc("@info:tooltip", "Open browser to DuetWebControl."))
        self._message.actionTriggered.connect(self._onMessageActionTriggered)
        self._message.show()

        self.writeSuccess.emit(self)
        self._cleanupRequest()
"""
