import json
import sys
import math
from functools import partial

from PySide6 import QtWidgets
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

import api
import config
from helpers import create_circular_pixmap
from utils import sql
from utils.sql import check_database
# from utils.helpers import STYLE  # Imported to reduce token count of gui

BOTTOM_CORNER_X = 400
BOTTOM_CORNER_Y = 450

PIN_STATE = False

PERSONALITY_STATE = False
JAILBREAK_STATE = False
OPEN_INTERPRETER_STATE = 0
REACT_STATE = 0

PRIMARY_COLOR = "#363636"
SECONDARY_COLOR = "#535353"
TEXT_COLOR = "#999999"
BORDER_COLOR = "#888"

STYLE = f"""
QWidget {{
    background-color: {PRIMARY_COLOR};
    border-radius: 12px;
}}
QTextEdit {{
    background-color: {SECONDARY_COLOR};
    border-radius: 12px;
    color: #FFF;
    padding-left: 5px;
}}
QTextEdit.msgbox {{
    background-color: {SECONDARY_COLOR};
    border-radius: 12px;
    border-top-right-radius: 0px;
    border-bottom-right-radius: 0px;
}}
QPushButton.resend {{
    background-color: none;
    border-radius: 12px;
}}
QPushButton.resend:hover {{
    background-color: #777;
    border-radius: 12px;
}}
QPushButton.rerun {{
    background-color: {PRIMARY_COLOR};
}}
QPushButton.send {{
    background-color: {SECONDARY_COLOR};
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
    border-top-left-radius: 0px;
    border-bottom-left-radius: 0px;
    color: {TEXT_COLOR};
}}
QPushButton:hover {{
    background-color: #444;
}}
QPushButton.send:hover {{
    background-color: #537373;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
    border-top-left-radius: 0px;
    border-bottom-left-radius: 0px;
    color: {TEXT_COLOR};
}}
QPushButton {{
    color: {TEXT_COLOR};
    border-radius: 3px;
}}
QPushButton.menuitem {{
    color: {TEXT_COLOR};
    border-radius: 3px;
}}
QPushButton#homebutton:checked {{
    background-color: none;
    color: {TEXT_COLOR};
}}
QPushButton#homebutton:checked:hover {{
    background-color: #444;
    color: {TEXT_COLOR};
}}
QPushButton:checked {{
    background-color: #444;
    border-radius: 3px;
}}
QPushButton:checked:hover {{
    background-color: #444;
    border-radius: 3px;
}}
QLineEdit {{
    color: {TEXT_COLOR};
}}
QLineEdit:disabled {{
    color: #4d4d4d;
}}
QLabel {{
    color: {TEXT_COLOR};
    padding-right: 10px; 
}}
QSpinBox {{
    color: {TEXT_COLOR};
}}
QCheckBox::indicator:unchecked {{
    border: 1px solid #2b2b2b;
    background: {TEXT_COLOR};
}}
QCheckBox::indicator:checked {{
    border: 1px solid #2b2b2b;
    background: {TEXT_COLOR} url("./utils/resources/icon-tick.svg") no-repeat center center;
}}
QCheckBox::indicator:unchecked:disabled {{
    border: 1px solid #2b2b2b;
    background: #424242;
}}
QCheckBox::indicator:checked:disabled {{
    border: 1px solid #2b2b2b;
    background: #424242;
}}
QWidget.central {{
    border-radius: 12px;
    border-top-left-radius: 30px;
}}
QTextEdit.user {{
    background-color: {SECONDARY_COLOR};
    color: #d1d1d1;
    border-radius: 12px;
    border-bottom-left-radius: 0px;
    /* border-top-right-radius: 0px;*/
}}
QTextEdit.assistant {{
    background-color: {SECONDARY_COLOR};
    color: #9bbbcf;
    border-radius: 12px;
    border-bottom-left-radius: 0px;
    /* border-top-right-radius: 0px;*/
}}
QTextEdit.code {{
    background-color: {PRIMARY_COLOR};
    color: {TEXT_COLOR};
}}
QScrollBar:vertical {{
    width: 0px;
}}
"""

class TitleButtonBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.main = parent
        self.setObjectName("TitleBarWidget")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(20)
        sizePolicy = QSizePolicy()
        sizePolicy.setHorizontalPolicy(QSizePolicy.Policy.Fixed)

        self.btn_minimise = self.TitleBarButtonMin(parent=self)
        self.btn_pin = self.TitleBarButtonPin(parent=self)
        self.btn_close = self.TitleBarButtonClose(parent=self)

        self.layout = QHBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addStretch(1)
        self.layout.addWidget(self.btn_minimise)
        self.layout.addWidget(self.btn_pin)
        self.layout.addWidget(self.btn_close)

        self.setMouseTracking(True)

        self.setAttribute(Qt.WA_TranslucentBackground, True)

    class TitleBarButtonPin(QPushButton):
        def __init__(self, parent=None):
            super().__init__(parent=parent)
            self.setFixedHeight(20)
            self.setFixedWidth(20)
            self.clicked.connect(self.toggle_pin)
            self.icon = QIcon(QPixmap("./utils/resources/icon-pin-off.png"))
            self.setIcon(self.icon)

        def toggle_pin(self):
            global PIN_STATE
            PIN_STATE = not PIN_STATE
            icon_iden = "on" if PIN_STATE else "off"
            icon_file = f"./utils/resources/icon-pin-{icon_iden}.png"
            self.icon = QIcon(QPixmap(icon_file))
            self.setIcon(self.icon)

    class TitleBarButtonMin(QPushButton):
        def __init__(self, parent=None):
            super().__init__(parent=parent)
            self.parent = parent
            self.setFixedHeight(20)
            self.setFixedWidth(20)
            self.clicked.connect(self.window_action)
            self.icon = QIcon(QPixmap("./utils/resources/minus.png"))
            self.setIcon(self.icon)

        def window_action(self):
            self.parent.main.collapse()
            if self.window().isMinimized():
                self.window().showNormal()
            else:
                self.window().showMinimized()

    class TitleBarButtonClose(QPushButton):

        def __init__(self, parent):
            super().__init__(parent=parent)
            self.setFixedHeight(20)
            self.setFixedWidth(20)
            self.clicked.connect(self.closeApp)
            self.icon = QIcon(QPixmap("./utils/resources/close.png"))
            self.setIcon(self.icon)

        def closeApp(self):
            self.parent().main.window().close()
            # self.window().close()
            # sys.exit()



class ContentPage(QWidget):
    def __init__(self, main, title=''):
        super().__init__(parent=main)

        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.back_button = Back_Button(main)
        self.label = QLabel(title)

        font = self.label.font()
        font.setPointSize(15)
        self.label.setFont(font)
        self.label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.title_layout = QHBoxLayout()
        self.title_layout.setSpacing(20)
        self.title_layout.addWidget(self.back_button)
        self.title_layout.addWidget(self.label)

        self.title_container = QWidget()
        self.title_container.setLayout(self.title_layout)

        # self.title_container.mouseEntered.connect(self.show_new_agent_button)
        # self.title_container.mouseLeft.connect(self.hide_new_agent_button)

        self.layout.addWidget(self.title_container)

        if title != 'Agents':
            self.title_layout.addStretch()

    # def event(self, event):
    #     if event.type() == QEvent.Enter:
    #         self.on_mouse_enter()
    #     elif event.type() == QEvent.Leave:
    #         self.on_mouse_leave()
    #     return super().event(event)

    # def on_mouse_enter(self):
    #     # Show the button when the mouse enters the widget's area
    #     if hasattr(self, 'new_agent_button'):
    #         self.new_agent_button.setVisible(True)
    #
    # def on_mouse_leave(self):
    #     # Hide the button when the mouse leaves the widget's area
    #     if hasattr(self, 'new_agent_button'):
    #         self.new_agent_button.setVisible(False)


    # def on_mouse_enter(self):
    #     # Show the button when the mouse enters the widget's area
    #     if hasattr(self, 'btn_new_agent'):
    #         self.btn_new_agent.setVisible(True)
    #
    # def on_mouse_leave(self):
    #     # Hide the button when the mouse leaves the widget's area
    #     if hasattr(self, 'btn_new_agent'):
    #         self.btn_new_agent.setVisible(False)
    # def show_new_agent_button(self):
    #     if hasattr(self, 'btn_new_agent'):  # Check if new_agent_button is an attribute of the current instance
    #         self.btn_new_agent.setVisible(True)
    #
    # def hide_new_agent_button(self):
    #     if hasattr(self, 'btn_new_agent'):
    #         self.btn_new_agent.setVisible(False)


class Back_Button(QPushButton):
    def __init__(self, main):
        super().__init__(parent=main, icon=QIcon())
        self.main = main
        self.clicked.connect(self.go_back)
        self.icon = QIcon(QPixmap("./utils/resources/icon-back.png"))
        self.setIcon(self.icon)
        self.setFixedSize(50, 50)
        self.setIconSize(QSize(50, 50))

    def go_back(self):
        self.main.content.setCurrentWidget(self.main.page_chat)
        self.main.sidebar.btn_new_context.setChecked(True)


