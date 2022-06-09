import QtQuick 6.0
import QtQuick.Controls 2.1
import QtQuick.Controls.Styles 1.1
import QtQuick.Layouts 1.1
import QtQuick.Dialogs 1.2
import QtQuick.Window 2.1

import UM 1.2 as UM
import Cura 1.0 as Cura

UM.Dialog
{
   id: dialog;

    title: "Network Connections Have Moved!";

    minimumWidth: screenScaleFactor * 650;
    minimumHeight: screenScaleFactor * 350;

    UM.Label{
        id: alert
        anchors.horizontalCenter: parent.horizontalCenter
        text: "Nautilus networking has moved!"
        UM.Theme.getFont("large")
        //Layout.columnSpan: 2
      }
    UM.Label{
      id: moreinfo
      width: parent.width*.9
      anchors.horizontalCenter: parent.horizontalCenter
      anchors.top: alert.bottom
      anchors.margins: 20
      text: "From the main window of Cura, click on the printer name, then \"Manage Printers\".
            Select a Nautilus and click the \"Connect Via Network\" button. \n
            If no buttons appear, make sure to click the \"Activate\" button with the Nautilus highlighted."
      UM.Theme.getFont("medium")
      wrapMode: Label.WordWrap
      horizontalAlignment: Text.AlignHCenter
    }

}
