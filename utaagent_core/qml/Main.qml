import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: win
    width: 1220; height: 820
    minimumWidth: 940; minimumHeight: 680
    visible: true
    title: "UTA · 歌词手帖"
    color: "#f4f3ef"
    font.family: "Microsoft YaHei UI"
    font.pixelSize: 14
    property color ink: "#243e36"
    property color muted: "#7e867f"
    onClosing: function(close) {
        if (backend.busy) {
            close.accepted = false
            toast.show("正在生成，请等待当前任务完成后关闭。")
        }
    }

    component SoftButton: Button {
        id: control
        property bool accent: false
        leftPadding: 18; rightPadding: 18
        implicitHeight: 42
        hoverEnabled: true
        contentItem: Text {
            text: control.text
            font: control.font
            color: control.accent ? "white" : win.ink
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            opacity: control.enabled ? 1 : 0.45
        }
        background: Rectangle {
            radius: 12
            color: control.accent ? (control.hovered ? "#396f5c" : "#285542") : (control.hovered ? "#e4e8df" : "#ecefe8")
            opacity: control.enabled ? 1 : 0.55
            Behavior on color { ColorAnimation { duration: 130 } }
            border.width: control.activeFocus ? 2 : 0
            border.color: "#96b6a3"
        }
    }
    component Field: TextField {
        implicitHeight: 42
        selectByMouse: true
        color: win.ink
        leftPadding: 12
        background: Rectangle { radius: 9; color: "#f6f7f3"; border.color: parent.activeFocus ? "#709985" : "#e1e5dc" }
    }
    component Caption: Label { color: win.muted; font.pixelSize: 12 }
    component Sheet: Dialog {
        modal: true
        anchors.centerIn: Overlay.overlay
        padding: 26
        header: Label {
            text: parent.title
            color: win.ink; font.pixelSize: 20; font.bold: true
            leftPadding: 26; topPadding: 22; bottomPadding: 12
        }
        background: Rectangle { color: "#fdfdfa"; radius: 22; border.color: "#e1e5dc" }
        Overlay.modal: Rectangle { color: "#6520362c" }
        enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 150 } }
    }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 32
        spacing: 24
        RowLayout {
            Layout.fillWidth: true
            Rectangle {
                width: 44; height: 44; radius: 14; color: win.ink
                Text { anchors.centerIn: parent; text: "詩"; color: "#f2e8d4"; font.pixelSize: 24; font.family: "Yu Mincho" }
            }
            ColumnLayout {
                spacing: 2
                Label { text: "UTA / 歌词手帖"; font.pixelSize: 20; font.bold: true; color: win.ink }
                Caption { text: "读懂每一句，收藏每一首。" }
            }
            Item { Layout.fillWidth: true }
            Caption { text: backend.modelLabel; elide: Text.ElideRight; Layout.maximumWidth: 200 }
            SoftButton { text: "设置  ↗"; objectName: "settingsButton"; onClicked: settingsDialog.open() }
        }

        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            spacing: 24
            Rectangle {
                Layout.fillHeight: true
                Layout.preferredWidth: 500
                Layout.fillWidth: true
                color: "#fdfdfa"; radius: 24; border.color: "#e4e7df"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 26; spacing: 14
                    Caption { text: "01  /  CREATE"; font.letterSpacing: 2 }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "从一段歌词开始"; color: win.ink; font.pixelSize: 25; font.bold: true }
                        Item { Layout.fillWidth: true }
                        ToolButton { text: "..."; font.pixelSize: 24; onClicked: inputMenu.open()
                            Menu {
                                id: inputMenu
                                MenuItem { text: "导入歌词 TXT"; onTriggered: backend.importLyrics() }
                                MenuItem { text: "手帖标题与主题"; onTriggered: settingsDialog.open() }
                                MenuItem { text: "查看生成日志"; onTriggered: logDialog.open() }
                            }
                        }
                    }
                    Caption { text: "粘贴日语歌词，保留你喜欢的换行。" }
                    Rectangle {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        radius: 14; color: "#f7f8f3"
                        ScrollView {
                            anchors.fill: parent; anchors.margins: 8; clip: true
                            TextArea {
                                id: lyrics
                                objectName: "lyricsInput"
                                placeholderText: "ここに、好きな歌詞を。\n\n在这里粘贴歌词…"
                                placeholderTextColor: "#a1aaa1"
                                color: "#30483e"; font.family: "Yu Gothic"; font.pixelSize: 18
                                wrapMode: TextEdit.Wrap
                                selectByMouse: true
                                padding: 16
                                background: null
                            }
                        }
                    }
                    RowLayout {
                        Caption { text: lyrics.text.trim() ? lyrics.text.trim().split("\n").length + " 行歌词" : "留一点时间，给喜欢的歌。" }
                        Item { Layout.fillWidth: true }
                        Caption { text: ["文库本","学习卡片","歌词本"][Math.max(0,["bunko","cards","lyrics"].indexOf(backend.settings.theme))] }
                    }
                    SoftButton {
                        objectName: "generateButton"
                        Layout.fillWidth: true; implicitHeight: 52
                        text: backend.busy ? "正在制作手帖…" : "生成 HTML 手帖   ↗"
                        accent: true
                        enabled: !backend.busy && lyrics.text.trim().length > 0
                        onClicked: backend.start(lyrics.text, bookTitle.text)
                    }
                    ProgressBar { Layout.fillWidth: true; visible: backend.busy; indeterminate: true }
                    Label { Layout.fillWidth: true; text: backend.status; color: win.muted; font.pixelSize: 12; wrapMode: Text.Wrap }
                }
            }

            ColumnLayout {
                Layout.preferredWidth: 490; Layout.fillWidth: true; Layout.fillHeight: true
                spacing: 14
                RowLayout {
                    ColumnLayout {
                        spacing: 6
                        Caption { text: "02  /  COLLECTION"; font.letterSpacing: 2 }
                        Label { text: backend.trash ? "回收站" : "我的书架"; color: win.ink; font.pixelSize: 26; font.bold: true }
                    }
                    Item { Layout.fillWidth: true }
                    SoftButton { text: "＋ 导入"; onClicked: backend.importHtml() }
                    ToolButton {
                        text: "..."; font.pixelSize: 24
                        onClicked: shelfMenu.open()
                        Menu {
                            id: shelfMenu
                            MenuItem { text: backend.trash ? "返回书架" : "查看回收站"; onTriggered: backend.toggleTrash() }
                            MenuItem { text: "刷新"; onTriggered: backend.refresh() }
                        }
                    }
                }
                Caption { text: backend.books.length + " 本手帖 · 单文件 HTML，随时阅读与分享" }
                Item {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    ListView {
                        id: bookList
                        anchors.fill: parent; clip: true
                        spacing: 12
                        model: backend.books
                        ScrollBar.vertical: ScrollBar {}
                        delegate: Rectangle {
                            id: card
                            required property var modelData
                            required property int index
                            width: bookList.width - 12; height: 132; radius: 18
                            color: "#fdfdfa"; border.color: "#e4e7df"
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 16; spacing: 16
                                Rectangle {
                                    Layout.preferredWidth: 68; Layout.fillHeight: true; radius: 7
                                    color: ["#dce5d7","#e9ddce","#d9e2e3"][card.index % 3]
                                    Rectangle { x: 5; width: 1; height: parent.height; color: "#abb6a3"; opacity: 0.5 }
                                    Text { anchors.centerIn: parent; text: "歌"; font.family: "Yu Mincho"; font.pixelSize: 28; color: "#5b7060" }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 8
                                    Label { text: card.modelData.title; font.pixelSize: 16; font.bold: true; color: win.ink; elide: Text.ElideRight; Layout.fillWidth: true }
                                    Caption { text: (card.modelData.created || "").replace("T","  ") }
                                    RowLayout {
                                        SoftButton { text: "阅读  ↗"; implicitHeight: 32; onClicked: backend.bookAction("open",card.modelData.id,"") }
                                        Item { Layout.fillWidth: true }
                                        ToolButton {
                                            text: "..."; font.pixelSize: 22
                                            onClicked: bookMenu.open()
                                            Menu {
                                                id: bookMenu
                                                MenuItem { text: "另存 HTML"; onTriggered: backend.bookAction("export",card.modelData.id,"") }
                                                MenuItem { text: "修改书架名称"; enabled: !backend.trash; onTriggered: { renameDialog.bookId = card.modelData.id; renameField.text = card.modelData.title; renameDialog.open() } }
                                                MenuItem { text: backend.trash ? "恢复到书架" : "移入回收站"; onTriggered: backend.bookAction("move",card.modelData.id,"") }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    Column {
                        visible: backend.books.length === 0
                        anchors.centerIn: parent; spacing: 14
                        Label { anchors.horizontalCenter: parent.horizontalCenter; text: "本"; color: "#b4c2ae"; font.pixelSize: 60; font.family: "Yu Mincho" }
                        Label { anchors.horizontalCenter: parent.horizontalCenter; text: backend.trash ? "回收站是空的" : "你的第一本手帖，从左边开始"; color: win.muted }
                        Caption { anchors.horizontalCenter: parent.horizontalCenter; text: "也可以导入已经保存的 HTML" }
                    }
                }
                Caption { Layout.fillWidth: true; wrapMode: Text.Wrap; text: "词条修改后，在阅读页下载 HTML，再导入书架即可收藏新版本。" }
            }
        }
    }

    Sheet {
        id: settingsDialog
        objectName: "settingsDialog"
        title: "手帖设置"
        width: 640; height: Math.min(win.height - 64, 730)
        onOpened: {
            const s = backend.settings
            endpoint.text=s.base_url; modelName.text=s.model; envName.text=s.api_key_env
            apiKey.text=backend.keyFor(s.api_key_env)
            mode.currentIndex=Math.max(0,mode.model.indexOf(s.output_mode))
            theme.currentIndex=Math.max(0,["bunko","cards","lyrics"].indexOf(s.theme))
            timeout.text=s.timeout; mecab.text=s.mecab; offline.checked=s.no_llm
            remember.checked=false
        }
        contentItem: ScrollView {
            clip: true
            ColumnLayout {
                width: settingsDialog.availableWidth
                spacing: 10
                Label { text: "阅读与排版"; color: win.ink; font.bold: true }
                Field { id: bookTitle; Layout.fillWidth: true; placeholderText: "手帖标题（留空使用歌词首行）" }
                ComboBox { id: theme; Layout.fillWidth: true; model: ["文库本","学习卡片","歌词本"] }
                Label { text: "模型与密钥"; color: win.ink; font.bold: true; Layout.topMargin: 10 }
                ComboBox {
                    Layout.fillWidth: true
                    model: ["选择服务预设","Qwen / 百炼","DeepSeek","自定义兼容接口"]
                    onActivated: {
                        if (currentIndex === 1) {
                            endpoint.text="https://dashscope.aliyuncs.com/compatible-mode/v1"; modelName.text="qwen-plus"; envName.text="DASHSCOPE_API_KEY"
                        } else if (currentIndex === 2) {
                            endpoint.text="https://api.deepseek.com"; modelName.text="deepseek-chat"; envName.text="DEEPSEEK_API_KEY"
                        } else if (currentIndex === 3) {
                            endpoint.text=""; modelName.text=""; envName.text="OPENAI_API_KEY"
                        }
                        apiKey.text=backend.keyFor(envName.text)
                    }
                }
                Caption { text: "接口地址 / Base URL" }
                Field { id: endpoint; Layout.fillWidth: true }
                Caption { text: "模型名称（可自由输入）" }
                Field { id: modelName; Layout.fillWidth: true }
                Caption { text: "密钥环境变量" }
                Field { id: envName; Layout.fillWidth: true; onEditingFinished: apiKey.text=backend.keyFor(text) }
                Field { id: apiKey; Layout.fillWidth: true; placeholderText: "API Key"; echoMode: TextInput.Password }
                CheckBox { id: remember; text: "保存密钥到用户环境变量，下次自动读取" }
                CheckBox { id: offline; text: "仅词典模式 · 不调用模型" }
                RowLayout {
                    Caption { text: "输出方式" }
                    ComboBox { id: mode; model: ["auto","json_schema","json_object","text"]; Layout.fillWidth: true }
                    Caption { text: "超时 / 秒" }
                    Field { id: timeout; Layout.preferredWidth: 80 }
                }
                Caption { text: "MeCab 路径（留空自动检测）" }
                Field { id: mecab; Layout.fillWidth: true }
                Caption { Layout.fillWidth: true; wrapMode: Text.Wrap; text: "歌词会发送至所选接口。密钥不写入手帖或普通配置；所有模型结果均经过本地校验。" }
            }
        }
        footer: RowLayout {
            spacing: 12
            Item { Layout.fillWidth: true }
            SoftButton { text: "取消"; onClicked: settingsDialog.close() }
            SoftButton {
                text: "保存设置"; accent: true
                Layout.rightMargin: 24; Layout.bottomMargin: 16; Layout.topMargin: 12
                onClicked: {
                    if (backend.configure({
                        base_url:endpoint.text.trim(), model:modelName.text.trim(),
                        api_key_env:envName.text.trim(), output_mode:mode.currentText,
                        theme:["bunko","cards","lyrics"][theme.currentIndex], timeout:timeout.text,
                        mecab:mecab.text.trim(), no_llm:offline.checked
                    },apiKey.text,remember.checked)) settingsDialog.close()
                }
            }
        }
    }
    Sheet {
        id: renameDialog
        title: "修改书架名称"
        property string bookId: ""
        width: 440
        ColumnLayout {
            width: parent.width
            Field { id: renameField; Layout.fillWidth: true }
            Caption { text: "仅修改书架名称，不改动 HTML 封面。" }
            SoftButton { text: "保存"; accent: true; onClicked: { if(renameField.text.trim()) { backend.bookAction("rename",renameDialog.bookId,renameField.text); renameDialog.close() } } }
        }
    }
    Sheet {
        id: logDialog
        title: "生成日志"
        width: 640; height: 420
        ScrollView { anchors.fill: parent; TextArea { text: backend.logs || "还没有生成记录。"; readOnly: true; wrapMode: TextEdit.Wrap; selectByMouse: true } }
    }
    Popup {
        id: toast
        property string message: ""
        function show(value) { message=value; open(); toastTimer.restart() }
        x: (win.width-width)/2; y: win.height-height-26
        width: Math.min(650,win.width-80); padding: 16
        background: Rectangle { radius: 12; color: "#283e34" }
        contentItem: Label { text: toast.message; color: "white"; wrapMode: Text.Wrap }
        Timer { id: toastTimer; interval: 5500; onTriggered: toast.close() }
    }
    Connections {
        target: backend
        function onNotice(message) { toast.show(message) }
        function onLyricsLoaded(text) { lyrics.text=text }
    }
}
