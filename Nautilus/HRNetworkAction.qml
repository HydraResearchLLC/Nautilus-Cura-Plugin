import QtQuick 6.0
import QtQuick.Controls 6.0
import QtQuick.Layouts 1.1
import QtQuick.Window 2.1

import UM 1.5 as UM
import Cura 1.0 as Cura


Cura.MachineAction
{
    id: base;

    property var finished: manager.finished
    onFinishedChanged: if(manager.finished) {completed()}

    function reset()
    {
        manager.reset()
    }

    anchors.fill: parent;
    property var selectedInstance: null

    property bool validUrl: true;

    Component.onCompleted: {
        actionDialog.minimumWidth = screenScaleFactor * 550;
        actionDialog.minimumHeight = screenScaleFactor * 380;
        actionDialog.maximumWidth = screenScaleFactor * 550;
        actionDialog.maximumHeight = screenScaleFactor * 380;
    }
    Rectangle
            {
                width: parent.width //- (parent.x+UM.Theme.getSize("default_margin").width)
                height: base.height //- (parent.y + UM.Theme.getSize("default_margin").height)
                color: UM.Theme.getColor("main_background")
                border.width: UM.Theme.getSize("default_lining").width
                border.color: UM.Theme.getColor("thick_lining")
    Column {
        anchors.fill: parent;
        anchors.margins: 20
        spacing: 5

        Item { width: parent.width; }
        UM.Label { text: catalog.i18nc("@label", "IP Address (URL)"); font: UM.Theme.getFont("medium")}
        Cura.TextField {
            id: urlField;
            text: manager.printerSettingUrl;
            maximumLength: 1024;
            anchors.left: parent.left;
            anchors.right: parent.right;
            onTextChanged: {
                base.validUrl = manager.validUrl(urlField.text);
            }
        }

        Item { width: parent.width; }
        UM.Label { text: catalog.i18nc("@label", "Printer Password (if you used M551)"); font: UM.Theme.getFont("medium")}
        Cura.TextField {
            id: printer_passwordField;
            text: manager.printerSettingPrinterPassword;
            maximumLength: 1024;
            anchors.left: parent.left;
            anchors.right: parent.right;
        }

        Item { width: parent.width; }
        UM.Label { text: catalog.i18nc("@label", "HTTP Basic Auth: user (if you run a reverse proxy)"); font: UM.Theme.getFont("medium")}
        Cura.TextField {
            id: http_userField;
            text: manager.printerSettingHTTPUser;
            maximumLength: 1024;
            anchors.left: parent.left;
            anchors.right: parent.right;
        }

        Item { width: parent.width; }
        UM.Label { text: catalog.i18nc("@label", "HTTP Basic Auth: password (if you run a reverse proxy)"); font: UM.Theme.getFont("medium")}
        Cura.TextField {
            id: http_passwordField;
            text: manager.printerSettingHTTPPassword;
            maximumLength: 1024;
            anchors.left: parent.left;
            anchors.right: parent.right;
        }



        Item {
            width: saveButton.implicitWidth
            height: saveButton.implicitHeight
        }

        Cura.PrimaryButton {
            id: saveButton;
            anchors.right: parent.right;
            anchors.rightMargin: 20
            text: "Save Config";
            //width: screenScaleFactor * 100;
            onClicked: {
                manager.saveConfig(urlField.text, printer_passwordField.text, http_userField.text, http_passwordField.text);
                actionDialog.reject();
            }
            enabled: base.validUrl;
        }

        Item { width: parent.width; }
        UM.Label {
            visible: !base.validUrl;
            text: catalog.i18nc("@error", "URL not valid. Example: http://192.168.1.42/");
            color: "red";
        }

    }
}
}
