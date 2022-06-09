import QtQuick 6.0
import QtQuick.Controls 6.0
import QtQuick.Layouts
import QtQuick.Dialogs
import QtQuick.Window

import UM 1.5 as UM
import Cura 1.0 as Cura

UM.Dialog
{
    id: base;
    property string object: "";

    property alias newName: nameField.text;
    property bool validName: true;
    property string validationError;
    property string dialogTitle: "Upload Filename";

    title: dialogTitle;

    width: screenScaleFactor * 400
    height: screenScaleFactor * 160

    //property variant catalog: UM.I18nCatalog { name: "uranium"; }

    signal textChanged(string text);
    signal selectText()
    onSelectText: {
        nameField.selectAll();
        nameField.focus = true;
    }
    Rectangle{
        id: backdrop
        width: parent.width //- (parent.x+UM.Theme.getSize("default_margin").width)
        height: base.height - (UM.Theme.getSize("default_margin").height)//+ parent.y )
        color: UM.Theme.getColor("main_background")
        border.width: UM.Theme.getSize("default_lining").width
        border.color: UM.Theme.getColor("thick_lining")

  /*      Column {
            id: namezone
            spacing: 20
            padding: 10
            anchors.left: backdrop.left
            width: backdrop.width
            //anchors.fill: backdrop;
            //anchors.margins: UM.Theme.getSize("thick_margin")*/
            UM.Label{
                id: bigname
                anchors.top: backdrop.top
                anchors.left: backdrop.left
                anchors.topMargin: UM.Theme.getSize("default_margin").height
                anchors.leftMargin: UM.Theme.getSize("default_margin").height
                text:"Filename:";
                font: UM.Theme.getFont("medium");
                //Layout.topMargin: UM.Theme.getSize("wide_margin") * 2
                //Layout.leftMargin: UM.Theme.getSize("wide_margin") * 2
              }
            Cura.TextField {
                objectName: "nameField";
                anchors.topMargin: UM.Theme.getSize("default_margin").height
                anchors.left: bigname.left
                anchors.top: bigname.bottom
                id: nameField;
                width: parent.width - 2 * UM.Theme.getSize("default_margin").width;
                text: base.object;
                maximumLength: 41;
                onTextChanged: base.textChanged(text);
                Keys.onReturnPressed: { if (base.validName) base.accept(); }
                Keys.onEnterPressed: { if (base.validName) base.accept(); }
                Keys.onEscapePressed: base.reject();
            }

            UM.Label {
                id: errormessage
                anchors.top: nameField.bottom
                anchors.left: bigname.left
                anchors.topMargin: UM.Theme.getSize("thick_lining").height
                visible: !base.validName;
                text: base.validationError;
                font: UM.Theme.getFont("small")
            }
        //}
        Cura.SecondaryButton {
            id: cancelButton
            anchors.top: errormessage.bottom
            anchors.right: parent.right
            anchors.margins: 15
            text: "Cancel";
            onClicked: base.reject();
        }
        Cura.PrimaryButton {
            anchors.top: errormessage.bottom
            anchors.right: cancelButton.left
            anchors.margins: 15
            text: "OK";
            onClicked: base.accept();
            enabled: base.validName;
            //isDefault: true;
        }


    }
    }
