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

    minimumWidth: 380 * screenScaleFactor
    minimumHeight: 200 * screenScaleFactor
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
            return true
        } else if(val == "uninstalled" || val == undefined ) {
            return false
        } else {
            return val
        }
    }


    ColumnLayout {
      id: col1
      anchors.fill: parent
      anchors.margins: margin

        ColumnLayout {
          id: rowLayout
          Layout.fillWidth: true

          width: parent.width
          height: parent.height


          Switch {
            id: installCB
            text: "Are Nautilus Printer Files Installed? "
            ToolTip.timeout: 5000
            ToolTip.visible: hovered
            ToolTip.text: "Deselect this to uninstall the Nautilus printer files \n Select it to install the files."
            checked: checkInstallStatus(UM.Preferences.getValue("HRNautilus/install_status"))
            onClicked: manager.changePluginInstallStatus(checked)
          } //end Switch
        } // end columnlayout

        RowLayout {
            id: buttonRow
            width: parent.width
            anchors.bottom: parent.bottom
            Button
            {
                id: button1
                text: qsTr("Open plugin website")
                onClicked: manager.openPluginWebsite()
            }

            Button
            {
                id: button
                UM.I18nCatalog
                {
                    id: catalog1
                    name: "cura"
                }
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
                text: catalog.i18nc("@action:button", "Help")
                onClicked: manager.showHelp()
            }
        } // end RowLayout

    } // end ColumnLayout
}
