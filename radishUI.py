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
import xml.etree.ElementTree as _ETree
import logging
import sys
import os

# For 3ds Max - Temporarily add this file's directory to PATH
sys.path.append(os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))))

# Local modules
import radish_utilities as util

_rt = pymxs.runtime
_radish_log_handler = util.CustomHandler()

_get_instances = util.get_instances

_is_ascii = util.is_ascii
_xml_tag_cleaner = util.xml_tag_cleaner
_xml_get_bool = util.xml_get_bool
_xml_indent = util.xml_indent


# Destroys instances of the dialog before recreating it
# This has to go before re-declaration of the ui variable
# noinspection PyBroadException
try:
    # noinspection PyUnboundLocalVariable
    _log.info('Closing old instances of UI...')
    # noinspection PyUnboundLocalVariable
    ui.close()
except:
    pass


# --------------------
#     Logger setup
# --------------------

_log = logging.getLogger("Radish")
_log.setLevel(logging.DEBUG)
# Clean up old handlers before re-initializing
# Important, as the user may re-launch this script without re-launching the parent program
# if _log.handlers:
#     _log.warning('Old Radish logger detected: resetting')
#     for handler in list(_log.handlers):
#         _log.removeHandler(handler)
# Add custom handler
_log.addHandler(_radish_log_handler)