class Page_Settings(ContentPage):
    def __init__(self, main):
        super().__init__(main=main, title='Settings')
        self.main = main

        self.settings_sidebar = self.Settings_SideBar(main=main, parent=self)

        self.content = QStackedWidget(self)
        self.page_system = self.Page_System_Settings(self)
        self.page_api = self.Page_API_Settings(self)
        self.page_attachment = self.Page_Attachment_Settings(self)
        self.content.addWidget(self.page_system)
        self.content.addWidget(self.page_api)
        self.content.addWidget(self.page_attachment)

        # H layout for lsidebar and content
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.settings_sidebar)
        input_layout.addWidget(self.content)
        # input_layout.addLayout(self.form_layout)

        # Create a QWidget to act as a container for the
        input_container = QWidget()
        input_container.setLayout(input_layout)

        # Adding input layout to the main layout
        self.layout.addWidget(input_container)

        self.layout.addStretch(1)

    class Settings_SideBar(QWidget):
        def __init__(self, main, parent):
            super().__init__(parent=main)
            self.main = main
            self.parent = parent
            self.setObjectName("SettingsSideBarWidget")
            self.setAttribute(Qt.WA_StyledBackground, True)
            self.setProperty("class", "sidebar")

            font = QFont()
            font.setPointSize(13)  # Set font size to 20 points

            self.btn_system = self.Settings_SideBar_Button(main=main, text='System')
            self.btn_system.setFont(font)
            self.btn_system.setChecked(True)
            self.btn_api = self.Settings_SideBar_Button(main=main, text='API')
            self.btn_api.setFont(font)
            self.btn_attachments = self.Settings_SideBar_Button(main=main, text='Attachments')
            self.btn_attachments.setFont(font)

            self.layout = QVBoxLayout(self)
            self.layout.setSpacing(0)
            self.layout.setContentsMargins(0, 0, 0, 0)

            # Create a button group and add buttons to it
            self.button_group = QButtonGroup(self)
            self.button_group.addButton(self.btn_system, 0)  # 0 is the ID associated with the button
            self.button_group.addButton(self.btn_api, 1)
            self.button_group.addButton(self.btn_attachments, 2)

            # Connect button toggled signal
            self.button_group.buttonToggled[QAbstractButton, bool].connect(self.onButtonToggled)

            # self.layout.addStretch(1)

            self.layout.addWidget(self.btn_system)
            self.layout.addWidget(self.btn_api)
            self.layout.addWidget(self.btn_attachments)
            self.layout.addStretch(1)

        def onButtonToggled(self, button, checked):
            if checked:
                index = self.button_group.id(button)
                self.parent.content.setCurrentIndex(index)

        def updateButtonStates(self):
            # Check the appropriate button based on the current page
            stacked_widget = self.parent.content
            self.btn_system.setChecked(stacked_widget.currentWidget() == self.btn_system)
            self.btn_api.setChecked(stacked_widget.currentWidget() == self.btn_api)

        class Settings_SideBar_Button(QPushButton):
            def __init__(self, main, text=''):
                super().__init__(parent=main, icon=QIcon())
                self.main = main
                self.setProperty("class", "menuitem")
                # self.clicked.connect(self.goto_system_settings)
                self.setText(text)
                self.setFixedSize(100, 30)
                self.setCheckable(True)

    class Page_System_Settings(QWidget):
        def __init__(self, parent):
            super().__init__(parent=parent)
            self.parent = parent
            self.form_layout = QFormLayout()

            # Example for integer input
            self.decay_at_idle_count = NoWheelSpinBox()
            self.form_layout.addRow(QLabel('Decay at idle count:'), self.decay_at_idle_count)

            # Example for text input
            self.bg_color = QLineEdit()
            self.form_layout.addRow(QLabel('Background Color:'), self.bg_color)

            # Example for checkbox input
            self.lookback_msg_count_increment = QCheckBox()
            self.form_layout.addRow(QLabel('Lookback msg count increment:'), self.lookback_msg_count_increment)

            # Example for dropdown
            self.on_consecutive_response = NoWheelComboBox()
            self.on_consecutive_response.addItems(['PAD', 'RESET', 'RESTART'])
            self.form_layout.addRow(QLabel('On consecutive response:'), self.on_consecutive_response)

            for i in range(self.form_layout.rowCount()):
                widget = self.form_layout.itemAt(i, QFormLayout.FieldRole).widget()
                if widget:  # Check if the item is a widget
                    widget.setFixedWidth(150)

            self.setLayout(self.form_layout)

        def load(self):
            config = self.parent.main.page_chat.agent.config
            self.decay_at_idle_count.setValue(config.get('action_inputs.decay_at_idle_count'))
            self.bg_color.setText(config.get('gui.bg_color'))
            self.lookback_msg_count_increment.setChecked(
                config.get('action_inputs.lookback_msg_count_increment'))
            self.on_consecutive_response.setCurrentText(config.get('context.on_consecutive_response'))

    class Page_Display_Settings(QWidget):
        def __init__(self, parent):
            pass

    class Page_API_Settings(QWidget):
        def __init__(self, main):
            super().__init__(parent=main)

            self.layout = QVBoxLayout(self)

            self.table = QTableWidget(self)
            self.table.setColumnCount(4)
            self.table.setHorizontalHeaderLabels(['ID', 'Name', 'Client Key', 'Private Key'])
            self.table.setSelectionMode(QTableWidget.SingleSelection)  # For single row selection. Use MultiSelection for multiple rows.
            self.table.setSelectionBehavior(QTableWidget.SelectRows)  # Select the entire row.
            self.table.verticalHeader().setVisible(False)
            self.table.setColumnHidden(0, True)  # Hide ID column
            self.table.horizontalHeader().setStretchLastSection(True)
            self.table.itemChanged.connect(self.item_edited)  # Connect the itemChanged signal to the item_edited method

            # Additional attribute to store the locked status of each API
            self.api_locked_status = {}

            palette = self.table.palette()
            palette.setColor(QPalette.Highlight, QColor(SECONDARY_COLOR))  # Setting it to red
            palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))  # Setting text color to white
            palette.setColor(QPalette.Text, QColor(TEXT_COLOR))  # Setting unselected text color to purple
            self.table.setPalette(palette)
            self.layout.addWidget(self.table)

            # Buttons
            self.add_button = QPushButton("Add", self)
            self.add_button.clicked.connect(self.add_entry)

            self.delete_button = QPushButton("Delete", self)
            self.delete_button.clicked.connect(self.delete_entry)

            self.button_layout = QHBoxLayout()
            self.button_layout.addWidget(self.add_button)
            self.button_layout.addWidget(self.delete_button)
            self.layout.addLayout(self.button_layout)

            self.setLayout(self.layout)

            self.load_data()

        def load_data(self):
            # Fetch the data from the database
            self.table.blockSignals(True)
            data = sql.get_results("""
                SELECT
                    id,
                    name,
                    client_key,
                    priv_key,
                    locked
                FROM apis""")
            for row_data in data:
                row_position = self.table.rowCount()
                self.table.insertRow(row_position)
                # api_id = None
                for column, item in enumerate(row_data):
                    # is_locked = row_data[4]
                    if column == 0:
                        api_id = item
                    if column < 4:  # Ensure we only add the first four items to the table
                        self.table.setItem(row_position, column, QTableWidgetItem(str(item)))
                # Store the 'locked' status
                # self.api_locked_status[api_id] = is_locked
                # set name column to read only if is_locked
                # if is_locked:
                #     self.table.item(row_position, 1).setFlags(Qt.ItemIsEnabled)
            self.table.blockSignals(False)

        def item_edited(self, item):
            # Proceed with updating the database
            row = item.row()
            api_id = self.table.item(row, 0).text()

            # # Check if the API is locked
            # if self.api_locked_status.get(int(api_id)):
            #     QMessageBox.warning(self, "Locked API", "This API is locked and cannot be edited.")
            #     return

            id_map = {
                1: 'name',
                2: 'client_key',
                3: 'priv_key'
            }

            column = item.column()
            column_name = id_map.get(column)
            new_value = item.text()
            sql.execute(f"""
                UPDATE apis
                SET {column_name} = ?
                WHERE id = ?
            """, (new_value, api_id,))

            # reload api settings
            api.load_api_keys()

        def delete_entry(self):
            current_row = self.table.currentRow()
            if current_row == -1:
                return

            api_id = self.table.item(current_row, 0).text()
            # Check if the API is locked
            if self.api_locked_status.get(int(api_id)):
                QMessageBox.warning(self, "Locked API", "This API is locked and cannot be deleted.")
                return

            # Proceed with deletion from the database and the table

        def add_entry(self):
            pass

    class Page_Attachment_Settings(QWidget):
        def __init__(self, main):
            super().__init__(parent=main)

            # Main layout
            self.layout = QHBoxLayout(self)

            # Table setup
            self.table = QTableWidget(self)
            self.table.setColumnCount(2)  # ID and Name
            self.table.setHorizontalHeaderLabels(['ID', 'Name'])
            self.table.setColumnHidden(0, True)  # Hide ID column
            self.table.setColumnWidth(1, 125)  # Set Name column width
            self.table.verticalHeader().setVisible(False)
            self.table.setSelectionBehavior(QTableWidget.SelectRows)  # Select the entire row.
            self.table.setSelectionMode(QTableWidget.SingleSelection)  # For single row selection.
            self.table.setEditTriggers(
                QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)  # Make the table editable on double click or when the edit key is pressed.

            # Adding table to the layout
            self.layout.addWidget(self.table)

            # Attachment data area
            self.attachment_data_layout = QVBoxLayout()
            self.attachment_data_label = QLabel("Attachment data")
            self.attachment_data_text_area = QTextEdit()

            # Adding widgets to the vertical layout
            self.attachment_data_layout.addWidget(self.attachment_data_label)
            self.attachment_data_layout.addWidget(self.attachment_data_text_area)

            # Adding the vertical layout to the main layout
            self.layout.addLayout(self.attachment_data_layout)

            # Setting the main layout
            self.setLayout(self.layout)

            # Load initial data
            self.load_attachments()

        def load_attachments(self):
            # This is a dummy method. You should fetch and use real data here.
            dummy_data = [
                (1, "Attachment1"),
                (2, "Attachment2"),
                # ...
            ]

            for row_data in dummy_data:
                row_position = self.table.rowCount()
                self.table.insertRow(row_position)
                for column, item in enumerate(row_data):
                    if column == 0:
                        table_item = QTableWidgetItem(str(item))
                        table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)  # Make ID column non-editable
                    else:
                        table_item = QTableWidgetItem(str(item))
                    self.table.setItem(row_position, column, table_item)

            # Adjust the table
            self.table.resizeColumnsToContents()  # Resize table to content
            self.table.horizontalHeader().setStretchLastSection(True)  # Make the last section stretch to fill the space



