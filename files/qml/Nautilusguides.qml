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

    minimumWidth: 630 * screenScaleFactor
    minimumHeight: 300 * screenScaleFactor
    //title: catalog.i18nc("@label", "3D Printing Guides & Troubleshooting")
    Label{
      id: title
      anchors.horizontalCenter: parent.horizontalCenter
      anchors.top: parent.top
      text: "3D Printing Guides & Troubleshooting"
      font.bold: true
      font.pointSize: 18
      //Layout.columnSpan: 2
    }
    GridLayout {
      id: grids
      columns: 4
      columnSpacing: 50
      height: parent.height
      width: parent.width
      //anchors.horizontalCenter: parent.horizontalCenter
      anchors.top: title.bottom
      anchors.topMargin:20
        //Begin Quality Tile
          Rectangle {
            id: qualityimg
            Layout.row: 0
            anchors.leftMargin: 50
            anchors.left: parent.left
            //anchors.top: parent.top
            width: UM.Theme.getSize("toolbox_thumbnail_medium").width
            height: UM.Theme.getSize("toolbox_thumbnail_medium").height
            border.width: UM.Theme.getSize("default_lining").width
            border.color: UM.Theme.getColor("lining")

            Image {
              anchors.centerIn: parent
              width: UM.Theme.getSize("toolbox_thumbnail_medium").width - UM.Theme.getSize("narrow_margin").width
              height: UM.Theme.getSize("toolbox_thumbnail_medium").height - UM.Theme.getSize("narrow_margin").width
              source: "../img/3DP Quality Trouble Shooting.png"
            }
          }
          Label {
            id: qualitylabel
            anchors.bottom: qualityimg.verticalCenter
            anchors.left: qualityimg.right
            //Layout.column: 1
            //Layout.row: 0
            bottomPadding: 10
            leftPadding: 10
            text: "Print Quality Guide"
            font.bold: true
            font.pointSize: 14
          }

          Button {
                id: qualitybutton
                UM.I18nCatalog
                {
                    id: catalog
                    name: "cura"
                }
                //Layout.column: 1
                //Layout.row: 1

                anchors.margins: 10
                //topPadding: 10
                anchors.left: qualityimg.right
                anchors.top: qualityimg.verticalCenter
                text: "Open"//catalog1.i18nc("@action:button", "Open")
                onClicked: manager.openQualityGuide()
                //Layout.columnSpan:2
            }
            //Begin Design Tile

            Rectangle {
              id: designimg
              //anchors.top: qualityimg.bottom
              anchors.left: qualitylabel.right
              //Layout.column: 3
              Layout.row: 0
              anchors.leftMargin: 50
              width: UM.Theme.getSize("toolbox_thumbnail_medium").width
              height: UM.Theme.getSize("toolbox_thumbnail_medium").height
              border.width: UM.Theme.getSize("default_lining").width
              border.color: UM.Theme.getColor("lining")

              Image {
                anchors.centerIn: parent
                width: UM.Theme.getSize("toolbox_thumbnail_medium").width - UM.Theme.getSize("narrow_margin").width
                height: UM.Theme.getSize("toolbox_thumbnail_medium").height - UM.Theme.getSize("narrow_margin").width
                source: "../img/design.png"
              }
            }
            Label {
              id: designlabel
              anchors.bottom: designimg.verticalCenter
              anchors.left: designimg.right

              bottomPadding: 10
              leftPadding: 10
              text: "Design Rules"
              font.bold: true
              font.pointSize: 14
            }

            Button {
                  id: designbutton
                  UM.I18nCatalog
                  {
                      id: catalog1
                      name: "cura"
                  }
                  anchors.margins: 10
                  //leftPadding: 10
                  //topPadding: 10
                  //Layout.column: 4
                  //Layout.row: 1
                  anchors.left: designimg.right
                  anchors.top: designimg.verticalCenter
                  text: catalog1.i18nc("@action:button", "Open")
                  onClicked: manager.openDesignGuide()
                  //Layout.columnSpan:2
              }

            //Begin Slicing Tile
                Rectangle {
                  id: sliceimg
                  anchors.top: qualityimg.bottom
                  anchors.left: qualityimg.left
                  //Layout.column: 0
                  //Layout.row: 2
                  anchors.topMargin: 20
                  width: UM.Theme.getSize("toolbox_thumbnail_medium").width
                  height: UM.Theme.getSize("toolbox_thumbnail_medium").height
                  border.width: UM.Theme.getSize("default_lining").width
                  border.color: UM.Theme.getColor("lining")

                  Image {
                    anchors.centerIn: parent
                    width: UM.Theme.getSize("toolbox_thumbnail_medium").width - UM.Theme.getSize("narrow_margin").width
                    height: UM.Theme.getSize("toolbox_thumbnail_medium").height - UM.Theme.getSize("narrow_margin").width
                    source: "../img/slicing.png"
                  }
                }
                Label {
                  id: slicelabel
                  //Layout.column: 1
                  //Layout.row:2
                  anchors.bottom: sliceimg.verticalCenter
                  anchors.left: sliceimg.right
                  bottomPadding: 10
                  leftPadding: 10
                  text: "Slicing Guide"
                  font.bold: true
                  font.pointSize: 14
                }

                Button {
                      id: slicebutton
                      UM.I18nCatalog
                      {
                          id: catalog2
                          name: "cura"
                      }
                      anchors.margins: 10
                      //leftPadding: 10
                      //topPadding: 10
                      //Layout.column: 1
                      //Layout.row: 3
                      anchors.left: sliceimg.right
                      anchors.top: sliceimg.verticalCenter
                      text: catalog1.i18nc("@action:button", "Open")
                      onClicked: manager.openSlicingGuide()
                      //Layout.columnSpan:2
                  }
//Everything's working up to this point but the buttons are all way too low

                  //Begin Material Guide Tile
                  Rectangle {
                    id: materialimg
                    anchors.top: designimg.bottom
                    anchors.left: designimg.left
                    //Layout.column: 2
                    //Layout.row: 2
                    anchors.topMargin: 20
                    width: UM.Theme.getSize("toolbox_thumbnail_medium").width
                    height: UM.Theme.getSize("toolbox_thumbnail_medium").height
                    border.width: UM.Theme.getSize("default_lining").width
                    border.color: UM.Theme.getColor("lining")

                    Image {
                      anchors.centerIn: parent
                      width: UM.Theme.getSize("toolbox_thumbnail_medium").width - UM.Theme.getSize("narrow_margin").width
                      height: UM.Theme.getSize("toolbox_thumbnail_medium").height - UM.Theme.getSize("narrow_margin").width
                      source: "../img/material.png"
                    }
                  }
                  Label {
                    id: materiallabel
                    //Layout.column: 3
                    //Layout.row:2
                    anchors.bottom: materialimg.verticalCenter
                    anchors.left: materialimg.right
                    bottomPadding: 10
                    leftPadding: 10
                    text: "Material Guide"
                    font.bold: true
                    font.pointSize: 14
                  }

                  Button {
                        id: materialbutton
                        UM.I18nCatalog
                        {
                            id: catalog3
                            name: "cura"
                        }
                        anchors.margins: 10
                        //leftPadding: 10
                        //topPadding: 10
                        //Layout.column: 3
                        //Layout.row: 3
                        anchors.left: materialimg.right
                        anchors.top: materialimg.verticalCenter
                        text: catalog1.i18nc("@action:button", "Open")
                        onClicked: manager.openMaterialGuide()
                        //Layout.columnSpan:2
                    }
        } // end RowLayout

    } // end ColumnLayout
