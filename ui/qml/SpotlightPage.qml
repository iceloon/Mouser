import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "Theme.js" as Theme

Item {
    id: spotlightPage
    readonly property var theme: Theme.palette(uiState.darkMode)
    property var s: lm.strings

    readonly property var modes: [
        { id: "spotlight", label: s["spotlight.mode_spotlight"] || "Spotlight" },
        { id: "laser",     label: s["spotlight.mode_laser"]     || "Laser dot" }
    ]

    readonly property var swatches: [
        "#00d4aa", "#ffffff", "#ff4d4f", "#ffd666", "#4d9bff"
    ]

    ScrollView {
        id: pageScroll
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth

        Column {
            id: mainCol
            width: pageScroll.availableWidth
            spacing: 0

            // ── Header ──────────────────────────────────────────────
            Item {
                width: parent.width
                height: 96

                Column {
                    anchors {
                        left: parent.left
                        leftMargin: 36
                        verticalCenter: parent.verticalCenter
                    }
                    spacing: 4

                    Text {
                        text: s["spotlight.title"] || "Spotlight"
                        font { family: uiState.fontFamily; pixelSize: 24; bold: true }
                        color: spotlightPage.theme.textPrimary
                    }

                    Text {
                        text: s["spotlight.subtitle"]
                              || "A click-through highlight that follows the pointer — no Logi Options+ needed"
                        font { family: uiState.fontFamily; pixelSize: 13 }
                        color: spotlightPage.theme.textSecondary
                    }
                }
            }

            Rectangle {
                width: parent.width - 72
                height: 1
                color: spotlightPage.theme.border
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Item { width: 1; height: 20 }

            // ── Preview card ────────────────────────────────────────
            Rectangle {
                width: parent.width - 72
                anchors.horizontalCenter: parent.horizontalCenter
                height: previewContent.implicitHeight + 40
                radius: Theme.radius
                color: spotlightPage.theme.bgCard
                border.width: 1
                border.color: spotlightPage.theme.border

                Column {
                    id: previewContent
                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        margins: 20
                    }
                    spacing: 12

                    Row {
                        width: parent.width

                        Column {
                            width: parent.width - previewButton.width - 12
                            spacing: 3

                            Text {
                                text: s["spotlight.preview_title"] || "Try it"
                                font { family: uiState.fontFamily; pixelSize: 14; bold: true }
                                color: spotlightPage.theme.textPrimary
                            }

                            Text {
                                text: s["spotlight.preview_desc"]
                                      || "Lights the overlay for 2.5 seconds. While it is on, the shade covers the whole screen and the hole follows your pointer."
                                font { family: uiState.fontFamily; pixelSize: 12 }
                                color: spotlightPage.theme.textSecondary
                                wrapMode: Text.WordWrap
                                width: parent.width
                            }
                        }

                        Button {
                            id: previewButton
                            text: backend.spotlightActive
                                  ? (s["spotlight.stop"] || "Hide")
                                  : (s["spotlight.preview"] || "Preview")
                            anchors.verticalCenter: parent.verticalCenter
                            onClicked: backend.spotlightActive
                                       ? backend.toggleSpotlight()
                                       : backend.previewSpotlight()
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: tipText.implicitHeight + 20
                        radius: 10
                        color: Qt.rgba(0, 0.83, 0.67, uiState.darkMode ? 0.10 : 0.12)
                        border.width: 1
                        border.color: Qt.rgba(0, 0.83, 0.67, 0.35)

                        Text {
                            id: tipText
                            anchors {
                                left: parent.left
                                right: parent.right
                                verticalCenter: parent.verticalCenter
                                margins: 12
                            }
                            text: s["spotlight.bind_tip"]
                                  || "Bind any button to “Spotlight (hold to highlight)” on the Mouse page. With a Spotlight presenter in plug-and-play mode, hold the pointer key to light the screen."
                            font { family: uiState.fontFamily; pixelSize: 12 }
                            color: spotlightPage.theme.textPrimary
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            Item { width: 1; height: 16 }

            // ── Style card ──────────────────────────────────────────
            Rectangle {
                width: parent.width - 72
                anchors.horizontalCenter: parent.horizontalCenter
                height: styleContent.implicitHeight + 40
                radius: Theme.radius
                color: spotlightPage.theme.bgCard
                border.width: 1
                border.color: spotlightPage.theme.border

                Column {
                    id: styleContent
                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        margins: 20
                    }
                    spacing: 16

                    // Mode
                    Column {
                        width: parent.width
                        spacing: 8

                        Text {
                            text: s["spotlight.mode"] || "Pointer style"
                            font { family: uiState.fontFamily; pixelSize: 14; bold: true }
                            color: spotlightPage.theme.textPrimary
                        }

                        Row {
                            spacing: 8

                            Repeater {
                                model: spotlightPage.modes

                                delegate: Rectangle {
                                    width: 132
                                    height: 36
                                    radius: 9
                                    readonly property bool selected: backend.spotlightMode === modelData.id
                                    color: selected
                                           ? Qt.rgba(0, 0.83, 0.67, 0.18)
                                           : "transparent"
                                    border.width: 1
                                    border.color: selected
                                                  ? spotlightPage.theme.accent
                                                  : spotlightPage.theme.border

                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData.label
                                        font { family: uiState.fontFamily; pixelSize: 12 }
                                        color: selected
                                               ? spotlightPage.theme.accent
                                               : spotlightPage.theme.textSecondary
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: backend.setSpotlightMode(modelData.id)
                                    }
                                }
                            }
                        }
                    }

                    // Radius
                    Column {
                        width: parent.width
                        spacing: 6

                        Row {
                            width: parent.width

                            Text {
                                width: parent.width - radiusValue.width
                                text: s["spotlight.radius"] || "Spot size"
                                font { family: uiState.fontFamily; pixelSize: 13; bold: true }
                                color: spotlightPage.theme.textPrimary
                            }

                            Text {
                                id: radiusValue
                                text: backend.spotlightRadius + " px"
                                font { family: uiState.fontFamily; pixelSize: 12 }
                                color: spotlightPage.theme.textSecondary
                            }
                        }

                        Slider {
                            width: parent.width
                            from: 60
                            to: 600
                            stepSize: 10
                            value: backend.spotlightRadius
                            onMoved: backend.setSpotlightRadius(value)
                        }
                    }

                    // Dim
                    Column {
                        width: parent.width
                        spacing: 6
                        opacity: backend.spotlightMode === "spotlight" ? 1.0 : 0.4
                        enabled: backend.spotlightMode === "spotlight"

                        Row {
                            width: parent.width

                            Text {
                                width: parent.width - dimValue.width
                                text: s["spotlight.dim"] || "Background shade"
                                font { family: uiState.fontFamily; pixelSize: 13; bold: true }
                                color: spotlightPage.theme.textPrimary
                            }

                            Text {
                                id: dimValue
                                text: Math.round(backend.spotlightDim * 100) + " %"
                                font { family: uiState.fontFamily; pixelSize: 12 }
                                color: spotlightPage.theme.textSecondary
                            }
                        }

                        Slider {
                            width: parent.width
                            from: 0
                            to: 95
                            stepSize: 5
                            value: Math.round(backend.spotlightDim * 100)
                            onMoved: backend.setSpotlightDim(value / 100.0)
                        }
                    }

                    // Ring width
                    Column {
                        width: parent.width
                        spacing: 6

                        Row {
                            width: parent.width

                            Text {
                                width: parent.width - ringValue.width
                                text: s["spotlight.ring"] || "Ring thickness"
                                font { family: uiState.fontFamily; pixelSize: 13; bold: true }
                                color: spotlightPage.theme.textPrimary
                            }

                            Text {
                                id: ringValue
                                text: backend.spotlightRingWidth + " px"
                                font { family: uiState.fontFamily; pixelSize: 12 }
                                color: spotlightPage.theme.textSecondary
                            }
                        }

                        Slider {
                            width: parent.width
                            from: 0
                            to: 8
                            stepSize: 1
                            value: backend.spotlightRingWidth
                            onMoved: backend.setSpotlightRingWidth(value)
                        }
                    }

                    // Color
                    Column {
                        width: parent.width
                        spacing: 8

                        Text {
                            text: s["spotlight.color"] || "Colour"
                            font { family: uiState.fontFamily; pixelSize: 13; bold: true }
                            color: spotlightPage.theme.textPrimary
                        }

                        Row {
                            spacing: 10

                            Repeater {
                                model: spotlightPage.swatches

                                delegate: Rectangle {
                                    width: 30
                                    height: 30
                                    radius: 15
                                    color: modelData
                                    border.width: backend.spotlightColor === modelData ? 3 : 1
                                    border.color: backend.spotlightColor === modelData
                                                  ? spotlightPage.theme.textPrimary
                                                  : spotlightPage.theme.border

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: backend.setSpotlightColor(modelData)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Item { width: 1; height: 28 }
        }
    }
}
