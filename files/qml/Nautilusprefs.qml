import QtQuick 2.4
import QtQuick.Controls 2.1
import QtQuick.Controls.Styles 1.1
import QtQuick.Layouts 1.1
import QtQuick.Dialogs 1.2
import QtQuick.Window 2.1

import UM 1.2 as UM
import Cura 1.0 as Cura


UM.Dialog
{
    id: base
    property string installStatusText

    minimumWidth: 400 * screenScaleFactor
    minimumHeight: 350 * screenScaleFactor
    title: catalog.i18nc("@label", "Nautilus Plugin Preferences")

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
            return "Nautilus profiles ARE installed"
        } else  {
            return "Nautilus profiles are NOT installed"
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

    ColumnLayout {
      id: col1
      spacing: 10
      height: parent.height
      anchors.horizontalCenter: parent.horizontalCenter
      //anchors.fill: parent
          Label{
            id: versionNO
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Nautilus Plugin Version "+ manager.getVersion
            font.bold: true
            font.pointSize: 18
            //Layout.columnSpan: 2
          }
          MenuSeparator {
            id: sep2
            ////anchors.top: versionNO.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            implicitWidth: 300
          }
          Label {
            id: installCB
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: sep2.bottom
            text: checkInstallStatus(UM.Preferences.getValue("Nautilus/install_status"))
            anchors.margins: 10
            //Layout.columnSpan: 2
            //setEnabled(false)
            //checked:

          } //end Switch
          Button
          {
            id: button1
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: installCB.bottom
            anchors.margins: 10
            text: qsTr(buttonStatus(UM.Preferences.getValue("Nautilus/install_status")))
            onClicked: manager.changePluginInstallStatus("checked")
            //Layout.columnSpan:2
          }
          MenuSeparator {
              id: sep1
              anchors.horizontalCenter: parent.horizontalCenter
              anchors.top: button1.bottom
              anchors.margins: 10
              implicitWidth: 300
          }

          Button {
                id: button
                UM.I18nCatalog
                {
                    id: catalog1
                    name: "cura"
                }
                anchors.top: sep1.bottom
                anchors.margins: 10
                anchors.horizontalCenter: parent.horizontalCenter
                text: catalog1.i18nc("@action:button", "Report Issue")
                onClicked: manager.reportIssue()
                //Layout.columnSpan:2
            }

            Button {
                id: helpButton
                UM.I18nCatalog
                {
                    id: catalog
                    name: "cura"
                }
                anchors.top: button.bottom
                anchors.margins: 10
                //Layout.topMargin:25
                //topPadding: 5
                anchors.horizontalCenter: parent.horizontalCenter
                text: catalog.i18nc("@action:button", "Help")
                onClicked: manager.showHelp()
                //Layout.columnSpan:2
            }
        } // end RowLayout

    } // end ColumnLayout
