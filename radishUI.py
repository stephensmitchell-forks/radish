# PySide 2
from PySide2.QtUiTools import QUiLoader
import PySide2.QtWidgets as QtW
from PySide2.QtCore import QFile

import MaxPlus
import sys
import os

# For 3ds Max - Temporarily add this file's directory to PATH
sys.path.append(os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))))

import util_pymxs as util

# Utility functions
max_out = util.max_out


class MaxDialogStarter(QtW.QDialog):

    def __init__(self, ui_file, parent=MaxPlus.GetQMaxMainWindow()):
        """
        The Initialization of the main UI class
        :param ui_file: The path to the .UI file from QDesigner
        :param parent: The main Max Window
        """
        super(MaxDialogStarter, self).__init__(parent)

        # ---------------------------------------------------
        #                    Variables
        # ---------------------------------------------------

        self._ui_file_string = ui_file
        self._parent = parent

        # ---------------------------------------------------
        #                     Main Init
        # ---------------------------------------------------

        # UI Loader

        ui_file = QFile(self._ui_file_string)
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self._widget = loader.load(ui_file)

        ui_file.close()

        # Attaches loaded UI to the dialog box

        main_layout = QtW.QVBoxLayout()
        main_layout.addWidget(self._widget)

        self.setLayout(main_layout)

        # Titling

        # self._window_title = "Optional Custom Title"
        # self.setWindowTitle(self._window_title)

        # ---------------------------------------------------
        #                 Widget Definitions
        # ---------------------------------------------------

        self._test_debug_layer = self.findChild(QtW.QLineEdit, 'jh_debug_layer')
        self._test_debug_light = self.findChild(QtW.QLineEdit, 'jh_debug_light')

        self._test_thing1_btn = self.findChild(QtW.QPushButton, 'jh_thing1_btn')
        self._test_thing2_btn = self.findChild(QtW.QPushButton, 'jh_thing2_btn')

        self._test_lineprint_btn = self.findChild(QtW.QPushButton, 'jh_lineprint_btn')
        self._test_lineprint_input = self.findChild(QtW.QLineEdit, 'jh_lineprint_input')

        # ---------------------------------------------------
        #                Function Definitions
        # ---------------------------------------------------

        self._test_thing1_btn.clicked.connect(self._test_do_thing1)  # Can't easily pass arguments, so call thing1 or
        self._test_thing2_btn.clicked.connect(self._test_do_thing2)  # thing2 directly.
        self._test_lineprint_btn.clicked.connect(self._test_lineprint)

    def _test_do_thing1(self):
        max_out('Thing 1')
        return

    def _test_do_thing2(self):
        max_out('Thing 2')
        return

    def _test_lineprint(self):
        max_out(self._test_lineprint_input.text())  # Get the contents of the line edit textbox with its .text() method
        return


# Code for opening the dialog

app = MaxPlus.GetQMaxMainWindow()
ui = MaxDialogStarter(uif, app)

# Path to UI file
uif = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))) + "\\qtDesignerTest.ui"

# Destroys instances of the dialog before recreating it
# noinspection PyBroadException
try:
    # noinspection PyUnboundLocalVariable
    ui.close()
except:
    pass

ui.show()