class Page_Agents(ContentPage):
    def __init__(self, main):
        super().__init__(main=main, title='Agents')
        self.main = main

        self.settings_sidebar = self.Agent_Settings_SideBar(main=main, parent=self)

        self.agent_id = 0
        # self.agent_config = {}

        self.content = QStackedWidget(self)
        self.page_general = self.Page_General_Settings(self)
        self.page_context = self.Page_Context_Settings(self)
        self.page_actions = self.Page_Actions_Settings(self)
        self.page_code = self.Page_Code_Settings(self)
        self.page_voice = self.Page_Voice_Settings(self)
        self.content.addWidget(self.page_general)
        self.content.addWidget(self.page_context)
        self.content.addWidget(self.page_actions)
        self.content.addWidget(self.page_code)
        self.content.addWidget(self.page_voice)

        # H layout for lsidebar and content
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.settings_sidebar)
        input_layout.addWidget(self.content)

        # Create a QWidget to act as a container for the
        input_container = QWidget()
        input_container.setLayout(input_layout)

        # Adding input layout to the main layout
        self.table_widget = QTableWidget(0, 6, self)

        # add button to title widget

        self.btn_new_agent = self.Button_New_Agent(parent=self)
        self.title_layout.addWidget(self.btn_new_agent)  # QPushButton("Add", self))
        self.title_layout.addStretch()

        self.load_agents()

        self.table_widget.setColumnWidth(1, 45)
        self.table_widget.setColumnWidth(4, 45)
        self.table_widget.setColumnWidth(5, 45)
        self.table_widget.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table_widget.setSelectionMode(QTableWidget.SingleSelection)
        self.table_widget.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_widget.hideColumn(0)
        self.table_widget.hideColumn(2)
        self.table_widget.horizontalHeader().hide()
        self.table_widget.verticalHeader().hide()
        # Connect signals to slots
        self.table_widget.itemSelectionChanged.connect(self.on_agent_selected)
        # remove grid line
        self.table_widget.setShowGrid(False)

        palette = self.table_widget.palette()
        palette.setColor(QPalette.Highlight, QColor(SECONDARY_COLOR))  # Setting it to red
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))  # Setting text color to white
        palette.setColor(QPalette.Text, QColor(TEXT_COLOR))  # Setting unselected text color to purple
        self.table_widget.setPalette(palette)
        # Add the table to the layout
        self.layout.addWidget(self.table_widget)
        self.layout.addWidget(input_container)

    def load_agents(self):
        icon_chat = QIcon('./utils/resources/icon-chat.png')
        icon_del = QIcon('./utils/resources/icon-delete.png')

        self.table_widget.setRowCount(0)
        data = sql.get_results("""
            SELECT
                id,
                '' AS avatar,
                config,
                name,
                '' AS chat_button,
                '' AS del_button
            FROM agents
            ORDER BY id DESC""")
        for row_data in data:
            row_position = self.table_widget.rowCount()
            self.table_widget.insertRow(row_position)
            for column, item in enumerate(row_data):
                self.table_widget.setItem(row_position, column, QTableWidgetItem(str(item)))

            # Parse the config JSON to get the avatar path
            config = json.loads(row_data[2])  # Assuming config is the second column and in JSON format
            agent_avatar_path = config.get('general.avatar_path', '')

            # Create the circular avatar QPixmap
            try:
                if agent_avatar_path == '':
                    raise Exception('No avatar path')
                avatar_img = QPixmap(agent_avatar_path)
            except Exception as e:
                avatar_img = QPixmap("./utils/resources/icon-agent.png")

            circular_avatar_pixmap = create_circular_pixmap(avatar_img, diameter=25)

            # Create a QLabel to hold the pixmap
            avatar_label = QLabel()
            avatar_label.setPixmap(circular_avatar_pixmap)
            # set background to transparent
            avatar_label.setAttribute(Qt.WA_TranslucentBackground, True)

            # Add the new avatar icon column after the ID column
            self.table_widget.setCellWidget(row_position, 1, avatar_label)

            # set btn icon
            btn_chat = QPushButton('')
            btn_chat.setIcon(icon_chat)
            btn_chat.setIconSize(QSize(25, 25))
            btn_chat.clicked.connect(partial(self.chat_with_agent, row_data))
            self.table_widget.setCellWidget(row_position, 4, btn_chat)

            # set btn icon
            btn_del = QPushButton('')
            btn_del.setIcon(icon_del)
            btn_del.setIconSize(QSize(25, 25))
            btn_del.clicked.connect(partial(self.delete_agent, row_data))
            self.table_widget.setCellWidget(row_position, 5, btn_del)

        if self.table_widget.rowCount() > 0:
            self.table_widget.selectRow(0)

    def on_agent_selected(self):
        current_row = self.table_widget.currentRow()
        if current_row == -1: return
        sel_id = self.table_widget.item(current_row, 0).text()
        agent_config_json = sql.get_scalar('SELECT config FROM agents WHERE id = ?', (sel_id,))

        self.agent_id = self.table_widget.item(current_row, 0).text()
        self.agent_config = json.loads(agent_config_json) if agent_config_json else {}

        # general.avatar_path

        # context.sys_msg
        # context.fallback_to_davinci
        # context.max_messages

        # actions.enable_actions
        # actions.source_directory
        # actions.replace_busy_action_on_new
        # actions.use_function_calling
        # actions.use_validator

        # code.enable_code_interpreter
        # code.auto_run_seconds
        # code.use_gpt4

        self.page_general.avatar_path = (self.agent_config.get('general.avatar_path', ''))
        try:
            # self.page_general.avatar.setPixmap(QPixmap())
            if self.page_general.avatar_path == '':
                raise Exception('No avatar path')
            avatar_img = QPixmap(self.page_general.avatar_path)
        except Exception as e:
            avatar_img = QPixmap("./utils/resources/icon-agent.png")
        self.page_general.avatar.setPixmap(avatar_img)
        self.page_general.avatar.update()
        self.page_general.name.setText(self.table_widget.item(current_row, 3).text())

        self.page_context.sys_msg.setText(self.agent_config.get('context.sys_msg', ''))
        self.page_context.fallback_to_davinci.setChecked(self.agent_config.get('context.fallback_to_davinci', False))
        self.page_context.max_messages.setValue(self.agent_config.get('context.max_messages', 5))

        self.page_actions.enable_actions.setChecked(self.agent_config.get('actions.enable_actions', False))
        self.page_actions.source_directory.setText(self.agent_config.get('actions.source_directory', ''))
        self.page_actions.replace_busy_action_on_new.setChecked(self.agent_config.get('actions.replace_busy_action_on_new', False))
        self.page_actions.use_function_calling.setChecked(self.agent_config.get('actions.use_function_calling', False))
        self.page_actions.use_validator.setChecked(self.agent_config.get('actions.use_validator', False))

        self.page_code.enable_code_interpreter.setChecked(self.agent_config.get('code.enable_code_interpreter', False))
        self.page_code.auto_run_seconds.setText(self.agent_config.get('code.auto_run_seconds', ''))
        self.page_code.use_gpt4.setChecked(self.agent_config.get('code.use_gpt4', False))


    def chat_with_agent(self, row_data):
        from agent.base import Agent
        id_value = row_data[0]  # self.table_widget.item(row_item, 0).text()
        self.main.page_chat.agent = Agent(agent_id=id_value)
        self.main.page_chat.load_bubbles()
        self.main.content.setCurrentWidget(self.main.page_chat)
        self.main.sidebar.btn_new_context.setChecked(True)

    def delete_agent(self, row_data):
        global PIN_STATE
        context_count = sql.get_results("""
            SELECT
                COUNT(*)
            FROM contexts
            WHERE agent_id = ?""", (row_data[0],))[0][0]

        has_contexts_msg = ''
        if context_count > 0:
            has_contexts_msg = 'This agent has contexts associated with it. Deleting this agent will delete all associated contexts. '

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText(f"{has_contexts_msg}Are you sure you want to delete this agent?")
        msg.setWindowTitle("Delete Agent")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        current_pin_state = PIN_STATE
        PIN_STATE = True
        retval = msg.exec_()
        PIN_STATE = current_pin_state
        if retval != QMessageBox.Yes:
            return

        sql.execute("DELETE FROM contexts_messages WHERE context_id IN (SELECT id FROM contexts WHERE agent_id = ?);", (row_data[0],))
        sql.execute("DELETE FROM contexts WHERE agent_id = ?;", (row_data[0],))
        sql.execute("DELETE FROM agents WHERE id = ?;", (row_data[0],))
        self.load_agents()

    def get_current_config(self):
        # ~CONF
        # Retrieve the current values from the widgets and construct a new 'config' dictionary
        current_config = {
            'general.avatar_path': self.page_general.avatar_path,
            'context.sys_msg': self.page_context.sys_msg.toPlainText(),
            'context.fallback_to_davinci': self.page_context.fallback_to_davinci.isChecked(),
            'context.max_messages': self.page_context.max_messages.value(),
            'actions.enable_actions': self.page_actions.enable_actions.isChecked(),
            'actions.source_directory': self.page_actions.source_directory.text(),
            'actions.replace_busy_action_on_new': self.page_actions.replace_busy_action_on_new.isChecked(),
            'actions.use_function_calling': self.page_actions.use_function_calling.isChecked(),
            'actions.use_validator': self.page_actions.use_validator.isChecked(),
            'code.enable_code_interpreter': self.page_code.enable_code_interpreter.isChecked(),
            'code.auto_run_seconds': self.page_code.auto_run_seconds.text(),
            'code.use_gpt4': self.page_code.use_gpt4.isChecked(),
        }
        return json.dumps(current_config)

    def update_config(self):
        sql.execute("UPDATE agents SET config = ? WHERE id = ?", (self.get_current_config(), self.agent_id))
        self.main.page_chat.agent.load_agent()

    class Button_New_Agent(QPushButton):
        def __init__(self, parent):
            super().__init__(parent=parent, icon=QIcon())
            self.parent = parent
            self.clicked.connect(self.new_agent)
            self.icon = QIcon(QPixmap("./utils/resources/icon-new.png"))
            self.setIcon(self.icon)
            self.setFixedSize(25, 25)
            self.setIconSize(QSize(25, 25))

        def new_agent(self):
            global PIN_STATE
            current_pin_state = PIN_STATE
            PIN_STATE = True
            text, ok = QInputDialog.getText(self, 'New Agent', 'Enter a name for the agent:')

            # Check if the OK button was clicked
            if ok:
                # Display the entered value in a message box
                sql.execute("INSERT INTO `agents` (`name`) SELECT ? AS `name`", (text,))
                self.parent.load_agents()
            PIN_STATE = current_pin_state

    class Agent_Settings_SideBar(QWidget):
        def __init__(self, main, parent):
            super().__init__(parent=main)
            self.main = main
            self.parent = parent
            self.setObjectName("SettingsSideBarWidget")
            self.setAttribute(Qt.WA_StyledBackground, True)
            self.setProperty("class", "sidebar")

            font = QFont()
            font.setPointSize(15)  # Set font size to 20 points

            self.btn_general = self.Settings_SideBar_Button(main=main, text='General')
            self.btn_general.setFont(font)
            self.btn_general.setChecked(True)
            self.btn_context = self.Settings_SideBar_Button(main=main, text='Context')
            self.btn_context.setFont(font)
            self.btn_actions = self.Settings_SideBar_Button(main=main, text='Actions')
            self.btn_actions.setFont(font)
            self.btn_code_interpreter = self.Settings_SideBar_Button(main=main, text='Code')
            self.btn_code_interpreter.setFont(font)
            self.btn_voice = self.Settings_SideBar_Button(main=main, text='Voice')
            self.btn_voice.setFont(font)

            self.layout = QVBoxLayout(self)
            self.layout.setSpacing(0)
            self.layout.setContentsMargins(0, 0, 0, 0)

            # Create a button group and add buttons to it
            self.button_group = QButtonGroup(self)
            self.button_group.addButton(self.btn_general, 0)
            self.button_group.addButton(self.btn_context, 1)
            self.button_group.addButton(self.btn_actions, 2)
            self.button_group.addButton(self.btn_code_interpreter, 3)
            self.button_group.addButton(self.btn_voice, 4)  # 1

            # Connect button toggled signal
            self.button_group.buttonToggled[QAbstractButton, bool].connect(self.onButtonToggled)

            # self.layout.addStretch(1)

            self.layout.addWidget(self.btn_general)
            self.layout.addWidget(self.btn_context)
            self.layout.addWidget(self.btn_actions)
            self.layout.addWidget(self.btn_code_interpreter)
            self.layout.addWidget(self.btn_voice)
            self.layout.addStretch()

        def onButtonToggled(self, button, checked):
            if checked:
                index = self.button_group.id(button)
                self.parent.content.setCurrentIndex(index)

        def updateButtonStates(self):
            # Check the appropriate button based on the current page
            stacked_widget = self.parent.content
            self.btn_context.setChecked(stacked_widget.currentWidget() == self.btn_context)
            self.btn_actions.setChecked(stacked_widget.currentWidget() == self.btn_actions)

        class Settings_SideBar_Button(QPushButton):
            def __init__(self, main, text=''):
                super().__init__(parent=main, icon=QIcon())
                self.main = main
                self.setProperty("class", "menuitem")
                # self.clicked.connect(self.goto_system_settings)
                self.setText(text)
                self.setFixedSize(75, 30)
                self.setCheckable(True)

    class Page_General_Settings(QWidget):
        def __init__(self, parent):
            super().__init__(parent=parent)
            self.parent = parent

            # Main layout for this widget
            main_layout = QVBoxLayout(self)
            main_layout.setAlignment(Qt.AlignCenter)  # Center the layout's content


            profile_layout = QHBoxLayout(self)
            profile_layout.setAlignment(Qt.AlignCenter)
            # Avatar - an image input field
            self.avatar_path = ''
            self.avatar = self.ClickableAvatarLabel(self)
            self.avatar.clicked.connect(self.change_avatar)
            # Load and set the avatar image, for example:
            # self.avatar.setPixmap(QPixmap(config.get_value('general.avatar')))

            # Name - a text field, so use QLineEdit
            self.name = QLineEdit()
            # add event when name changed update db field
            self.name.textChanged.connect(self.update_name)
            # self.name.setFixedWidth(150)
            # self.name.setText(config.get_value('general.name'))

            # Set the font size to 22 for the name field
            font = self.name.font()
            font.setPointSize(15)
            self.name.setFont(font)
            # centre the text
            self.name.setAlignment(Qt.AlignCenter)

            # Adding avatar and name to the main layout
            profile_layout.addWidget(self.avatar)  # Adding the avatar

            # add profile layout to main layout
            main_layout.addLayout(profile_layout)
            main_layout.addWidget(self.name)  # Adding the name field
            main_layout.addStretch()

            # Set the layout to the QWidget
            self.setLayout(main_layout)

        def update_name(self):
            new_name = self.name.text()
            sql.execute("UPDATE agents SET name = ? WHERE id = ?", (new_name, self.parent.agent_id))

        class ClickableAvatarLabel(QLabel):
            # This creates a new signal called 'clicked' that the label will emit when it's clicked.
            clicked = Signal()

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # Assuming a default avatar path is set in case no avatar is set yet
                # self.default_avatar_path = 'path_to_default_avatar'
                # self.setPixmap(QPixmap(self.default_avatar_path))
                self.setAlignment(Qt.AlignCenter)
                self.setCursor(Qt.PointingHandCursor)  # Change mouse cursor to hand pointer for better UI indication
                self.setFixedSize(100, 100)
                self.setStyleSheet("border: 1px dashed rgb(200, 200, 200); border-radius: 50px;")  # A custom style for the empty label

            def mousePressEvent(self, event):
                super().mousePressEvent(event)
                if event.button() == Qt.LeftButton:  # Emit 'clicked' only for left button clicks
                    self.clicked.emit()

            def setPixmap(self, pixmap):
                # Override setPixmap to maintain the aspect ratio of the image
                super().setPixmap(pixmap.scaled(
                    self.width(), self.height(),
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation
                ))

            def paintEvent(self, event):
                # Override paintEvent to draw a circular image
                painter = QPainter(self)
                painter.setRenderHint(QPainter.Antialiasing)
                path = QPainterPath()
                path.addEllipse(0, 0, self.width(), self.height())
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, self.pixmap())
                painter.end()

        def change_avatar(self):
            global PIN_STATE
            current_pin_state = PIN_STATE
            PIN_STATE = True
            options = QFileDialog.Options()
            fileName, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "",
                                                      "Images (*.png *.jpeg *.jpg *.bmp *.gif)", options=options)
            PIN_STATE = current_pin_state
            if fileName:
                self.avatar.setPixmap(QPixmap(fileName))
                self.avatar_path = fileName
                self.parent.update_config()
                # update config in agents
                # Update the configuration with the new avatar path
                # config.set_value('general.avatar', fileName)
                # Assuming the parent has a method `update_config` that gets called when settings change
                # self.parent().update_config()

    class Page_Context_Settings(QWidget):
        def __init__(self, parent):
            super().__init__(parent=parent)
            self.form_layout = QFormLayout()

            # SysMsg - a big block of text, so use a QTextEdit
            self.sys_msg = QTextEdit()
            # self.sys_msg.setPlainText(config.get_value('context.sys-msg'))
            self.sys_msg.setFixedHeight(100)  # Adjust height as per requirement
            self.form_layout.addRow(QLabel('SysMsg:'), self.sys_msg)

            # Fallback to davinci - a checkbox
            self.fallback_to_davinci = QCheckBox()
            # self.fallback_to_davinci.setChecked(config.get_value('context.fallback-to-davinci'))
            self.form_layout.addRow(QLabel('Fallback to davinci:'), self.fallback_to_davinci)

            # max-messages - a numeric input, so use QSpinBox
            self.max_messages = QSpinBox()
            # self.max_messages.setValue(config.get_value('context.max-messages'))
            self.max_messages.setFixedWidth(150)  # Consistent width
            self.form_layout.addRow(QLabel('Max Messages:'), self.max_messages)

            # Add the form layout to a QVBoxLayout and add a spacer to push everything to the top
            self.main_layout = QVBoxLayout(self)
            self.main_layout.addLayout(self.form_layout)
            spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
            self.main_layout.addItem(spacer)

            self.sys_msg.textChanged.connect(parent.update_config)
            self.fallback_to_davinci.stateChanged.connect(parent.update_config)
            self.max_messages.valueChanged.connect(parent.update_config)

            # self.setLayout(self.form_layout)

    class Page_Actions_Settings(QWidget):
        def __init__(self, parent):
            super().__init__(parent=parent)
            self.form_layout = QFormLayout()

            # Enable actions - checkbox
            self.enable_actions = QCheckBox()
            self.form_layout.addRow(QLabel('Enable actions:'), self.enable_actions)

            # Source directory - path field and button to trigger folder dialog
            self.source_directory = QLineEdit()
            self.browse_button = QPushButton("..")
            self.browse_button.setFixedSize(25, 25)
            self.browse_button.clicked.connect(self.browse_for_folder)

            hbox = QHBoxLayout()
            hbox.addWidget(self.browse_button)
            hbox.addWidget(self.source_directory)

            # self.form_layout.addRow(QLabel('Source Directory:'), hbox)

            # Replace-busy-action-on-new - checkbox
            self.replace_busy_action_on_new = QCheckBox()
            # self.form_layout.addRow(QLabel('Replace busy action on new:'), self.replace_busy_action_on_new)

            # Use function calling - checkbox
            self.use_function_calling = QCheckBox()
            # self.form_layout.addRow(QLabel('Use function calling:'), self.use_function_calling)

            # Use validator - checkbox
            self.use_validator = QCheckBox()
            # self.form_layout.addRow(QLabel('Use validator:'), self.use_validator)

            # Create labels as member variables
            self.label_source_directory = QLabel('Source Directory:')
            self.label_replace_busy_action_on_new = QLabel('Replace busy action on new:')
            self.label_use_function_calling = QLabel('Use function calling:')
            self.label_use_validator = QLabel('Use validator:')

            # Add them to the form layout
            self.form_layout.addRow(self.label_source_directory, hbox)
            self.form_layout.addRow(self.label_replace_busy_action_on_new, self.replace_busy_action_on_new)
            self.form_layout.addRow(self.label_use_function_calling, self.use_function_calling)
            self.form_layout.addRow(self.label_use_validator, self.use_validator)

            self.setLayout(self.form_layout)

            # Connect the signal to the slot
            self.enable_actions.stateChanged.connect(self.toggle_enabled_state)

            # Set initial state
            self.toggle_enabled_state()

            self.enable_actions.stateChanged.connect(parent.update_config)
            self.source_directory.textChanged.connect(parent.update_config)
            self.replace_busy_action_on_new.stateChanged.connect(parent.update_config)
            self.use_function_calling.stateChanged.connect(parent.update_config)
            self.use_validator.stateChanged.connect(parent.update_config)

        def browse_for_folder(self):
            folder = QFileDialog.getExistingDirectory(self, "Select Source Directory")
            if folder:
                self.source_directory.setText(folder)

        def toggle_enabled_state(self):
            global TEXT_COLOR
            is_enabled = self.enable_actions.isChecked()

            # Set enabled/disabled state for the widgets
            self.source_directory.setEnabled(is_enabled)
            self.browse_button.setEnabled(is_enabled)
            self.replace_busy_action_on_new.setEnabled(is_enabled)
            self.use_function_calling.setEnabled(is_enabled)
            self.use_validator.setEnabled(is_enabled)

            # Update label colors based on enabled state
            if is_enabled:
                color = TEXT_COLOR  # or any other color when enabled
            else:
                color = "#4d4d4d"  # or any other color when disabled

            self.label_source_directory.setStyleSheet(f"color: {color}")
            self.label_replace_busy_action_on_new.setStyleSheet(f"color: {color}")
            self.label_use_function_calling.setStyleSheet(f"color: {color}")
            self.label_use_validator.setStyleSheet(f"color: {color}")

    class Page_Code_Settings(QWidget):
        def __init__(self, parent):
            super().__init__(parent=parent)
            self.form_layout = QFormLayout()

            # Enable code interpreter - checkbox
            self.enable_code_interpreter = QCheckBox()
            self.form_layout.addRow(QLabel('Enable code interpreter:'), self.enable_code_interpreter)

            # Auto run seconds - integer input
            self.auto_run_seconds = QLineEdit()
            self.auto_run_seconds.setValidator(QIntValidator(0, 9999))  # Assuming a max of 9999 seconds for simplicity
            self.form_layout.addRow(QLabel('Auto run seconds:'), self.auto_run_seconds)

            # Use GPT4 - checkbox
            self.use_gpt4 = QCheckBox()
            self.form_layout.addRow(QLabel('Use GPT4:'), self.use_gpt4)

            # Create labels as member variables
            self.label_enable_code_interpreter = QLabel('Enable code interpreter:')
            self.label_auto_run_seconds = QLabel('Auto run seconds:')
            self.label_use_gpt4 = QLabel('Use GPT4:')

            # Set the layout
            self.setLayout(self.form_layout)

            # Connect the signal to the slot
            self.enable_code_interpreter.stateChanged.connect(self.toggle_enabled_state)

            # Set initial state
            self.toggle_enabled_state()

            # Connect the signals to the slots
            self.enable_code_interpreter.stateChanged.connect(parent.update_config)
            self.auto_run_seconds.textChanged.connect(parent.update_config)
            self.use_gpt4.stateChanged.connect(parent.update_config)

        def toggle_enabled_state(self):
            global TEXT_COLOR
            is_enabled = self.enable_code_interpreter.isChecked()

            # Set enabled/disabled state for the widgets
            self.auto_run_seconds.setEnabled(is_enabled)
            self.use_gpt4.setEnabled(is_enabled)

            # Update label colors based on enabled state
            if is_enabled:
                color = TEXT_COLOR  # or any other color when enabled
            else:
                color = "#4d4d4d"  # or any other color when disabled

            self.label_enable_code_interpreter.setStyleSheet(f"color: {color}")
            self.label_auto_run_seconds.setStyleSheet(f"color: {color}")
            self.label_use_gpt4.setStyleSheet(f"color: {color}")

    class Page_Voice_Settings(QWidget):
        def __init__(self, main):
            super().__init__(parent=main)

            # UI setup
            self.layout = QVBoxLayout(self)

            # Search panel setup
            self.search_panel = QWidget(self)
            self.search_layout = QHBoxLayout(self.search_panel)
            self.api_dropdown = QComboBox(self)
            self.api_dropdown.addItem("ALL", 0)  # adding "ALL" option with id=0
            self.search_field = QLineEdit(self)
            self.search_layout.addWidget(QLabel("API:"))
            self.search_layout.addWidget(self.api_dropdown)
            self.search_layout.addWidget(QLabel("Search:"))
            self.search_layout.addWidget(self.search_field)
            self.layout.addWidget(self.search_panel)

            self.table = QTableWidget(self)
            self.table.setSelectionMode(QTableWidget.SingleSelection)
            self.table.setSelectionBehavior(QTableWidget.SelectRows)
            palette = self.table.palette()
            palette.setColor(QPalette.Highlight, QColor(SECONDARY_COLOR))
            palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
            palette.setColor(QPalette.Text, QColor(TEXT_COLOR))
            self.table.setPalette(palette)

            # Creating a new QWidget to hold the buttons
            self.buttons_panel = QWidget(self)
            self.buttons_layout = QHBoxLayout(self.buttons_panel)
            self.buttons_layout.setAlignment(Qt.AlignRight)  # Aligning buttons to the right

            # Set as voice button
            self.set_voice_button = QPushButton("Set as voice", self)
            self.set_voice_button.setFixedWidth(150)  # Set the width to a normal button width
            # Test voice button
            self.test_voice_button = QPushButton("Test voice", self)
            self.test_voice_button.setFixedWidth(150)  # Set the width to a normal button width
            # Adding buttons to the layout
            self.buttons_layout.addWidget(self.set_voice_button)
            self.buttons_layout.addWidget(self.test_voice_button)
            self.layout.addWidget(self.table)
            self.layout.addWidget(self.buttons_panel)  # Adding the buttons panel to the main layout
            # Connect button click and other UI events
            self.set_voice_button.clicked.connect(self.set_as_voice)
            self.test_voice_button.clicked.connect(self.test_voice)  # You will need to define the 'test_voice' method

            self.api_dropdown.currentIndexChanged.connect(self.filter_table)
            self.search_field.textChanged.connect(self.filter_table)

            # Database fetch and display
            self.load_data_from_db()
            self.load_apis()

            self.table.verticalHeader().hide()
            self.table.hideColumn(0)  # Hide ID column

        def load_data_from_db(self):
            # Fetch all voices initially
            self.all_voices, self.col_names = sql.get_results("""
                SELECT
                    v.`id`,
                    a.`name` AS api_id,
                    v.`display_name`,
                    v.`known_from`,
                    v.`uuid`,
                    v.`added_on`,
                    v.`updated_on`,
                    v.`rating`,
                    v.`creator`,
                    v.`lang`,
                    v.`deleted`,
                    v.`fav`,
                    v.`full_in_prompt`,
                    v.`verb`,
                    v.`add_prompt`
                FROM `voices` v
                LEFT JOIN apis a
                    ON v.api_id = a.id""", incl_column_names=True)

            self.display_data_in_table(self.all_voices)

        def load_apis(self):
            # Assuming that the first item in the tuple is 'ID' and the second is 'name'
            apis = sql.get_results("SELECT ID, name FROM apis")
            for api in apis:
                # Use integer indices instead of string keys
                api_id = api[0]  # 'ID' is at index 0
                api_name = api[1]  # 'name' is at index 1
                self.api_dropdown.addItem(api_name, api_id)

        def filter_table(self):
            api_id = self.api_dropdown.currentData()
            search_text = self.search_field.text().lower()

            filtered_voices = []
            for voice in self.all_voices:
                # Check if voice matches the selected API and contains the search text in 'name' or 'known_from'
                # (using the correct indices for your data)
                if (api_id == 0 or str(voice[1]) == str(api_id)) and \
                        (search_text in voice[2].lower() or search_text in voice[3].lower()):
                    filtered_voices.append(voice)

            self.display_data_in_table(filtered_voices)

        def display_data_in_table(self, voices):
            self.table.setRowCount(len(voices))
            # Add an extra column for the play buttons
            self.table.setColumnCount(len(voices[0]) if voices else 0)
            # Add a header for the new play button column
            self.table.setHorizontalHeaderLabels(self.col_names)

            for row_index, row_data in enumerate(voices):
                for col_index, cell_data in enumerate(row_data):  # row_data is a tuple, not a dict
                    self.table.setItem(row_index, col_index, QTableWidgetItem(str(cell_data)))

        def set_as_voice(self):
            current_row = self.table.currentRow()
            if current_row == -1:
                QMessageBox.warning(self, "Selection Error", "Please select a voice from the table!")
                return

            voice_id = self.table.item(current_row, 0).text()
            # Further actions can be taken using voice_id or the data of the selected row

            QMessageBox.information(self, "Voice Set", f"Voice with ID {voice_id} has been set!")

        def test_voice(self):
            # Implement the functionality to test the voice
            pass

