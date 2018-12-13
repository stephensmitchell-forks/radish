# --------------------
#       Modules
# --------------------

# PySide 2
from PySide2.QtUiTools import QUiLoader
import PySide2.QtWidgets as QtW
from PySide2.QtCore import QFile

# 3ds Max
import MaxPlus

# Misc
import xml.etree.ElementTree as _ETree
import datetime
import sys
import os

# Local modules
import radish_utilities as util
import radish_io as rio

# Logging
import logging
_log = logging.getLogger('Radish.UI')
_log.info('Logger %s Active' % _log.name)

_get_instances = util.get_instances

_is_ascii = util.is_ascii
_xml_tag_cleaner = util.xml_tag_cleaner
_xml_get_bool = util.xml_get_bool
_xml_indent = util.xml_indent


# --------------------
#      UI Class
# --------------------

class RadishUI(QtW.QDialog):
    # TODO: Reorganize RadishUI class to only include UI-related code.

    def __init__(self, ui_file, runtime, parent_log, parent=MaxPlus.GetQMaxMainWindow()):
        """
        The Initialization of the main UI class
        :param ui_file: The path to the .UI file from QDesigner
        :param runtime: The pymxs runtime
        :param parent_log: The logger object used by the script which called RadishUI.
        :param parent: The main Max Window
        """
        # Init QtW.QDialog
        super(RadishUI, self).__init__(parent)
        # Set up callback for camera detection
        self._active_camera_callback = MaxPlus.NotificationManager.Register(MaxPlus.NotificationCodes.ViewportChange,
                                                                            self._active_camera_handler)

        # ---------------------------------------------------
        #                    Variables
        # ---------------------------------------------------

        self._ui_file_string = ui_file
        self._rt = runtime
        self._parent_log = parent_log
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
        #                   Widget Setup
        # ---------------------------------------------------

        # Cams
        self._rd_cam_le = self.findChild(QtW.QLineEdit, 'rd_cam_le')
        self._rd_cam_chk = self.findChild(QtW.QCheckBox, 'rd_cam_override_chk')
        self._rd_cam_cb = self.findChild(QtW.QComboBox, 'rd_cam_override_cb')

        # Passes
        self._rd_pass_cb = self.findChild(QtW.QComboBox, 'rd_selpass_cb')
        self._rd_pass_le = self.findChild(QtW.QLineEdit, 'rd_selpass_cust_le')

        # Options
        self._rd_opt_lights_chk = self.findChild(QtW.QCheckBox, 'rd_opt_lights_chk')
        self._rd_opt_layers_chk = self.findChild(QtW.QCheckBox, 'rd_opt_layers_chk')
        # self._rd_opt_resolution_chk = self.findChild(QtW.QCheckBox, 'rd_opt_resolution_chk')
        # self._rd_opt_effects_chk = self.findChild(QtW.QCheckBox, 'rd_opt_effects_chk')
        # self._rd_opt_elements_chk = self.findChild(QtW.QCheckBox, 'rd_opt_elements_chk')

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

        # Dev
        self._dev_logger_cb = self.findChild(QtW.QComboBox, 'dev_logger_cb')

        # ---------------------------------------------------
        #                Function Connections
        # ---------------------------------------------------

        # Cams
        self._rd_cam_chk.stateChanged.connect(self._rd_cam_override_handler)

        # Passes
        self._rd_pass_cb.currentIndexChanged.connect(self._rd_pass_handler)

        # Save / Load
        self._rd_save_btn.clicked.connect(self.rd_save)
        self._rd_load_btn.clicked.connect(self.rd_load)

        # Resets
        self._rd_resetpass_btn.clicked.connect(self.rd_reset_pass)
        self._rd_resetcam_btn.clicked.connect(self.rd_reset_cam)
        self._rd_resetall_btn.clicked.connect(self.rd_reset_all)

        # Dev
        self._dev_logger_cb.currentIndexChanged.connect(self._dev_logger_handler)

        # ---------------------------------------------------
        #                  Attribute Setup
        # ---------------------------------------------------

        # Attributes used for navigating the XML config
        self._tgt_project = 'TEST'
        self._tgt_cam = None
        self._tgt_pass = None

        # Stores text for pass combobox
        self._passes = {'beauty': 'Beauty',
                        'prepass': 'Pre-Pass',
                        'custom': 'Custom...'}

        # Stores current active viewport
        self._active_cam = self._rt.getActiveCamera()

        # Stores current options, set by _rd_get_settings()
        self._options = {'lights': None,
                         'layers': None,
                         'resolution': None,
                         'effects': None,
                         'elements': None}

        # DEV - Set log level
        self._dev_logger_handler()

        # Finds and parses the config file using the specified handler
        # Also set up pass combobox, pulling custom passes from the loaded config
        try:
            self._rd_cfg = rio.RadishIO(runtime=self._rt,
                                        config_type='XML')
            self._rd_set_passes(self._rd_cfg)
        except:
            _log.exception('Radish failed to initialize!')
            self.close()

        # ---------------------------------------------------
        #               End of RadishUI Init
        # ---------------------------------------------------

        _log.info('RadishUI Initialized')

    # ---------------------------------------------------
    #                  Private Methods
    # ---------------------------------------------------

    # Cams

    def _rd_cam_override_handler(self):
        """
        Used by the UI to check the state of the override checkbox, and toggle the override combobox accordingly.
        Also re-builds the list of cameras when it's activated.
        :return:
        """
        _log.debug('_rd_cam_override_handler')
        if self._rd_cam_chk.isChecked():
            self._rd_cam_le.setEnabled(False)
            self._rd_cam_cb.setEnabled(True)

            tmp_cams = []

            for c in self._rt.cameras:
                if len(self._rt.getPropNames(c)) == 0:
                    continue
                else:
                    tmp_cams.append(str(c.name))

            self._rd_cam_cb.clear()
            self._rd_cam_cb.addItems(tmp_cams)

        else:
            self._rd_cam_le.setEnabled(True)
            self._rd_cam_cb.setEnabled(False)

    def _active_camera_handler(self, code):
        """
        This is used by the ViewportChange callback set in the RadishUI init.  It checks for changes in the
        active camera view, and updates the GUI and _active_cam param accordingly.
        :param code: Callback Code
        :return: None
        """
        _log.debug('_active_camera_handler called with event code %s' % str(code))
        this_cam = self._rt.getActiveCamera()
        if self._active_cam != this_cam:
            _log.info('_active_camera_handler - Updating')
            self._active_cam = this_cam
            if self._active_cam is not None:
                self._rd_cam_le.setText(this_cam.name)
            else:
                self._rd_cam_le.setText('None')

    # Passes

    def _rd_pass_handler(self):
        """
        Check the state of the pass combobox, if custom is selected unlock the input field for it.
        :return: None
        """
        _log.debug('_rd_pass_handler')
        if self._rd_pass_cb.currentText() == self._passes['custom']:
            self._rd_pass_le.setEnabled(True)
        else:
            self._rd_pass_le.setEnabled(False)

    def _rd_set_passes(self, cfg):
        """
        Populates the pass combobox with default values and any custom passes found in the config.
        :param cfg: Initialized RadishIO object
        :return: None
        """
        _log.debug('_rd_set_passes')
        passes = cfg.get_all_passes()
        append_list = []

        # Reset the CB
        self._rd_pass_cb.clear()

        self._rd_pass_cb.addItems([self._passes['beauty'],
                                   self._passes['prepass'],
                                   self._passes['custom']])

        for name in passes:
            if name not in self._passes.itervalues():
                append_list.append(name)

        self._rd_pass_cb.insertItems(2, append_list)

        _log.debug('last_pass = %s' % self._tgt_pass)
        pass_index = self._rd_pass_cb.findText(self._tgt_pass)
        if pass_index >= 0:
            self._rd_pass_cb.setCurrentIndex(pass_index)

    # Dev

    def _dev_logger_handler(self):
        """
        Handles setting the logger level based on the UI ComboBox.
        :return: None
        """
        _log.debug('_dev_logger_handler')
        self._parent_log.setLevel(getattr(logging, self._dev_logger_cb.currentText()))

    # Misc internal logic

    def _rd_get_settings(self):
        """
        Get all settings from dialog window and update the ._tgt_cam, ._tgt_pass, and ._options class attributes.
        """
        _log.debug('_rd_get_settings')

        settings_valid = True

        # Cam
        if self._rd_cam_chk.isChecked():
            self._tgt_cam = self._rd_cam_cb.currentText()
        else:
            self._tgt_cam = self._rd_cam_le.text()
        if _is_ascii(self._tgt_cam) is False:
            raise ValueError('Camera name must be a valid ASCII string, got %s' % self._tgt_cam)
        if self._tgt_cam == '':
            self._tgt_cam = 'BLANK'

        # Pass
        if self._rd_pass_cb.currentText() == self._passes['custom']:
            self._tgt_pass = self._rd_pass_le.text()
        else:
            self._tgt_pass = self._rd_pass_cb.currentText()
        if _is_ascii(self._tgt_pass) is False:
            raise ValueError('Pass name must be a valid ASCII string, got %s' % self._tgt_pass)
        if self._tgt_pass == '':
            self._tgt_pass = 'BLANK'

        # Options
        self._options['lights'] = self._rd_opt_lights_chk.isChecked()
        self._options['layers'] = self._rd_opt_layers_chk.isChecked()
        # self._options['resolution'] = self._rd_opt_resolution_chk.isChecked()
        # self._options['effects'] = self._rd_opt_effects_chk.isChecked()
        # self._options['elements'] = self._rd_opt_elements_chk.isChecked()

        _log.debug('Cam: %s  ---   Pass: %s  ---  Options: %s' % (self._tgt_cam, self._tgt_pass, self._options))


    # ---------------------------------------------------
    #                  Public Methods
    # ---------------------------------------------------

    # Save / Load
    def rd_save(self):
        """
        Save current scene state to RadishIO memory, then write it to disk.
        """
        _log.debug('rd_save')

        # Run _rd_get_settings(), and cancel saving if it returns an error
        try:
            self._rd_get_settings()
        except ValueError:
            _log.exception('Unable to record scene state - Failed to get settings from UI')
            return

        # Save state to memory, then update pass combobox and write to disk
        try:
            self._rd_cfg.save_state(self._tgt_cam, self._tgt_pass, self._options)
            self._rd_cfg.write()
        except:
            _log.exception('Unable to record scene state!')

        self._rd_set_passes(self._rd_cfg)


    def rd_load(self):
        """
        Load the config for the current camera pass and apply it to the scene.
        """
        _log.debug('rd_load')

        # Run _rd_get_settings(), and cancel saving if it returns an error
        try:
            self._rd_get_settings()
        except ValueError:
            _log.exception('Unable to load scene state - Failed to get settings from UI')
            return

        try:
            self._rd_cfg.load_state(self._tgt_cam, self._tgt_pass, self._options)
        except:
            _log.exception('Unable to load scene state!')


    # Resets
    def rd_reset_pass(self, tgt_cam=None, tgt_pass=None, save=True):
        """
        Calls RadishIO method to reset current camera pass.  If not passed arguments, get them from the UI.
        :param tgt_cam: String, name of camera
        :param tgt_pass: String, name of pass
        :param save: Bool, should we re-save the config after doing this
        :return: None
        """
        _log.debug('rd_reset_pass')

        if tgt_cam is None or tgt_pass is None:
            self._rd_get_settings()
            tgt_cam = self._tgt_cam
            tgt_pass = self._tgt_pass

        try:
            self._rd_cfg.reset_pass(tgt_cam, tgt_pass)
        except ValueError:
            _log.exception('Unable to Reset Pass %s!' % tgt_pass)

        # Update Pass list
        self._rd_set_passes(self._rd_cfg)

        if save:
            try:
                self._rd_cfg.write()
            except:
                _log.exception('Unable to save config after resetting Pass %s!' % tgt_pass)

    def rd_reset_cam(self, tgt_cam=None, save=True):
        """
        Calls RadishIO method to reset current camera.  If not passed arguments, get them from the UI.
        :param tgt_cam: String, name of camera
        :param save: Bool, should we re-save the config after doing this
        :return: None
        """
        _log.debug('rd_reset_cam')

        if tgt_cam is None:
            self._rd_get_settings()
            tgt_cam = self._tgt_cam

        try:
            self._rd_cfg.reset_cam(tgt_cam)
        except ValueError:
            _log.exception('Unable to Reset Cam %s!' % tgt_cam)

        # Update Pass list
        self._rd_set_passes(self._rd_cfg)

        if save:
            try:
                self._rd_cfg.write()
            except:
                _log.exception('Unable to save config after resetting Cam %s!' % tgt_cam)

    def rd_reset_all(self, save=True):
        """
        Calls RadishIO method to reset ENTIRE config
        :param save: Bool, should we re-save the config after doing this
        :return: None
        """
        _log.debug('rd_reset_all')

        self._rd_cfg.reset_all()

        # Update Pass list
        self._rd_set_passes(self._rd_cfg)

        if save:
            try:
                self._rd_cfg.write()
            except:
                _log.exception('Unable to save config after resetting!')

    # QtWidget
    def closeEvent(self, event):
        """
        Called on GUI close, end of program.
        :param event: QtEvent Object
        :return: None
        """
        _log.debug('closeEvent')
        _log.info('Closing RadishUI')

        # noinspection PyBroadException
        try:
            MaxPlus.NotificationManager.Unregister(self._active_camera_callback)
            _log.info('Successfully unregistered _active_camera_callback')
        except:
            pass

        event.accept()


_log.debug('module loaded')
