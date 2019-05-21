import QtQuick 2.1
import QtQuick.Controls 2.1
import QtQuick.Layouts 1.1
import QtQuick.Window 2.1
import QtQuick.Controls.Styles 1.1

import UM 1.1 as UM


UM.Dialog
{
    id: base
    property string installStatusText

    minimumWidth: 450 * screenScaleFactor
    minimumHeight: 400 * screenScaleFactor
    title: catalog.i18nc("@label", "Nautilus Plugin Preferences")

    function checkBooleanVals(val) {
        if(val == "True") {
            return true
        } else if(val == undefined || val == "False" ) {
            return false
        } else {
            return val
        }
    }

    function checkInstallStatus(prefVal) {
        if(prefVal == "installed") {
            return "Nautilus files ARE installed"
        } else  {
            return "Nautilus files are NOT installed"
        }
    }

    function buttonStatus(prefVal) {
        if(prefVal == "installed") {
            return "Uninstall plugin files"
        } else {
            return "Install plugin files"
        }
    }

    function checkedStatus(prefVal) {
        if(prefVal == "installed") {
            return "checked"
        } else {
            return
        }
    }

    GridLayout {
      id: col1
      rows: 4
      columns: 2
      flow: GridLayout.ToptoBottom
      anchors.fill: parent
          Label{
            id: versionNO
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Nautilus Plugin Version "+ manager.getVersion
            font.bold: true
            font.pointSize: 18
            Layout.columnSpan: 2
          }

          Label {
            id: installCB
            anchors.horizontalCenter: parent.horizontalCenter
            text: checkInstallStatus(UM.Preferences.getValue("Nautilus/install_status"))
            Layout.columnSpan: 2
            //setEnabled(false)
            //checked:

          } //end Switch
          Button
          {
            id: button1
            anchors.horizontalCenter: parent.horizontalCenter
            text: qsTr(buttonStatus(UM.Preferences.getValue("Nautilus/install_status")))
            onClicked: manager.changePluginInstallStatus("checked")
            Layout.columnSpan:2
          }

        // end columnlayout

            Button
            {
                id: button
                UM.I18nCatalog
                {
                    id: catalog1
                    name: "cura"
                }
                anchors.left: versionNO.left
                text: catalog1.i18nc("@action:button", "Report Issue")
                onClicked: manager.reportIssue()
            }

            Button
            {
                id: helpButton
                UM.I18nCatalog
                {
                    id: catalog
                    name: "cura"
                }
                anchors.right: versionNO.right
                text: catalog.i18nc("@action:button", "Help")
                onClicked: manager.showHelp()
            }
        } // end RowLayout

    } // end ColumnLayout