class Page_Contexts(ContentPage):
    def __init__(self, main):
        super().__init__(main=main, title='Contexts')
        self.main = main

        self.table_widget = QTableWidget(0, 5, self)

        self.load_contexts()

        self.table_widget.setColumnWidth(3, 45)
        self.table_widget.setColumnWidth(4, 45)
        # self.table_widget.setColumnWidth(1, 450)
        self.table_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        # self.table_widget.setSelectionMode(QTableWidget.Sin)
        self.table_widget.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_widget.hideColumn(0)
        self.table_widget.horizontalHeader().hide()
        self.table_widget.verticalHeader().hide()

        palette = self.table_widget.palette()
        palette.setColor(QPalette.Highlight, QColor(SECONDARY_COLOR))  # Setting it to red
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))  # Setting text color to white
        palette.setColor(QPalette.Text, QColor(TEXT_COLOR))  # Setting unselected text color to purple
        self.table_widget.setPalette(palette)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        # Add the table to the layout
        self.layout.addWidget(self.table_widget)

    def load_contexts(self):
        self.table_widget.setRowCount(0)
        data = sql.get_results("""
            SELECT
                c.id,
                c.summary,
                a.name,
                '' AS goto_button,
                '' AS del_button
            FROM contexts c
            LEFT JOIN agents a
                ON c.agent_id = a.id
            LEFT JOIN (
                SELECT
                    context_id,
                    MAX(id) as latest_message_id
                FROM contexts_messages
                GROUP BY context_id
            ) cm ON c.id = cm.context_id
            WHERE c.parent_id IS NULL
            ORDER BY
                CASE WHEN cm.latest_message_id IS NULL THEN 0 ELSE 1 END,
                COALESCE(cm.latest_message_id, 0) DESC, 
                c.id DESC
            """)
        first_desc = 'CURRENT CONTEXT'

        icon_chat = QIcon('./utils/resources/icon-chat.png')
        icon_del = QIcon('./utils/resources/icon-delete.png')

        for row_data in data:
            if first_desc:
                row_data = [row_data[0], first_desc, row_data[2], row_data[3]]
                first_desc = None
            row_position = self.table_widget.rowCount()
            self.table_widget.insertRow(row_position)
            for column, item in enumerate(row_data):
                self.table_widget.setItem(row_position, column, QTableWidgetItem(str(item)))

            if row_data[2] is None:  # If agent_name is NULL
                self.table_widget.setSpan(row_position, 1, 1, 2)  # Make the summary cell span over the next column

            # set btn icon
            btn_chat = QPushButton('')
            btn_chat.setIcon(icon_chat)
            btn_chat.setIconSize(QSize(25, 25))
            btn_chat.clicked.connect(partial(self.goto_context, row_data))
            self.table_widget.setCellWidget(row_position, 3, btn_chat)

            # set btn icon
            btn_delete = QPushButton('')
            btn_delete.setIcon(icon_del)
            btn_delete.setIconSize(QSize(25, 25))
            btn_delete.clicked.connect(partial(self.delete_context, row_data))
            self.table_widget.setCellWidget(row_position, 4, btn_delete)

    def goto_context(self, row_item):
        from agent.base import Agent
        id_value = row_item[0]  # self.table_widget.item(row_item, 0).text()
        self.main.page_chat.agent = Agent(agent_id=None, context_id=id_value)
        self.main.page_chat.load_bubbles()
        self.main.content.setCurrentWidget(self.main.page_chat)
        self.main.sidebar.btn_new_context.setChecked(True)
        # print(f"goto ID: {id_value}")

    def delete_context(self, row_item):
        from agent.base import Agent
        global PIN_STATE
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("Are you sure you want to permanently delete this context?")
        msg.setWindowTitle("Delete Context")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        current_pin_state = PIN_STATE
        PIN_STATE = True
        retval = msg.exec_()
        PIN_STATE = current_pin_state
        if retval != QMessageBox.Yes:
            return

        context_id = row_item[0]
        sql.execute("DELETE FROM contexts_messages WHERE context_id = ?;", (context_id,))
        sql.execute("DELETE FROM contexts WHERE id = ?;", (context_id,))
        self.load_contexts()

        if self.main.page_chat.agent.context.message_history.context_id == context_id:
            self.main.page_chat.agent = Agent(agent_id=None)


