import QtQuick 6.0
import QtQuick.Controls 6.0
import QtQuick.Layouts
import QtQuick.Dialogs
import QtQuick.Window

import UM 1.5 as UM
import Cura 1.0 as Cura


UM.Dialog
{
    id: base
    property string installStatusText

    minimumWidth: 400 * screenScaleFactor
    minimumHeight: 450 * screenScaleFactor
    title: "Hydra Research Plugin Preferences"

    function checkBooleanVals(val) {
        if(val == "Yes") {
            return true
        } else if(val == undefined || val == "No" ) {
            return false
        } else {
            return val
        }
    }
    function checkInstallStatus(prefVal) {
        if(prefVal == "installed") {
            return "Hydra Research profiles ARE installed"
        } else  {
            return "Hydra Research profiles are NOT installed"
        }
    }

    function buttonStatus(prefVal) {
        if(prefVal == "installed") {
            return "Uninstall profiles"
        } else {
            return "Install profiles"
        }
    }

    function checkedStatus(prefVal) {
        if(prefVal == "installed") {
            return "checked"
        } else if(prefVal == "downloaded") {
            return
        }
    }
    Rectangle
            {
                width: parent.width //- (parent.x+UM.Theme.getSize("default_margin").width)
                height: base.height - (parent.y + UM.Theme.getSize("default_margin").height)
                color: UM.Theme.getColor("main_background")
                border.width: UM.Theme.getSize("default_lining").width
                border.color: UM.Theme.getColor("thick_lining")

    ColumnLayout {
      id: col1
      spacing: 10
      height: parent.height
      width: parent.width

          UM.Label{
            id: versionNO
            Layout.alignment: Qt.AlignCenter
            text: "Hydra Research Plugin"
            //color: "black"
            font: UM.Theme.getFont("huge")
            //Layout.columnSpan: 2
          }
          UM.Label{
            id: versionNO2
            Layout.alignment: Qt.AlignCenter
            text: "v" + manager.getVersion
            //color: "black"
            font: UM.Theme.getFont("large")
          }
          MenuSeparator {
            id: sep2
            //////anchors.top: versionNO2.bottom
            Layout.alignment: Qt.AlignCenter
            implicitWidth: 300
          }
          UM.Label {
            id: installCB
            Layout.alignment: Qt.AlignCenter
            //anchors.top: sep2.bottom
            text: checkInstallStatus(UM.Preferences.getValue("Nautilus/install_status"))
            font: UM.Theme.getFont("medium")
            //color: "black"
            //anchors.margins: 10
            //Layout.columnSpan: 2
            //setEnabled(false)
            //checked:

          } //end Switch
          Cura.SecondaryButton
          {
            id: button1
            Layout.alignment: Qt.AlignCenter
            //anchors.top: installCB.bottom
            //anchors.margins: 10
            text: qsTr(buttonStatus(UM.Preferences.getValue("Nautilus/install_status")))
            onClicked: manager.changePluginInstallStatus("checked")
            //Layout.columnSpan:2
          }
          MenuSeparator {
              id: sep1
              Layout.alignment: Qt.AlignCenter
              //anchors.top: button1.bottom
              //anchors.margins: 10
              implicitWidth: 300
          }
          Cura.SecondaryButton{
            id: resetprice
            //anchors.top: sep1.bottom
            //anchors.margins: 10
            Layout.alignment: Qt.AlignCenter
            text: "Reset Material Prices"
            onClicked: manager.addMatCosts()
          }
          Cura.SecondaryButton {
                id: button
                //anchors.top: resetprice.bottom
                //anchors.margins: 10
                Layout.alignment: Qt.AlignCenter
                text: "Report Issue"
                onClicked: manager.reportIssue()
                //Layout.columnSpan:2
            }

            Cura.SecondaryButton {
                id: helpButton
                //anchors.top: button.bottom
                //anchors.margins: 10
                //Layout.topMargin:25
                //topPadding: 5
                Layout.alignment: Qt.AlignCenter
                text: "Help"
                onClicked: manager.showHelp()
                //Layout.columnSpan:2
            }

          UM.CheckBox{
            id: developermode
            //anchors.top: helpButton.bottom
            //anchors.margins: 10
            //Layout.topMargin:25
            //topPadding: 5
            Layout.alignment: Qt.AlignCenter
            text: "Developer Mode"
            font: UM.Theme.getFont("medium")
            checked: checkBooleanVals(manager.developerModeStatus)
            onClicked: manager.setDeveloperMode()
          }
        } // end RowLayout

    } // end ColumnLayout
}