_log.info('Radish Logger active')


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
        # Init QtW.QDialog
        super(RadishUI, self).__init__(parent)
        # Set up callback for camera detection
        self._active_camera_callback = MaxPlus.NotificationManager.Register(MaxPlus.NotificationCodes.ViewportChange,
                                                                            self._active_camera_handler)

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

        # Parameters used for navigating the XML config
        self._tgt_project = 'TEST'
        self._tgt_cam = None
        self._tgt_pass = None

        # Stores indices for pass combobox
        self._passes = {'beauty': 0, 'prepass': 1, 'custom': 2}

        # Stores current active viewport
        self._active_cam = self._rt.getActiveCamera()

        # Sets config file path and reads xml file.  Generate one if it doesn't exist.
        # This function also sets the _rd_cfg, _rd_cfg_root, and _rd_cfg_path params
        self._rd_cfg_setup()

        # ---------------------------------------------------
        #               End of RadishUI Init
        # ---------------------------------------------------

        _log.info('RadishUI Initialized')

    # ---------------------------------------------------
    #                  Private Methods
    # ---------------------------------------------------

    # Cams

    def _rd_cam_override(self):
        """
        Check the state of the override checkbox, and toggle the override combobox accordingly.
        Also re-build the list of cameras when it's activated.
        :return:
        """
        _log.debug('_rd_cam_override')
        if self._rd_cam_chk.isChecked():
            self._rd_cam_le.setEnabled(False)
            self._rd_cam_cb.setEnabled(True)

            tmp_cams = []

            for c in _rt.cameras:
                if len(_rt.getPropNames(c)) == 0:
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

    def _rd_pass_override(self):
        """
        Check the state of the pass combobox, if custom is selected unlock the input field for it.
        :return: None
        """
        _log.debug('_rd_pass_override')
        if self._rd_pass_cb.currentIndex() == self._passes['custom']:
            self._rd_pass_le.setEnabled(True)
        else:
            self._rd_pass_le.setEnabled(False)

    # Info

    def _rd_cfg_setup(self):
        """
        Handles finding and setting up the Radish config file, and assigning the
        _rd_cfg, _rd_cfg_root, _rd_cfg_path params.
        :return: None
        """
        _log.debug('_rd_cfg_setup')

        self._rd_cfg_path = os.path.dirname(__file__) + '\\radishConfig.xml'
        # noinspection PyBroadException
        try:
            _log.info('Trying to read config file %s...' % self._rd_cfg_path)
            self._rd_cfg = _ETree.parse(self._rd_cfg_path)
            self._rd_cfg_root = self._rd_cfg.getroot()
            # Display config file path in GUI
            self._rd_config_le.setText(self._rd_cfg_path)
            self._rd_status_label.setText('Config file found')
        except IOError:
            _log.info('Config not found.  Generating one instead')
            self._rd_cfg = _ETree.ElementTree(_ETree.Element('root'))
            self._rd_cfg_root = self._rd_cfg.getroot()
            _xml_indent(self._rd_cfg_root)
            self._rd_cfg.write(self._rd_cfg_path)
            _log.info('New config saved')
            # Indicate new config file in GUI
            self._rd_config_le.setText(self._rd_cfg_path)
            self._rd_status_label.setText('No config found - Created new file at above address')
        except _ETree.ParseError:
            _log.error("Config file is corrupt, and can't be read!  Backing it up and trying again...")
            self._rd_status_label.setText("Config file is corrupt, and can't be read!  Backing it up...")
            try:
                # First remove old .BAK, if it exists
                os.remove('%s.BAK' % self._rd_cfg_path)
            except OSError:
                pass
            os.rename(self._rd_cfg_path, '%s.BAK' % self._rd_cfg_path)
            self._rd_cfg_setup()
        except:
            _log.error('Unknown error while reading config file')

    # Misc internal logic
    def _rd_get_settings(self):
        """
        Get all settings from dialog window and update class properties.
        :return: None
        """
        _log.debug('_rd_get_settings')

        settings_valid = True

        # Cam
        if self._rd_cam_chk.isChecked():
            self._tgt_cam = self._rd_cam_cb.currentText()
        else:
            self._tgt_cam = self._rd_cam_le.text()
        if _is_ascii(self._tgt_cam) is False:
            _log.error('Camera name must be a valid ASCII string!  Clean your shit up!')
            self._rd_status_label.setText('Camera name must be a valid ASCII string!  Clean your shit up!')
            settings_valid = False
        if self._tgt_cam == '':
            self._tgt_cam = 'BLANK'

        # Pass
        if self._rd_pass_cb.currentIndex() == self._passes['custom']:
            self._tgt_pass = self._rd_pass_le.text().upper()
        else:
            self._tgt_pass = self._rd_pass_cb.currentText().upper()
        if _is_ascii(self._tgt_pass) is False:
            _log.error('Pass name must be a valid ASCII string!  Cut it out!')
            self._rd_status_label.setText('Pass name must be a valid ASCII string!  Cut it out!')
            settings_valid = False
        if self._tgt_pass == '':
            self._tgt_pass = 'BLANK'

        _log.debug('Cam: %s  ---   Pass: %s' % (self._tgt_cam, self._tgt_pass))

        return settings_valid

    def _rd_save_to_disk(self):
        """
        Handles writing the config file to disk.
        :return: Bool indicating success or failure.
        """
        # XML Cleanup
        _xml_indent(self._rd_cfg_root)

        # Save to disk
        # noinspection PyBroadException
        try:
            self._rd_cfg.write(self._rd_cfg_path)
        except IOError:
            _log.error('Unable to save config to disk')
            self._rd_status_label.setText('Unable to save config to disk')
            return False
        except:
            _log.error('Unknown error while writing config file')
            return False

        return True

    # ---------------------------------------------------
    #                  Public Methods
    # ---------------------------------------------------

    # Save / Load
    def rd_save(self):
        """
        Save the current scene state to the config file.  If there's already an entry for this camera pass,
        clear it first.  If there isn't, create one.
        :return: Bool indicating success or failure.
        """
        _log.debug('rd_save')

        # Run _rd_get_settings(), and cancel saving if it returns an error
        if self._rd_get_settings() is False:
            _log.error('Unable to record scene state')
            return False

        # Try to find the camera and pass in the config - If we can't, add them
        cam_el = self._rd_cfg_root.find("./*[@realName='%s']" % self._tgt_cam)
        if cam_el is None:
            _log.info('%s is not in config file - adding it now' % self._tgt_cam)
            cam_el = _ETree.SubElement(self._rd_cfg_root, _xml_tag_cleaner(self._tgt_cam), {'realName': self._tgt_cam})
            pass_el = None
        else:
            pass_el = cam_el.find("./*[@realName='%s']" % self._tgt_pass)
        if pass_el is None:
            pass_el = _ETree.SubElement(cam_el, _xml_tag_cleaner(self._tgt_pass), {'realName': self._tgt_pass})

        # Clear the target pass
        self.rd_reset_pass(cam_el, pass_el, save=False)

        # -----------------------
        # Populate pass with data
        # -----------------------

        # ----------
        #   LAYERS
        # ----------
        layers_el = _ETree.SubElement(pass_el, 'LAYERS')  # Create LAYERS element
        layers_skipped = 0

        for i in range(_rt.layerManager.count):
            layer = _rt.layerManager.getLayer(i)

            # Print error message and skip if Layer name is invalid
            if _is_ascii(layer.name) is False:
                try:
                    _log.warning('Skipping %s  -  It contains non-ASCII characters' % layer.name)
                except UnicodeEncodeError:
                    _log.warning('Skipping %s  -  It contains non-ASCII characters' % _xml_tag_cleaner(layer.name))
                layers_skipped += 1
                continue

            _ETree.SubElement(layers_el, _xml_tag_cleaner(layer.name), {'realName': layer.name,
                                                                        'on': str(layer.on)})
            _log.debug('%s is %s' % (layer.name, layer.on))

        if layers_skipped > 0:
            _log.warning('Skipped %d layers' % layers_skipped)

        # ----------
        #   LIGHTS
        # ----------
        lights_el = _ETree.SubElement(pass_el, 'LIGHTS')  # Create LIGHTS element
        lights_ignored = []
        lights_skipped = 0

        # Iterate over all lights, print their properties
        for light in _rt.lights:
            # Skip this obj if it's in the ignore list
            if light.name in lights_ignored:
                continue

            # Print error message if Light name is invalid
            if not _is_ascii(light.name):
                try:
                    _log.warning('Skipping %s  -  It contains non-ASCII characters' % light.name)
                except UnicodeEncodeError:
                    _log.warning('Skipping %s  -  It contains non-ASCII characters' % _xml_tag_cleaner(light.name))
                lights_skipped += 1
                continue

            # Print instances, if there are any
            tgt_instances = _get_instances(light)
            if len(tgt_instances) > 1:
                _log.debug('Found %d instances of %s' % (len(tgt_instances), light.name))
                for i in tgt_instances:
                    lights_ignored.append(i.name)

            # Create entry for this light in XML object
            light_el = _ETree.SubElement(lights_el, _xml_tag_cleaner(light.name), {'realName': light.name,
                                                                                   'instanceCount': str(len(tgt_instances) - 1)})
            # Check if this light has an "on" or "enabled" property - save their state to the XML object if they do
            if _rt.isProperty(light, 'on'):
                light_el.set('on', str(light.on))
            if _rt.isProperty(light, 'enabled'):
                light_el.set('enabled', str(light.enabled))

        if lights_skipped > 0:
            _log.warning('Skipped %d lights' % lights_skipped)

        # -----------------------
        # Save the updated config
        # -----------------------
        return self._rd_save_to_disk()

    def rd_load(self):
        """
        Load the config for the current camera pass and apply it to the scene.
        :return: Bool indicating success or failure.
        """
        _log.debug('rd_load')

        # Run _rd_get_settings(), and cancel loading if it returns an error
        if self._rd_get_settings() is False:
            _log.error('Unable to load scene state')
            return False

        # Try to find the camera and pass in the config - If we can't, error out
        cam_el = self._rd_cfg_root.find("./*[@realName='%s']" % self._tgt_cam)
        if cam_el is None:
            _log.error('Camera not found in config!')
            return False
        else:
            pass_el = cam_el.find("./*[@realName='%s']" % self._tgt_pass)
        if pass_el is None:
            _log.error('Pass not found in config!')
            return False

        layers_el = pass_el.find('LAYERS')
        lights_el = pass_el.find('LIGHTS')

        # -----------------------
        #   Restore pass state
        # -----------------------

        # ----------
        #   LAYERS
        # ----------
        for layer in layers_el:
            _log.debug('Layer %s is Visible: %s' % (layer.attrib['realName'],
                                                    layer.attrib['on']))
            _rt.layerManager.getLayerFromName(layer.attrib['realName']).on = _xml_get_bool(layer.attrib['on'])

        _log.info('%d Layers restored' % len(layers_el))

        # ----------
        #   LIGHTS
        # ----------
        for light in lights_el:
            _log.debug('Light %s (and %s instances) is On/Enabled: %s/%s' % (light.attrib['realName'],
                                                                             light.attrib['instanceCount'],
                                                                             light.attrib['on'],
                                                                             light.attrib['enabled']))
            light_obj = _rt.getNodeByName(light.attrib['realName'])
            if light.attrib['on'] is not None:
                light_obj.on = _xml_get_bool(light.attrib['on'])
            if light.attrib['enabled'] is not None:
                light_obj.enabled = _xml_get_bool(light.attrib['enabled'])

        _log.info('%d Unique Lights restored' % len(lights_el))
        return True

    # Resets
    def rd_reset_pass(self, cam_el=None, pass_el=None, save=True):
        """
        Clears config data for the current camera pass.  If not passed kwargs, it will get the target pass from
        GUI settings.
        :param cam_el: An ETree element object for the target Camera.
        :param pass_el: An ETree element object for the target Pass.
        :param save: Whether or not to re-save the config after running.  Defaults to True.
        :return: Bool indicating success or failure.
        """
        _log.debug('rd_reset_pass')

        # If we weren't passed a target camera and pass element, get them
        if cam_el is None or pass_el is None:
            # Run _rd_get_settings(), and cancel resetting if it returns an error
            if self._rd_get_settings() is False:
                _log.error('Unable to reset selected pass')
                return False

            cam_el = self._rd_cfg_root.find("./*[@realName='%s']" % self._tgt_cam)
            pass_el = cam_el.find("./*[@realName='%s']" % self._tgt_pass)

            if pass_el is None:
                _log.warning('Pass %s not found!' % self._tgt_pass)
                return False

        _log.info('Resetting %s %s' % (cam_el.attrib['realName'], pass_el.attrib['realName']))
        # Clear the target pass
        for child_el in list(pass_el):
            pass_el.remove(child_el)

        if save is True:
            return self._rd_save_to_disk()
        else:
            return True

    def rd_reset_cam(self):
        _log.debug('rd_reset_cam')

    def rd_reset_all(self):
        _log.debug('rd_reset_all')

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
            _log.warning('Could not unregister _active_camera_callback')

        # noinspection PyBroadException
        try:
            _log.info('Shutting down Radish logger...')
            # Shut down handlers
            logging.shutdown()
            # Remove handlers
            for handler in list(_log.handlers):
                _log.removeHandler(handler)
        except:
            _log.warning('Could not shutdown Radish logger')

        event.accept()


# --------------------
#    Dialog Setup
# --------------------

# Path to UI file
uif = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))) + "\\radish_standalone.ui"

app = MaxPlus.GetQMaxMainWindow()
ui = RadishUI(uif, _rt, app)

# Punch it
ui.show()
_log.info('GUI created')