class Page_Chat(QScrollArea):
    def __init__(self, main):
        super().__init__(parent=main)
        from agent.base import Agent
        self.agent = Agent(agent_id=None)
        self.main = main

        self.chat_bubbles = []
        self.last_assistant_bubble = None

        # Overall layout for the page
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # TopBar pp
        self.topbar = self.Top_Bar(self)
        self.layout.addWidget(self.topbar)

        # Scroll area for the chat
        self.scroll_area = QScrollArea(self)
        self.chat = QWidget(self.scroll_area)
        self.chat_scroll_layout = QVBoxLayout(self.chat)
        self.chat_scroll_layout.addStretch(1)

        self.scroll_area.setWidget(self.chat)
        self.scroll_area.setWidgetResizable(True)

        self.layout.addWidget(self.scroll_area)

    class Top_Bar(QWidget):
        def __init__(self, parent):
            super().__init__(parent=parent)
            self.setMouseTracking(True)
            self.setFixedHeight(40)
            self.topbar_layout = QHBoxLayout(self)
            self.topbar_layout.setSpacing(0)
            # self.topbar_layout.setContentsMargins(0, 0, 0, 0)
            self.topbar_layout.setContentsMargins(5, 5, 5, 10)

            agent_name = self.parent().agent.name
            agent_avatar_path = self.parent().agent.config.get('general.avatar_path', '')
            try:
                # self.page_general.avatar.setPixmap(QPixmap())
                if agent_avatar_path == '':
                    raise Exception('No avatar path')
                avatar_img = QPixmap(agent_avatar_path)
            except Exception as e:
                avatar_img = QPixmap("./utils/resources/icon-agent.png")
            # Step 1: Load the image
            # pixmap = QPixmap("path_to_your_image_here")  # put the correct path of your image

            circular_pixmap = create_circular_pixmap(avatar_img)

            # Step 3: Set the pixmap on a QLabel
            self.profile_pic_label = QLabel(self)
            self.profile_pic_label.setPixmap(circular_pixmap)
            self.profile_pic_label.setFixedSize(50, 30)  # set the QLabel size to the same as the pixmap
            # self.profile_pic_label.setStyleSheet(
            #     "border: 1px solid rgb(200, 200, 200); border-radius: 15px;")  # A custom style for the empty label

            # Step 4: Add QLabel to your layout
            self.topbar_layout.addWidget(self.profile_pic_label)

            self.agent_name_label = QLabel(self)
            self.agent_name_label.setText(agent_name)
            font = self.agent_name_label.font()
            font.setPointSize(15)
            self.agent_name_label.setFont(font)
            self.agent_name_label.setStyleSheet("QLabel:hover { color: #dddddd; }")
            self.agent_name_label.mousePressEvent = self.agent_name_clicked
            self.agent_name_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.topbar_layout.addWidget(self.agent_name_label)

            self.topbar_layout.addStretch()

            self.button_container = QWidget(self)
            button_layout = QHBoxLayout(self.button_container)  # Layout for the container
            button_layout.setSpacing(5)  # Set spacing between buttons, adjust to your need
            button_layout.setContentsMargins(0, 0, 20, 0)  # Optional: if you want to reduce space from the container's margins

            # Create buttons
            btn_prev_context = QPushButton(icon=QIcon('./utils/resources/icon-left-arrow.png'))
            btn_next_context = QPushButton(icon=QIcon('./utils/resources/icon-right-arrow.png'))
            btn_prev_context.setFixedSize(25, 25)
            btn_next_context.setFixedSize(25, 25)
            # ... add as many buttons as you need

            # Add buttons to the container layout instead of the button group
            button_layout.addWidget(btn_prev_context)
            button_layout.addWidget(btn_next_context)
            # ... add buttons to the layout

            # Add the container to the top bar layout
            self.topbar_layout.addWidget(self.button_container)

            self.button_container.hide()

        def enterEvent(self, event):
            self.showButtonGroup()

        def leaveEvent(self, event):
            self.hideButtonGroup()

        def showButtonGroup(self):
            self.button_container.show()

        def hideButtonGroup(self):
            self.button_container.hide()

        def agent_name_clicked(self, event):
            self.parent().main.content.setCurrentWidget(self.parent().main.page_agents)

        def set_agent(self, agent):
            agent_name = agent.name
            agent_avatar_path = agent.config.get('general.avatar_path', '')
            self.agent_name_label.setText(agent_name)
            # Update the profile picture
            try:
                if agent_avatar_path == '':
                    raise Exception('No avatar path')
                avatar_img = QPixmap(agent_avatar_path)
            except Exception as e:
                avatar_img = QPixmap("./utils/resources/icon-agent.png")

            # Create a circular profile picture
            circular_pixmap = create_circular_pixmap(avatar_img)

            # Update the QLabel with the new pixmap
            self.profile_pic_label.setPixmap(circular_pixmap)

    #
    class MessageBubbleBase(QTextEdit):
        def __init__(self, msg_id, text, viewport, role, parent):
            super().__init__(parent=parent)
            if role not in ('user', 'code'):
                self.setReadOnly(True)

            self.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding
            )
            self.parent = parent
            self.msg_id = msg_id
            self.agent = parent.agent
            self.role = role
            self.setProperty("class", "bubble")
            self.setProperty("class", role)
            self._viewport = viewport
            self.margin = QMargins(6, 0, 6, 0)
            self.text = ''
            self.original_text = text

            self.append_text(text)

        def calculate_button_position(self):
            button_width = 60
            button_height = 25
            button_x = self.width() - button_width
            button_y = self.height() - button_height
            return QRect(button_x, button_y, button_width, button_height)

        def append_text(self, text):
            self.text += text
            self.original_text = self.text
            self.setPlainText(self.text)
            self.update_size()

        def update_size(self):
            # self.text = self.toPlainText()
            self.setFixedSize(self.sizeHint())
            if hasattr(self, 'btn_resend'):
                self.btn_resend.setGeometry(self.calculate_button_position())
            self.updateGeometry()
            self.parent.updateGeometry()

        def sizeHint(self):
            lr = self.margin.left() + self.margin.right()
            tb = self.margin.top() + self.margin.bottom()

            doc = self.document().clone()
            doc.setDefaultFont(self.font())
            doc.setPlainText(self.text)
            doc.setTextWidth((self._viewport.width() - lr) * 0.8)

            return QSize(int(doc.idealWidth() + lr), int(doc.size().height() + tb))

        def minimumSizeHint(self):
            return self.sizeHint()

        def keyPressEvent(self, event):
            super().keyPressEvent(event)

    class MessageBubbleUser(MessageBubbleBase):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            self.btn_resend = self.BubbleButton_Resend(self)
            self.btn_resend.setGeometry(self.calculate_button_position())
            self.btn_resend.hide()

            self.textChanged.connect(self.text_editted)

        def text_editted(self):
            self.text = self.toPlainText()
            self.update_size()

        def check_and_toggle_resend_button(self):
            if self.toPlainText() != self.original_text:
                self.btn_resend.show()
            else:
                self.btn_resend.hide()

        def keyPressEvent(self, event):
            super().keyPressEvent(event)
            self.check_and_toggle_resend_button()
            # self.update_size()

        class BubbleButton_Resend(QPushButton):
            def __init__(self, parent=None):
                super().__init__(parent=parent, icon=QIcon())
                self.setProperty("class", "resend")
                self.clicked.connect(self.resend_msg)

                icon = QIcon(QPixmap("./utils/resources/icon-send.png"))
                self.setIcon(icon)

            def resend_msg(self):
                pass

    class MessageBubbleCode(MessageBubbleBase):
        def __init__(self, msg_id, text, viewport, role, parent, start_timer=False):
            super().__init__(msg_id, text, viewport, role, parent)

            lang, code = self.split_lang_and_code(text)
            self.append_text(code)
            self.setToolTip(f'{lang} code')
            self.tag = lang
            self.btn_rerun = self.BubbleButton_Rerun_Code(self)
            self.btn_rerun.setGeometry(self.calculate_button_position())
            self.btn_rerun.hide()

            if start_timer:
                self.countdown_stopped = False
                self.countdown = self.agent.config.get('code_interpreter.auto_run_seconds')  #
                self.countdown_button = self.CountdownButton(self)
                self.countdown_button.move(self.btn_rerun.x() - 20, self.btn_rerun.y() + 4)  # Adjust the position as needed

                self.countdown_button.clicked.connect(self.countdown_stop_btn_clicked)

                self.timer = QTimer(self)
                self.timer.timeout.connect(self.update_countdown)
                self.timer.start(1000)  # Start countdown timer with 1-second interval

        def countdown_stop_btn_clicked(self):
            self.countdown_stopped = True
            self.countdown_button.hide()

        def split_lang_and_code(self, text):
            if text.startswith('```') and text.endswith('```'):
                lang, code = text[3:-3].split('\n', 1)
                # code = code.rstrip('\n')
                return lang, code
            return None, text

        def enterEvent(self, event):
            self.check_and_toggle_rerun_button()
            self.reset_countdown()
            super().enterEvent(event)

        def leaveEvent(self, event):
            self.check_and_toggle_rerun_button()
            self.reset_countdown()
            super().leaveEvent(event)

        def update_countdown(self):
            if self.countdown > 0:
                # if True:  # not self.main.parent().parent().parent().expanded:
                #     self.reset_countdown()
                self.countdown -= 1
                self.countdown_button.setText(f"{self.countdown}")
            else:
                self.timer.stop()
                self.countdown_button.hide()
                if hasattr(self, 'countdown_stopped'):
                    self.countdown_stopped = True

                self.btn_rerun.click()

        def reset_countdown(self):
            countdown_stopped = getattr(self, 'countdown_stopped', True)
            if countdown_stopped: return
            self.timer.stop()
            self.countdown = self.agent.config.get('code_interpreter.auto_run_seconds')  # 5  # Reset countdown to 5 seconds
            self.countdown_button.setText(f"{self.countdown}")
            # if self.main.parent().parent().expanded and not self.underMouse():
            if not self.underMouse():
                self.timer.start()  # Restart the timer

        def check_and_toggle_rerun_button(self):
            if self.underMouse():
                self.btn_rerun.show()
            else:
                self.btn_rerun.hide()

        class BubbleButton_Rerun_Code(QPushButton):
            def __init__(self, parent=None):
                super().__init__(parent=parent, icon=QIcon())
                self.bubble = parent
                self.setProperty("class", "rerun")
                self.clicked.connect(self.rerun_code)

                icon = QIcon(QPixmap("./utils/resources/icon-run.png"))
                self.setIcon(icon)

            def rerun_code(self):
                # Implement the functionality for rerunning the code
                pass

        class CountdownButton(QPushButton):
            def __init__(self, parent):
                super().__init__(parent=parent)
                self.setText(str(parent.agent.config.get('code.auto_run_seconds')))  # )
                self.setIcon(QIcon())  # Initially, set an empty icon
                self.setStyleSheet("color: white;")
                self.setFixedHeight(22)
                self.setFixedWidth(22)

            def enterEvent(self, event):
                icon = QIcon(QPixmap("./utils/resources/close.png"))
                self.setIcon(icon)
                self.setText("")  # Clear the text when displaying the icon
                super().enterEvent(event)

            def leaveEvent(self, event):
                self.setIcon(QIcon())  # Clear the icon
                self.setText(str(self.parent().countdown))  # Reset the text to the current countdown value
                super().leaveEvent(event)

        def contextMenuEvent(self, event):
            global PIN_STATE
            # Create the standard context menu
            menu = self.createStandardContextMenu()

            # Add a separator to distinguish between standard and custom actions
            menu.addSeparator()

            # Create your custom actions
            action_one = menu.addAction("Action One")
            action_two = menu.addAction("Action Two")

            # Connect actions to functions
            action_one.triggered.connect(self.action_one_function)
            action_two.triggered.connect(self.action_two_function)

            # Highlight the bubble visually
            # self.highlight_bubble()

            current_pin_state = PIN_STATE
            PIN_STATE = True
            # Show the context menu at current mouse position
            menu.exec_(event.globalPos())
            PIN_STATE = current_pin_state

            # Revert the highlight after the menu is closed
            # self.unhighlight_bubble()

        def action_one_function(self):
            # Do something for action one
            pass

        def action_two_function(self):
            # Do something for action two
            pass

    def load_new_code_bubbles(self):
        last_bubble_id = 0
        for bubble in reversed(self.chat_bubbles):
            if bubble.msg_id == -1: continue
            last_bubble_id = bubble.msg_id  # todo - dirty
            break

        # last_bubble_id = self.chat_bubbles[-1].msg_id
        msgs = self.agent.context.message_history.get(msg_limit=30,
                                                      pad_consecutive=False,
                                                      only_role_content=False,
                                                      incl_roles=('code',),
                                                      from_msg_id=last_bubble_id + 1)
        for msg in msgs:
            self.insert_bubble(msg)

    def load_bubbles(self):  # , is_first_load=False):  # todo - rename
        self.clear_bubbles()
        msgs = self.agent.context.message_history.get(msg_limit=30,
                                                      pad_consecutive=False,
                                                      only_role_content=False,
                                                      incl_roles=('user', 'assistant', 'code'))
        for msg in msgs:
            self.insert_bubble(msg, is_first_load=True)

        self.topbar.set_agent(self.agent)

    def clear_bubbles(self):
        while self.chat_bubbles:
            bubble = self.chat_bubbles.pop()
            self.chat_scroll_layout.removeWidget(bubble)
            bubble.deleteLater()

        # # clear all bubble widgets in the scroll area
        # for b in self.chat_bubbles
        # for i in reversed(range(self._scroll_layout.count())):
        #     self._scroll_layout.removeWidget(self._scroll_layout.itemAt(i).widget())

    def on_button_click(self):
        self.send_message(self.main.message_text.toPlainText(), clear_input=True)

    def send_message(self, message, role='user', clear_input=False):
        global PIN_STATE
        try:
            new_msg = self.agent.save_message(role, message)
        except Exception as e:
            # show error message box
            old_pin_state = PIN_STATE
            PIN_STATE = True
            QMessageBox.critical(self, "Error", "OpenAI API Error: " + str(e))
            PIN_STATE = old_pin_state
            return

        if not new_msg:
            return

        if clear_input:
            # QTimer.singleShot(1, self.main.message_text.clear)
            QTimer.singleShot(1, self.main.message_text.clear)
            self.main.message_text.setFixedHeight(51)
            self.main.send_button.setFixedHeight(51)

        if role == 'user':
            self.main.new_bubble_signal.emit({'id': new_msg.id, 'role': 'user', 'content': new_msg.content})
            self.scroll_to_end()

        for key, chunk in self.agent.receive(stream=True):
            if key == 'assistant' or key == 'message':
                self.main.new_sentence_signal.emit(chunk)
                self.scroll_to_end()
            else:
                break

        self.load_new_code_bubbles()

    # self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
    @Slot(dict)
    def insert_bubble(self, message=None, is_first_load=False):
        viewport = self
        msg_role = message['role']

        if msg_role == 'user':
            bubble = self.MessageBubbleUser(message['id'], message['content'], viewport, role=msg_role, parent=self)
        elif msg_role == 'code':
            bubble = self.MessageBubbleCode(message['id'], message['content'], viewport, role=msg_role, parent=self, start_timer=not is_first_load)
        else:
            bubble = self.MessageBubbleBase(message['id'], message['content'], viewport, role=msg_role, parent=self)

        self.chat_bubbles.append(bubble)
        count = len(self.chat_bubbles)

        if msg_role == 'assistant':
            self.last_assistant_bubble = bubble
        else:
            self.last_assistant_bubble = None

        self.chat_scroll_layout.insertWidget(count - 1, bubble)

        return bubble

    @Slot(str)
    def new_sentence(self, sentence):
        if self.last_assistant_bubble is None:
            self.main.new_bubble_signal.emit({'id': -1, 'role': 'assistant', 'content': sentence})
            # self.last_assistant_bubble = nb
        else:
            self.last_assistant_bubble.append_text(sentence)
        # self.scroll_to_end()

    def scroll_to_end(self):
        QCoreApplication.processEvents()  # process GUI events to update content size
        scrollbar = self.main.page_chat.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum() + 20)
        # QCoreApplication.processEvents()


