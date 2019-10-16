import QtQuick 2.4
import QtQuick.Controls 1.4
import QtQuick.Controls.Styles 1.1
import QtQuick.Layouts 1.1
import QtQuick.Dialogs 1.2
import QtQuick.Window 2.1

import UM 1.2 as UM
import Cura 1.0 as Cura


UM.Dialog
{
    id: base
    property int recwidth: Math.floor(250*screenScaleFactor)

    width: Math.floor(600 * screenScaleFactor)
    minimumWidth: width
    maximumWidth: width
    minimumHeight: Math.floor(470 * screenScaleFactor)
    maximumHeight: minimumHeight
    title: catalog.i18nc("@label", "Guides & Resources")
    Rectangle {
      id: usermanual
      width: parent.width - 20
      height: UM.Theme.getSize("toolbox_thumbnail_large").height
      anchors.horizontalCenter: parent.horizontalCenter
      anchors.top: parent.top
      anchors.topMargin: 20
      border.width: UM.Theme.getSize("default_lining").width
      border.color: UM.Theme.getColor("lining")
      Image {
        id: userimg
        anchors.left: usermanual.left
        anchors.verticalCenter: usermanual.verticalCenter
        anchors.margins: 5
        width:UM.Theme.getSize("toolbox_thumbnail_large").height - 10
        height: UM.Theme.getSize("toolbox_thumbnail_large").height - 10
        source: "../img/usermanual.png"
      }
      Label {
        id: usermanuallabel
        anchors.top: usermanual.top
        anchors.topMargin: 15
        anchors.left: userimg.right
        leftPadding: 10
        text: "User Manual & Resources"
        font.pointSize: 16
      }
      Label{
        id: usermanualinfo
        anchors.top:usermanuallabel.bottom
        anchors.topMargin: 5
        anchors.left: userimg.right
        width: usermanual.width - userimg.width - 10
        wrapMode: Label.WordWrap
        leftPadding: 10
        text: "Resources for the Nautilus 3D printer. Here you will find the Nautilus user manual, printer firmware and configuration, as well as source files for the Nautilus."
        font.pointSize: 12
      }
      Button {
        id: usermanualbutton
        anchors.leftMargin: 10
        anchors.left: userimg.right
        anchors.top: usermanualinfo.bottom
        anchors.topMargin: 10
        text: "Open"
        onClicked: manager.openUserManual()
      }
    }

    Label{
      id: title
      anchors.horizontalCenter: parent.horizontalCenter
      anchors.top: usermanual.bottom
      anchors.topMargin:20
      text: "——     Guides     ——"
      font.bold: true
      font.pointSize: 16
      //Layout.columnSpan: 2
    }
    GridLayout {
      id: grids
      columns: 2
      //columnSpacing: 20
      height: 2*parent.height/3
      width: parent.width
      anchors.horizontalCenter: parent.horizontalCenter
      anchors.top: title.bottom

        //Begin Quality Tile
          Rectangle {
            id: qualityimg
            Layout.row: 0
            anchors.leftMargin: 10
            anchors.left: parent.left
            //anchors.top: parent.top
            width: recwidth//UM.Theme.getSize("toolbox_thumbnail_medium").width
            height: UM.Theme.getSize("toolbox_thumbnail_medium").height
            border.width: UM.Theme.getSize("default_lining").width
            border.color: UM.Theme.getColor("lining")

            Image {
              id: qualim
              anchors.left: qualityimg.left
              anchors.verticalCenter: qualityimg.verticalCenter
              anchors.margins: 5
              width: UM.Theme.getSize("toolbox_thumbnail_medium").width - 10
              height: UM.Theme.getSize("toolbox_thumbnail_medium").height - 10
              source: "../img/3DP Quality Trouble Shooting.png"
            }
            Label {
              id: qualitylabel
              anchors.top: qualim.top
              anchors.topMargin: 10
              anchors.left: qualim.right
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

                  anchors.leftMargin: 10
                  //topPadding: 10
                  anchors.left: qualim.right
                  anchors.top: qualim.verticalCenter
                  text: "Open"//catalog1.i18nc("@action:button", "Open")
                  onClicked: manager.openQualityGuide()
                  //Layout.columnSpan:2
              }
          }

            //Begin Design Tile

            Rectangle {
              id: designimg
              //anchors.top: qualityimg.bottom
              //anchors.left: qualitylabel.right
              Layout.column: 1
              Layout.row: 0
              anchors.rightMargin: 10
              anchors.right:parent.right
              width: recwidth//UM.Theme.getSize("toolbox_thumbnail_medium").width
              height: UM.Theme.getSize("toolbox_thumbnail_medium").height
              border.width: UM.Theme.getSize("default_lining").width
              border.color: UM.Theme.getColor("lining")

              Image {
                id:desim
                anchors.left: designimg.left
                anchors.verticalCenter: designimg.verticalCenter
                anchors.margins: 5
                width: UM.Theme.getSize("toolbox_thumbnail_medium").width - 10
                height: UM.Theme.getSize("toolbox_thumbnail_medium").height - 10
                source: "../img/design.png"
              }
              Label {
                id: designlabel
                anchors.top:desim.top
                anchors.topMargin:10
                anchors.left:desim.right
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
                    anchors.leftMargin: 10
                    //leftPadding: 10
                    //topPadding: 10
                    //Layout.column: 4
                    //Layout.row: 1
                    anchors.left: desim.right
                    anchors.top: desim.verticalCenter
                    text: catalog1.i18nc("@action:button", "Open")
                    onClicked: manager.openDesignGuide()
                    //Layout.columnSpan:2
                }
            }


            //Begin Slicing Tile
                Rectangle {
                  id: sliceimg
                  anchors.leftMargin: 10
                  anchors.left: parent.left
                  //Layout.column: 0
                  anchors.top: qualityimg.bottom
                  anchors.topMargin: 20
                  width: recwidth//UM.Theme.getSize("toolbox_thumbnail_medium").width
                  height: UM.Theme.getSize("toolbox_thumbnail_medium").height
                  border.width: UM.Theme.getSize("default_lining").width
                  border.color: UM.Theme.getColor("lining")

                  Image {
                    id:slicim
                    anchors.left: sliceimg.left
                    anchors.verticalCenter: sliceimg.verticalCenter
                    anchors.margins: 5
                    width: UM.Theme.getSize("toolbox_thumbnail_medium").width - 10
                    height: UM.Theme.getSize("toolbox_thumbnail_medium").height - 10
                    source: "../img/slicing.png"
                  }
                  Label {
                    id: slicelabel
                    //Layout.column: 1
                    //Layout.row:2
                    anchors.top: slicim.top
                    anchors.topMargin: 10
                    anchors.left: slicim.right
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
                        anchors.leftMargin: 10
                        //leftPadding: 10
                        //topPadding: 10
                        //Layout.column: 1
                        //Layout.row: 3
                        anchors.left: slicim.right
                        anchors.top: slicim.verticalCenter
                        text: catalog1.i18nc("@action:button", "Open")
                        onClicked: manager.openSlicingGuide()
                        //Layout.columnSpan:2
                    }
                }


                  //Begin Material Guide Tile
                  Rectangle {
                    id: materialimg
                    anchors.top: qualityimg.bottom
                    anchors.right: parent.right
                    anchors.rightMargin: 10
                    anchors.topMargin: 20
                    //Layout.column: 2
                    //Layout.row: 2
                    width: recwidth//UM.Theme.getSize("toolbox_thumbnail_medium").width
                    height: UM.Theme.getSize("toolbox_thumbnail_medium").height
                    border.width: UM.Theme.getSize("default_lining").width
                    border.color: UM.Theme.getColor("lining")

                    Image {
                      id: matim
                      anchors.left: materialimg.left
                      anchors.verticalCenter: materialimg.verticalCenter
                      anchors.margins:5
                      width: UM.Theme.getSize("toolbox_thumbnail_medium").width - 10
                      height: UM.Theme.getSize("toolbox_thumbnail_medium").height - 10
                      source: "../img/material.png"
                    }
                    Label {
                      id: materiallabel
                      //Layout.column: 3
                      //Layout.row:2
                      anchors.top: matim.top
                      anchors.topMargin: 10
                      anchors.left: matim.right
                      bottomPadding: 10
                      leftPadding: 10
                      text: "Material Guide"
                      font.bold: true
                      font.pointSize: 14
                    }

                    Button {
                          id: materialbutton
                          //iconName: "list-add"
                          anchors.leftMargin: 10
                          //leftPadding: 10
                          //topPadding: 10
                          //Layout.column: 3
                          //Layout.row: 3
                          anchors.left: matim.right
                          anchors.top: matim.verticalCenter
                          text: catalog1.i18nc("@action:button", "Open")
                          MouseArea {
                              anchors.fill: parent
                              cursorShape: Qt.PointingHandCursor
                              hoverEnabled: true
                              onClicked: manager.openMaterialGuide()
                          }
                          //Layout.columnSpan:2
                      }
                  }
        } // end RowLayout

    } // end ColumnLayout
