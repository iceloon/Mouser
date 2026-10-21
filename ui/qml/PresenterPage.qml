import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "Theme.js" as Theme

Item {
    id: presenterPage
    readonly property var theme: Theme.palette(uiState.darkMode)
    property var s: lm.strings

    function indexForAction(key) {
        var want = backend.presenterAction(key)
        var items = backend.allActions
        for (var i = 0; i < items.length; i++) {
            if (items[i].id === want)
                return i
        }
        return 0
    }

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
                        text: s["presenter.title"] || "Presenter"
                        font { family: uiState.fontFamily; pixelSize: 24; bold: true }
                        color: presenterPage.theme.textPrimary
                    }

                    Text {
                        text: s["presenter.subtitle"]
                              || "Logitech Spotlight remote — pointer key, page keys and connection state"
                        font { family: uiState.fontFamily; pixelSize: 13 }
                        color: presenterPage.theme.textSecondary
                    }
                }
            }

            Rectangle {
                width: parent.width - 72
                height: 1
                color: presenterPage.theme.border
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Item { width: 1; height: 20 }

            // ── Status card ─────────────────────────────────────────
            Rectangle {
                width: parent.width - 72
                anchors.horizontalCenter: parent.horizontalCenter
                height: statusColumn.implicitHeight + 40
                radius: Theme.radius
                color: presenterPage.theme.bgCard
                border.width: 1
                border.color: presenterPage.theme.border

                Column {
                    id: statusColumn
                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        margins: 20
                    }
                    spacing: 10

                    Row {
                        spacing: 10

                        Rectangle {
                            width: 10
                            height: 10
                            radius: 5
                            anchors.verticalCenter: parent.verticalCenter
                            color: backend.presenterConnected
                                   ? presenterPage.theme.accent
                                   : presenterPage.theme.textSecondary
                        }

                        Text {
                            text: backend.presenterConnected
                                  ? (backend.presenterName + "  ·  "
                                     + (backend.presenterTransport === "bluetooth"
                                        ? (s["presenter.bluetooth"] || "Bluetooth")
                                        : (s["presenter.usb"] || "USB receiver")))
                                  : (s["presenter.not_connected"] || "No presenter detected")
                            font { family: uiState.fontFamily; pixelSize: 14; bold: true }
                            color: presenterPage.theme.textPrimary
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    Text {
                        width: parent.width
                        text: s["presenter.status_hint"]
                              || "Plug the receiver (or pair over Bluetooth) and the remote is picked up automatically — no Logi Options+ required."
                        font { family: uiState.fontFamily; pixelSize: 12 }
                        color: presenterPage.theme.textSecondary
                        wrapMode: Text.WordWrap
                    }

                    Row {
                        width: parent.width
                        spacing: 12

                        Text {
                            width: parent.width - enabledSwitch.width
                            text: s["presenter.enabled"] || "Handle this presenter"
                            font { family: uiState.fontFamily; pixelSize: 13 }
                            color: presenterPage.theme.textPrimary
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Switch {
                            id: enabledSwitch
                            checked: backend.presenterEnabled
                            onToggled: backend.setPresenterEnabled(checked)
                        }
                    }
                }
            }

            Item { width: 1; height: 16 }

            // ── Behaviour card ──────────────────────────────────────
            Rectangle {
                width: parent.width - 72
                anchors.horizontalCenter: parent.horizontalCenter
                height: behaviourColumn.implicitHeight + 40
                radius: Theme.radius
                color: presenterPage.theme.bgCard
                border.width: 1
                border.color: presenterPage.theme.border
                opacity: backend.presenterEnabled ? 1.0 : 0.45

                Column {
                    id: behaviourColumn
                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        margins: 20
                    }
                    spacing: 14

                    Row {
                        width: parent.width
                        spacing: 12

                        Column {
                            width: parent.width - pointerSwitch.width
                            spacing: 2
                            Text {
                                text: s["presenter.pointer"] || "Pointer key lights the spotlight"
                                font { family: uiState.fontFamily; pixelSize: 13; bold: true }
                                color: presenterPage.theme.textPrimary
                            }
                            Text {
                                text: s["presenter.pointer_desc"]
                                      || "While the pointer key is held, the screen dims and the hole follows the remote."
                                font { family: uiState.fontFamily; pixelSize: 11 }
                                color: presenterPage.theme.textSecondary
                                wrapMode: Text.WordWrap
                                width: parent.width
                            }
                        }

                        Switch {
                            id: pointerSwitch
                            checked: backend.presenterPointerOverlay
                            enabled: backend.presenterEnabled
                            anchors.verticalCenter: parent.verticalCenter
                            onToggled: backend.setPresenterPointerOverlay(checked)
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: presenterPage.theme.border
                    }

                    Row {
                        width: parent.width
                        spacing: 12

                        Column {
                            width: parent.width - takeoverSwitch.width
                            spacing: 2
                            Text {
                                text: s["presenter.takeover"] || "Take over the arrow keys"
                                font { family: uiState.fontFamily; pixelSize: 13; bold: true }
                                color: presenterPage.theme.textPrimary
                            }
                            Text {
                                text: s["presenter.takeover_desc"]
                                      || "Next/Back send Left/Right arrows. Windows cannot tell which device sent a key, so this is global while enabled — leave it off if you use the arrow keys for other apps."
                                font { family: uiState.fontFamily; pixelSize: 11 }
                                color: presenterPage.theme.textSecondary
                                wrapMode: Text.WordWrap
                                width: parent.width
                            }
                        }

                        Switch {
                            id: takeoverSwitch
                            checked: backend.presenterTakeoverKeys
                            enabled: backend.presenterEnabled
                            anchors.verticalCenter: parent.verticalCenter
                            onToggled: backend.setPresenterTakeoverKeys(checked)
                        }
                    }
                }
            }

            Item { width: 1; height: 16 }

            // ── Button mapping card ─────────────────────────────────
            Rectangle {
                width: parent.width - 72
                anchors.horizontalCenter: parent.horizontalCenter
                height: mappingColumn.implicitHeight + 40
                radius: Theme.radius
                color: presenterPage.theme.bgCard
                border.width: 1
                border.color: presenterPage.theme.border
                opacity: backend.presenterTakeoverKeys ? 1.0 : 0.45

                Column {
                    id: mappingColumn
                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        margins: 20
                    }
                    spacing: 12

                    Text {
                        text: s["presenter.mapping_title"] || "Button actions (only used while takeover is on)"
                        font { family: uiState.fontFamily; pixelSize: 13; bold: true }
                        color: presenterPage.theme.textPrimary
                    }

                    Row {
                        width: parent.width
                        spacing: 12

                        Text {
                            width: 90
                            text: s["presenter.next"] || "Next"
                            font { family: uiState.fontFamily; pixelSize: 12 }
                            color: presenterPage.theme.textSecondary
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        ComboBox {
                            id: nextCombo
                            width: parent.width - 110
                            model: backend.allActions
                            textRole: "label"
                            Component.onCompleted: currentIndex = presenterPage.indexForAction("presenter_next")
                            onActivated: backend.setMapping("presenter_next", backend.allActions[currentIndex].id)
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: 12

                        Text {
                            width: 90
                            text: s["presenter.prev"] || "Back"
                            font { family: uiState.fontFamily; pixelSize: 12 }
                            color: presenterPage.theme.textSecondary
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        ComboBox {
                            id: prevCombo
                            width: parent.width - 110
                            model: backend.allActions
                            textRole: "label"
                            Component.onCompleted: currentIndex = presenterPage.indexForAction("presenter_prev")
                            onActivated: backend.setMapping("presenter_prev", backend.allActions[currentIndex].id)
                        }
                    }
                }
            }

            Item { width: 1; height: 28 }
        }
    }
}