class SideBar(QWidget):
    def __init__(self, main):
        super().__init__(parent=main)
        self.main = main
        self.setObjectName("SideBarWidget")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setProperty("class", "sidebar")

        self.btn_new_context = self.SideBar_NewContext(self)
        self.btn_settings = self.SideBar_Settings(main=main)
        self.btn_agents = self.SideBar_Agents(main=main)
        self.btn_contexts = self.SideBar_Contexts(main=main)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Create a button group and add buttons to it
        self.button_group = QButtonGroup(self)
        self.button_group.addButton(self.btn_new_context, 0)
        self.button_group.addButton(self.btn_settings, 1)
        self.button_group.addButton(self.btn_agents, 2)
        self.button_group.addButton(self.btn_contexts, 3)  # 1

        self.title_bar = TitleButtonBar(self.main)
        self.layout.addWidget(self.title_bar)
        self.layout.addStretch(1)

        self.layout.addWidget(self.btn_settings)
        self.layout.addWidget(self.btn_agents)
        self.layout.addWidget(self.btn_contexts)
        self.layout.addWidget(self.btn_new_context)

    def update_buttons(self):
        is_current_chat = self.main.content.currentWidget() == self.main.page_chat
        icon_iden = 'chat' if not is_current_chat else 'new-large'
        icon = QIcon(QPixmap(f"./utils/resources/icon-{icon_iden}.png"))
        self.btn_new_context.setIcon(icon)

    class SideBar_NewContext(QPushButton):
        def __init__(self, parent):
            super().__init__(parent=parent, icon=QIcon())
            self.parent = parent
            self.main = parent.main
            self.clicked.connect(self.new_context)
            self.icon = QIcon(QPixmap("./utils/resources/icon-new-large.png"))
            self.setIcon(self.icon)
            self.setToolTip("New context")
            self.setFixedSize(50, 50)
            self.setIconSize(QSize(50, 50))
            self.setCheckable(True)
            # set class = homebutton
            self.setObjectName("homebutton")

        def new_context(self):
            is_current_widget = self.main.content.currentWidget() == self.main.page_chat
            if is_current_widget:
                self.main.page_chat.agent.context.new_context()
                self.main.page_chat.load_bubbles()
            else:
                # self.main.page_chat.agent = Agent(agent_id=None)
                self.load_chat()
                # # Manually uncheck all other buttons in the group
                # for button in self.parent.button_group.buttons():
                #     button.setChecked(False)

        def load_chat(self):
            self.main.content.setCurrentWidget(self.main.page_chat)
            self.main.page_chat.load_bubbles()

    class SideBar_Settings(QPushButton):
        def __init__(self, main):
            super().__init__(parent=main, icon=QIcon())
            self.main = main
            self.clicked.connect(self.open_settins)
            self.icon = QIcon(QPixmap("./utils/resources/icon-settings.png"))
            self.setIcon(self.icon)
            self.setToolTip("Settings")
            self.setFixedSize(50, 50)
            self.setIconSize(QSize(50, 50))
            self.setCheckable(True)

        def open_settins(self):
            self.main.content.setCurrentWidget(self.main.page_settings)

    class SideBar_Agents(QPushButton):
        def __init__(self, main):
            super().__init__(parent=main, icon=QIcon())
            self.main = main
            self.clicked.connect(self.open_settins)
            self.icon = QIcon(QPixmap("./utils/resources/icon-agent.png"))
            self.setIcon(self.icon)
            self.setToolTip("Agents")
            self.setFixedSize(50, 50)
            self.setIconSize(QSize(50, 50))
            self.setCheckable(True)

        def open_settins(self):
            self.main.content.setCurrentWidget(self.main.page_agents)

    class SideBar_Contexts(QPushButton):
        def __init__(self, main):
            super().__init__(parent=main, icon=QIcon())
            self.main = main
            self.clicked.connect(self.open_contexts)
            self.icon = QIcon(QPixmap("./utils/resources/icon-contexts.png"))
            self.setIcon(self.icon)
            self.setToolTip("Contexts")
            self.setFixedSize(50, 50)
            self.setIconSize(QSize(50, 50))
            self.setCheckable(True)

        def open_contexts(self):
            self.main.content.setCurrentWidget(self.main.page_contexts)


