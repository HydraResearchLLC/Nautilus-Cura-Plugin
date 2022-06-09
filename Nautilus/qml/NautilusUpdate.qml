import QtQuick 6.0
import QtQuick.Controls 1.4
import QtQuick.Controls.Styles 1.1
import QtQuick.Layouts 1.1
import QtQuick.Dialogs 1.3
import QtQuick.Window 2.1

import UM 1.2 as UM
import Cura 1.5 as Cura


Cura.MachineAction
{
    id: dialog;

    //property string currentName: (instanceList.currentIndex != -1 ? instanceList.currentItem.name : "");
    property int defaultVerticalMargin: UM.Theme.getSize("default_margin").height;
    property int defaultHorizontalMargin: UM.Theme.getSize("default_margin").width;
    property string selectedPath: CuraApplication.getDefaultPath("dialog_load_path")
    property bool validPath: true
    property bool connectedPrinter: true
    property int usefulWidth: 350 * screenScaleFactor


    Rectangle {
      width: parent.width + 20//- 20
      height: parent.height + 10000//(UM.Theme.getSize("toolbox_thumbnail_large").height * 1.5) + 20//5*parent.height/16 //UM.Theme.getSize("toolbox_thumbnail_large").height
      anchors.horizontalCenter: parent.horizontalCenter
      anchors.top: parent.top
      anchors.topMargin: - 10 // was 20
      border.width: UM.Theme.getSize("default_lining").width
      border.color: UM.Theme.getColor("lining")
    }
    Item {
        UM.I18nCatalog { id: catalog; name: "cura"; }
        SystemPalette { id: palette }
        id: windowFirmwareUpdate


        anchors {
            fill: parent;
            topMargin: parent.defaultVerticalMargin
                }

        Row {
          id: printerRow;
          spacing: 5;
          anchors { top: parent.top
                    //left: printerRow.left
                    horizontalCenter: parent.horizontalCenter
                    margins: 40
          }

          Label {anchors.verticalCenter: printerRow.verticalCenter; text: "Select Printer: "}

          ComboBox{
              id: instanceList
              anchors.verticalCenter: printerRow.verticalCenter;
              model: manager.serverList;
              onCurrentIndexChanged: { dialog.connectedPrinter = manager.statusCheck(currentText);}
            }

          Label {
            text: "Printer is not connected";
            anchors.leftMargin: 30;
            anchors.verticalCenter: printerRow.verticalCenter;
            visible: !dialog.connectedPrinter;

          }
        }

        Row {
          id: firmRow;
          spacing: 5;
          anchors { top: printerRow.top
                    horizontalCenter: parent.horizontalCenter
                    //left: parent.left
                    margins: 40
          }

          Label {anchors.verticalCenter: firmRow.verticalCenter; text: "Firmware Zip: "}

          TextField {
                    id: pathField
                    placeholderText: "Enter path or click Browse"
                    text: fileDialog.fileUrl;
                    width: usefulWidth;
                    anchors.verticalCenter: firmRow.verticalCenter;
                    onTextChanged: {
                        dialog.validPath = manager.validPath(pathField.text);
                      }
        }

          Cura.SecondaryButton {
            text: "Browse";
            anchors.verticalCenter: firmRow.verticalCenter;
            //anchors.horizontalCenter: firmRow.horizontalCenter;
            anchors.leftMargin: 20
            onClicked: fileDialog.open()}
        }
        Label{ text: "Invalid Path! ";
              anchors{
                top: firmRow.bottom
                horizontalCenter: parent.horizontalCenter
              }
              visible: !dialog.validPath
      }
      Cura.PrimaryButton {
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        text: "Update"
        enabled: dialog.validPath //&& dialog.connectedPrinter
        onClicked: {confirmationDialog.open(); manager.setUpdatePrinter(instanceList.currentText);}
      }

        }

        Item
        {    UM.Dialog{
                id: confirmationDialog;
                minimumWidth: screenScaleFactor * 350
                minimumHeight: screenScaleFactor * 100
                Rectangle {
                  width: parent.width + 20//- 20
                  height: parent.height + 10000//(UM.Theme.getSize("toolbox_thumbnail_large").height * 1.5) + 20//5*parent.height/16 //UM.Theme.getSize("toolbox_thumbnail_large").height
                  anchors.horizontalCenter: parent.horizontalCenter
                  anchors.top: parent.top
                  anchors.topMargin: - 10 // was 20
                  border.width: UM.Theme.getSize("default_lining").width
                  border.color: UM.Theme.getColor("lining")
                }

                Label{
                  id: question
                  anchors.horizontalCenter: parent.horizontalCenter
                  text: "Begin updating your printer?"
                  font.bold: false
                  font.pointSize: 12
                  color: "#737373"
                  //Layout.columnSpan: 2
                }

                Cura.PrimaryButton{
                  id: button1
                  anchors.top: question.bottom
                  anchors.right: parent.horizontalCenter
                  anchors.topMargin: 20
                  anchors.rightMargin:10
                  text: "Yes"
                  onClicked: {manager.updateConfirm(), confirmationDialog.close()}
                }

                Cura.SecondaryButton{
                  id: button2
                  anchors.top: question.bottom
                  anchors.left: parent.horizontalCenter
                  anchors.topMargin: 20
                  anchors.leftMargin: 10
                  text: "No"
                  onClicked: {confirmationDialog.close()}
                }
            }
          }

        FileDialog {
          id: fileDialog
          title: "Please choose a file"
          folder: CuraApplication.getDefaultPath("dialog_load_path")
          nameFilters: [ "Zip files (*.zip)"]
          onAccepted: {
              selectedPath: fileDialog.fileUrl;
              manager.setZipPath(fileDialog.fileUrl);
              fileDialog.close();
          }
          onRejected: {
              fileDialog.close()
          }

}
}
