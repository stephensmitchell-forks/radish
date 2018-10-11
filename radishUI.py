# --------------------
#       Modules
# --------------------

# PySide 2
from PySide2.QtUiTools import QUiLoader
import PySide2.QtWidgets as QtW
from PySide2.QtCore import QFile

# 3ds Max
import pymxs
import MaxPlus

# Misc
import logging
import sys
import os

# For 3ds Max - Temporarily add this file's directory to PATH
sys.path.append(os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))))

# Local modules
import radish_utilities as util

rt = pymxs.runtime
max_out = util.max_out
_radish_log_handler = util.CustomHandler()


# --------------------
#     Logger setup
# --------------------
_log = logging.getLogger("Radish")
_log.setLevel(logging.DEBUG)
# Clean up old handlers before re-initializing
# Important, as the user may re-launch this script without re-launching the parent program
if _log.handlers:
    _log.info('Resetting Logger...')
    for handler in list(_log.handlers):
        _log.removeHandler(handler)
# Add custom handler
_log.addHandler(_radish_log_handler)

_log.info('Logger active')


# --------------------
#      UI Class
# --------------------

class RadishUI(QtW.QDialog):

    def __init__(self, ui_file, runtime, parent=MaxPlus.GetQMaxMainWindow()):
        """
        The Initialization of the main UI class
        :param ui_file: The path to the .UI file from QDesigner
        :param runtime: The pymxs runtime
        :param parent: The main Max Window
        """
        super(RadishUI, self).__init__(parent)

        # ---------------------------------------------------
        #                    Variables
        # ---------------------------------------------------

        self._ui_file_string = ui_file
        self._parent = parent
        self._rt = runtime

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
        #                   Widget Setup
        # ---------------------------------------------------

        # Cams
        self._rd_cam_le = self.findChild(QtW.QLineEdit, 'rd_cam_le')
        self._rd_cam_chk = self.findChild(QtW.QCheckBox, 'rd_cam_override_chk')
        self._rd_cam_cb = self.findChild(QtW.QComboBox, 'rd_cam_override_cb')

        # Passes
        self._rd_pass_cb = self.findChild(QtW.QComboBox, 'rd_selpass_cb')
        self._rd_pass_le = self.findChild(QtW.QLineEdit, 'rd_selpass_cust_le')

        # Save / Load
        self._rd_save_btn = self.findChild(QtW.QPushButton, 'rd_save_btn')
        self._rd_load_btn = self.findChild(QtW.QPushButton, 'rd_load_btn')

        # Resets
        self._rd_resetpass_btn = self.findChild(QtW.QPushButton, 'rd_clear_pass_btn')
        self._rd_resetcam_btn = self.findChild(QtW.QPushButton, 'rd_clear_cam_btn')
        self._rd_resetall_btn = self.findChild(QtW.QPushButton, 'rd_clear_project_btn')

        # Info
        self._rd_config_le = self.findChild(QtW.QLineEdit, 'rd_config_le')
        self._rd_status_label = self.findChild(QtW.QLabel, 'rd_status_label')

        # ---------------------------------------------------
        #                Function Connections
        # ---------------------------------------------------

        # Cams
        self._rd_cam_chk.stateChanged.connect(self._rd_cam_override)

        # Passes
        self._rd_pass_cb.currentIndexChanged.connect(self._rd_pass_override)

        # Save / Load
        self._rd_save_btn.clicked.connect(self.rd_save)
        self._rd_load_btn.clicked.connect(self.rd_load)

        # Resets
        self._rd_resetpass_btn.clicked.connect(self.rd_reset_pass)
        self._rd_resetcam_btn.clicked.connect(self.rd_reset_cam)
        self._rd_resetall_btn.clicked.connect(self.rd_reset_all)

        # ---------------------------------------------------
        #                  Parameter Setup
        # ---------------------------------------------------

        # Stores indices for pass combobox
        self._passes = {'beauty': 0, 'prepass': 1, 'custom': 2}

        # Stores current active viewport
        self._camera = self._rt.getActiveCamera()

    # ---------------------------------------------------
    #                  Private Methods
    # ---------------------------------------------------

    # Cams

    # Check the state of the override checkbox, and toggle the override combobox accordingly
    def _rd_cam_override(self):
        _log.debug('_rd_cam_override')
        if self._rd_cam_chk.isChecked():
            self._rd_cam_le.setEnabled(False)
            self._rd_cam_cb.setEnabled(True)
        else:
            self._rd_cam_le.setEnabled(True)
            self._rd_cam_cb.setEnabled(False)

        return

    # Passes

    # Check the state of the pass combobox, if custom is selected unlock the input field for it.
    def _rd_pass_override(self):
        _log.debug('_rd_pass_override')
        if self._rd_pass_cb.currentIndex() == self._passes['custom']:
            self._rd_pass_le.setEnabled(True)
        else:
            self._rd_pass_le.setEnabled(False)

        return

    # Misc internal logic
    def _rd_get_settings(self):
        # Get all settings from dialog window and update class properties
        _log.debug('_rd_get_settings')

    # ---------------------------------------------------
    #                  Public Methods
    # ---------------------------------------------------

    # Save / Load
    def rd_save(self):
        _log.debug('rd_save')
        return

    def rd_load(self):
        _log.debug('rd_load')
        return

    # Resets
    def rd_reset_pass(self):
        _log.debug('rd_reset_pass')
        return

    def rd_reset_cam(self):
        _log.debug('rd_reset_cam')
        return

    def rd_reset_all(self):
        _log.debug('rd_reset_all')

    # Active Viewport handler
    def cam_change_handler(self):
        _log.debug('cam_change_handler')
        this_cam = self._rt.getActiveCamera()
        if self._camera != this_cam:
            _log.debug('cam_change_handler - Updating')
            self._camera = this_cam
            if self._camera is not None:
                self._rd_cam_le.setText(this_cam.name)
            else:
                self._rd_cam_le.setText('None')

        return


# --------------------
#    Dialog Setup
# --------------------

# Destroys instances of the dialog before recreating it
# This has to go before re-declaration of the ui variable
try:  # noinspection PyBroadException
    _log.info('Closing old instances of UI...')
    ui.close()  # noinspection PyUnboundLocalVariable
except:
    _log.info('No old instances found')
    pass

# Path to UI file
uif = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))) + "\\radish_standalone.ui"

app = MaxPlus.GetQMaxMainWindow()
ui = RadishUI(uif, rt, app)

# Punch it
ui.show()
log.info('UI created')

# --------------------
#  Cam Change Handler
# --------------------
rt.callbacks.removeScripts(rt.name("viewportChange"), id=rt.name("bdf_cameraChange"))
rt.callbacks.addScript(rt.name("viewportChange"),
                       "python.execute \"ui.cam_change_handler()\"",
                       id=rt.name("bdf_cameraChange"))