# class TopBar(QWidget):
#     def __init__(self, parent=None):
#         super().__init__(parent=parent)
#         self.setFixedHeight(50)


# class ButtonBar(QWidget):
#     def __init__(self, parent=None):
#         super().__init__(parent=parent)
#         self.setObjectName("TitleBarWidget")
#         self.setAttribute(Qt.WA_StyledBackground, True)
#         self.setFixedHeight(20)
#         sizePolicy = QSizePolicy()
#         sizePolicy.setHorizontalPolicy(QSizePolicy.Policy.Fixed)
#
#         self.btn_personality = self.ButtonBar_Personality(parent=self)
#         self.btn_jailbreak = self.ButtonBar_Jailbreak(parent=self)
#         self.btn_interpreter = self.ButtonBar_OpenInterpreter(parent=self)
#         # self.layout.addWidget(self.minimizeButton)
#         # self.layout.addWidget(self.closeButton)
#         self.layout = QHBoxLayout(self)
#         self.layout.setSpacing(0)
#         self.layout.setContentsMargins(0, 0, 0, 0)
#         self.layout.addStretch(1)
#         self.layout.addWidget(self.btn_interpreter)
#         self.layout.addWidget(self.btn_personality)
#         self.layout.addWidget(self.btn_jailbreak)
#         # self.layout.addWidget(self.closeButton)
#         self.setMouseTracking(True)
#         self._pressed = False
#         self._cpos = None
#         # make the title bar transparent
#         self.setAttribute(Qt.WA_TranslucentBackground, True)
#
#     class ButtonBar_Personality(QPushButton):
#         def __init__(self, parent=None):
#             super().__init__(parent=parent, icon=QIcon())
#             self.setFixedHeight(20)
#             self.setFixedWidth(20)
#             self.clicked.connect(self.toggle_personality)
#             self.icon = QIcon(QPixmap("./utils/resources/icon-drama-on.png"))
#             self.setIcon(self.icon)
#             self.setToolTip("Personality")
#
#         def toggle_personality(self):
#             global PERSONALITY_STATE
#             PERSONALITY_STATE = not PERSONALITY_STATE
#             icon_iden = "on" if PERSONALITY_STATE else "off"
#             icon_file = f"./utils/resources/icon-drama-{icon_iden}.png"
#             self.icon = QIcon(QPixmap(icon_file))
#             self.setIcon(self.icon)
#
#     class ButtonBar_Jailbreak(QPushButton):
#         def __init__(self, parent=None):
#             super().__init__(parent=parent, icon=QIcon())
#             self.setFixedHeight(20)
#             self.setFixedWidth(20)
#             self.clicked.connect(self.toggle_personality)
#             self.icon = QIcon(QPixmap("./utils/resources/icon-jailbreak-on.png"))
#             self.setIcon(self.icon)
#             self.setToolTip("Jailbreak")
#
#         def toggle_personality(self):
#             global PERSONALITY_STATE
#             PERSONALITY_STATE = not PERSONALITY_STATE
#             icon_iden = "on" if PERSONALITY_STATE else "off"
#             icon_file = f"./utils/resources/icon-jailbreak-{icon_iden}.png"
#             self.icon = QIcon(QPixmap(icon_file))
#             self.setIcon(self.icon)
#
#     class ButtonBar_OpenInterpreter(QPushButton):
#         def __init__(self, parent=None):
#             super().__init__(parent=parent, icon=QIcon())
#             self.setFixedHeight(20)
#             self.setFixedWidth(20)
#             self.clicked.connect(self.toggle_openinterpreter)
#             self.icon = QIcon(QPixmap("./utils/resources/icon-interpreter-on.png"))
#             self.setIcon(self.icon)
#             self.setToolTip("Open Interpreter")
#
#         def toggle_openinterpreter(self):
#             global OPEN_INTERPRETER_STATE
#             # 3 WAY TOGGLE
#             OPEN_INTERPRETER_STATE = ((OPEN_INTERPRETER_STATE + 1 + 1) % 3) - 1
#             icon_iden = "on" if OPEN_INTERPRETER_STATE == 0 else "forced" if OPEN_INTERPRETER_STATE == 1 else "off"
#             icon_file = f"./utils/resources/icon-interpreter-{icon_iden}.png"
#             self.icon = QIcon(QPixmap(icon_file))
#             self.setIcon(self.icon)


class MessageText(QTextEdit):
    enterPressed = Signal()

    def __init__(self, main=None):
        super().__init__(parent=None)
        self.parent = main
        self.agent = main.page_chat.agent
        self.setCursor(QCursor(Qt.PointingHandCursor))
        # self.setFixedSize(self.sizeHint())

    def keyPressEvent(self, event):
        combo = event.keyCombination()
        key = combo.key()
        mod = combo.keyboardModifiers()

        # Check for Ctrl + B key combination
        if key == Qt.Key.Key_B and mod == Qt.KeyboardModifier.ControlModifier:
            # Insert the code block where the cursor is
            cursor = self.textCursor()
            cursor.insertText("```\n\n```")  # Inserting with new lines between to create a space for the code
            cursor.movePosition(QTextCursor.PreviousBlock, QTextCursor.MoveAnchor, 1)  # Move cursor inside the code block
            self.setTextCursor(cursor)
            self.setFixedSize(self.sizeHint())
            return  # We handle the event, no need to pass it to the base class

        if key == Qt.Key.Key_Enter or key == Qt.Key.Key_Return:
            if mod == Qt.KeyboardModifier.ShiftModifier:
                event.setModifiers(Qt.KeyboardModifier.NoModifier)
                return super().keyPressEvent(event)
            else:
                # last_role_was_user = self.agent.context.message_history.last_role() == 'user'
                # msg_has_text = self.toPlainText().strip() != ''
                # if not msg_has_text and last_role_was_user:
                #     last_user_msg = self.agent.context.message_history.last()['content']
                #     self.setPlainText(last_user_msg)
                if self.toPlainText().strip() == '':
                    return
                return self.enterPressed.emit()

        se = super().keyPressEvent(event)
        self.setFixedSize(self.sizeHint())
        self.parent.sync_send_button_size()
        return se

    def sizeHint(self):
        # Use QTextDocument for more accurate text measurements
        doc = QTextDocument()
        doc.setDefaultFont(self.font())
        doc.setPlainText(self.toPlainText())

        # Assuming you want to keep a minimum height for 3 lines of text
        min_height_lines = 3

        # Calculate the required width and height
        text_rect = doc.documentLayout().documentSize()
        width = self.width()
        font_height = QFontMetrics(self.font()).height()
        num_lines = max(min_height_lines, text_rect.height() / font_height)

        # Calculate height based on the number of lines
        height = int(font_height * num_lines)

        return QSize(width, height)

    files = []

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            self.files.append(url.toLocalFile())
            # insert text where cursor is

        event.accept()

    def insertFromMimeData(self, source: QMimeData):
        """
        Reimplemented from QTextEdit.insertFromMimeData().
        Inserts plain text data from the MIME data source.
        """
        # Check if the MIME data source has text
        if source.hasText():
            # Get the plain text from the source
            text = source.text()

            # Insert the plain text at the current cursor position
            self.insertPlainText(text)
        else:
            # If the source does not contain text, call the base class implementation
            super().insertFromMimeData(source)


class SendButton(QPushButton):
    def __init__(self, text, msgbox, parent=None):
        super().__init__(text, parent=parent)
        self._parent = parent
        self.msgbox = msgbox
        self.icon = QIcon(QPixmap("./utils/resources/icon-send.png"))
        self.setIcon(self.icon)

    def minimumSizeHint(self):
        return self.sizeHint()

    def sizeHint(self):
        height = self._parent.message_text.height()
        width = 70
        return QSize(width, height)


class Main(QMainWindow):
    new_bubble_signal = Signal(dict)
    new_sentence_signal = Signal(str)

    mouseEntered = Signal()
    mouseLeft = Signal()

    def check_db(self):
        # Check if the database is available
        while not check_database():
            # If not, show a QFileDialog to get the database location
            sql.db_path, _ = QFileDialog.getOpenFileName(None, "Open Database", "", "Database Files (*.db);;All Files (*)")

            if not sql.db_path:
                QMessageBox.critical(None, "Error", "Database not selected. Application will exit.")
                return

            # Set the database location in the agent
            config.set_value('system.db_path', sql.db_path)

    def __init__(self):  # , base_agent=None):
        super().__init__()
        self.check_db()

        self.leave_timer = QTimer(self)
        self.leave_timer.setSingleShot(True)
        self.leave_timer.timeout.connect(self.collapse)

        self.setWindowTitle('OpenAgent')
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowIcon(QIcon('./utils/resources/icon.png'))
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.central = QWidget()
        self.central.setProperty("class", "central")
        self._layout = QVBoxLayout(self.central)
        self.setMouseTracking(True)

        self.sidebar = SideBar(self)

        self.content = QStackedWidget(self)
        self.page_chat = Page_Chat(self)
        self.page_settings = Page_Settings(self)
        self.page_agents = Page_Agents(self)
        self.page_contexts = Page_Contexts(self)
        self.content.addWidget(self.page_chat)
        self.content.addWidget(self.page_settings)
        self.content.addWidget(self.page_agents)
        self.content.addWidget(self.page_contexts)
        self.content.currentChanged.connect(self.load_page)

        # self.page_chat.agent = base_agent

        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_layout.setSpacing(0)
        self.sidebar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        # Horizontal layout for content and sidebar
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.content)
        hlayout.addWidget(self.sidebar)
        hlayout.setSpacing(0)

        self.content_container = QWidget()
        self.content_container.setLayout(hlayout)

        # self.sidebar_layout.addStretch(1)

        # Adding the scroll area to the main layout
        self._layout.addWidget(self.content_container)

        # Message text and send button
        # self.button_bar = ButtonBar()
        self.message_text = MessageText(main=self)
        self.message_text.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.send_button = SendButton('', self.message_text, self)
        self.message_text.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.send_button.setFixedSize(70, 51)
        self.message_text.setFixedHeight(51)
        self.message_text.setProperty("class", "msgbox")
        self.send_button.setProperty("class", "send")

        # Horizontal layout for message text and send button
        self.hlayout = QHBoxLayout()
        self.hlayout.addWidget(self.message_text)
        self.hlayout.addWidget(self.send_button)
        # self.spacer = QSpacerItem(0, 0)
        self.hlayout.setSpacing(0)
        # Button bar should not stretch vertically

        # Vertical layout for button bar and input layout
        input_layout = QVBoxLayout()
        # input_layout.addWidget(self.button_bar)
        input_layout.addLayout(self.hlayout)

        # Create a QWidget to act as a container for the input widgets and button bar
        input_container = QWidget()
        input_container.setLayout(input_layout)

        # Adding input layout to the main layout
        self._layout.addWidget(input_container)
        self._layout.setSpacing(1)

        self.setCentralWidget(self.central)
        self.send_button.clicked.connect(self.page_chat.on_button_click)
        self.message_text.enterPressed.connect(self.page_chat.on_button_click)

        self.new_bubble_signal.connect(self.page_chat.insert_bubble)
        self.new_sentence_signal.connect(self.page_chat.new_sentence)
        self.oldPosition = None
        self.expanded = False

        self.show()
        self.page_chat.load_bubbles()

    # def collapse(self):
    #     global PIN_STATE
    #     if PIN_STATE: return
    #     if not self.expanded: return
    #
    #     self.expanded = False
    #     self.content_container.hide()  # First, hide the content
    #     QApplication.processEvents()  # Process any pending events
    #
    #     if self.is_bottom_corner():
    #         new_width, new_height = 50, 100
    #         x = self.x() + self.width() - new_width
    #         y = self.y() + self.height() - new_height
    #
    #         # Debugging print statements; remove these once the issue is resolved
    #         print(f"Old Position: ({self.x()}, {self.y()}), Old Size: ({self.width()}x{self.height()})")
    #         print(f"New Position: ({x}, {y}), New Size: ({new_width}x{new_height})")
    #
    #         self.resize(new_width, new_height)  # Resize before moving
    #         self.move(x, y)  # Then move to new position

    def sync_send_button_size(self):
        self.send_button.setFixedHeight(self.message_text.height())

    def is_bottom_corner(self):
        screen_geo = QGuiApplication.primaryScreen().geometry() # get screen geometry
        win_geo = self.geometry()  # get window geometry
        win_x = win_geo.x()
        win_y = win_geo.y()
        win_width = win_geo.width()
        win_height = win_geo.height()
        screen_width = screen_geo.width()
        screen_height = screen_geo.height()
        win_right = win_x + win_width >= screen_width
        win_bottom = win_y + win_height >= screen_height
        is_right_corner = win_right and win_bottom
        return is_right_corner

    # def expand(self):
    #     if self.expanded: return
    #     self.expanded = True
    #
    #     new_width, new_height = 700, 750
    #     x = self.x() - (new_width - self.width())
    #     y = self.y() - (new_height - self.height())
    #
    #     # Same debugging print statements
    #     print(f"Old Position: ({self.x()}, {self.y()}), Old Size: ({self.width()}x{self.height()})")
    #     print(f"New Position: ({x}, {y}), New Size: ({new_width}x{new_height})")
    #
    #     self.resize(new_width, new_height)  # Resize before moving
    #     self.move(x, y)  # Then move to new position
    #
    #     self.content_container.show()  # Finally, show the content
    #     QApplication.processEvents()
    #
    def collapse(self):
        global PIN_STATE
        if PIN_STATE: return
        if not self.expanded: return

        if self.is_bottom_corner():
            self.message_text.hide()
            self.send_button.hide()
            self.change_width(50)

        self.expanded = False
        self.content_container.hide()
        QApplication.processEvents()
        # self.button_bar.hide()
        self.change_height(100)

    def expand(self):
        if self.expanded: return
        self.expanded = True
        self.change_height(750)
        self.change_width(700)
        self.content_container.show()
        self.message_text.show()
        self.send_button.show()
        # self.button_bar.show()

    def mousePressEvent(self, event):
        self.oldPosition = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.oldPosition is None: return
        delta = QPoint(event.globalPosition().toPoint() - self.oldPosition)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPosition = event.globalPosition().toPoint()

    def enterEvent(self, event):
        self.leave_timer.stop()
        self.expand()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.leave_timer.start(1000)
        super().leaveEvent(event)

    def change_height(self, height):
        old_height = self.height()
        self.setFixedHeight(height)
        self.move(self.x(), self.y() - (height - old_height))

    def change_width(self, width):
        old_width = self.width()
        self.setFixedWidth(width)
        self.move(self.x() - (width - old_width), self.y())

    def sizeHint(self):
        return QSize(600, 100)

    def load_page(self, index):
        self.sidebar.update_buttons()
        page = self.content.widget(index)
        if page == self.page_agents:
            self.page_agents.load_agents()
        elif page == self.page_contexts:
            self.page_contexts.load_contexts()


class NoWheelSpinBox(QSpinBox):
    """A SpinBox that does not react to mouse wheel events."""

    def wheelEvent(self, event):
        event.ignore()

class NoWheelComboBox(QComboBox):
    """A SpinBox that does not react to mouse wheel events."""

    def wheelEvent(self, event):
        event.ignore()

def create_checkbox(self, label, initial_value):
    cb = QCheckBox(label, self)
    cb.setChecked(initial_value)
    return cb

def create_lineedit(self, initial_value=''):
    le = QLineEdit(self)
    le.setText(str(initial_value))
    return le

def create_combobox(self, items, initial_value):
    cb = QComboBox(self)
    for item in items:
        cb.addItem(item)
    cb.setCurrentText(initial_value)
    return cb

def create_folder_button(self, initial_value):
    btn = QPushButton("Select Folder", self)
    btn.clicked.connect(lambda: self.select_folder(btn, initial_value))
    return btn

def select_folder(self, button, initial_value):
    folder = QFileDialog.getExistingDirectory(self, "Select Folder", initial_value)
    folder.setStyleSheet("color: white;")
    if folder:
        # Store the folder to config or use it as you need
        pass


class GUI:
    def __init__(self):
        pass

    def run(self):
        app = QApplication(sys.argv)
        app.setStyleSheet(STYLE)
        m = Main()  # self.agent)
        m.expand()
        app.exec()
