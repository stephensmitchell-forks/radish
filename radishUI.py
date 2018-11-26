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
import datetime
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
_log.setLevel(logging.INFO)
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

        # Options
        self._rd_opt_lights_chk = self.findChild(QtW.QCheckBox, 'rd_opt_lights_chk')
        self._rd_opt_layers_chk = self.findChild(QtW.QCheckBox, 'rd_opt_layers_chk')
        self._rd_opt_resolution_chk = self.findChild(QtW.QCheckBox, 'rd_opt_resolution_chk')
        self._rd_opt_effects_chk = self.findChild(QtW.QCheckBox, 'rd_opt_effects_chk')
        self._rd_opt_elements_chk = self.findChild(QtW.QCheckBox, 'rd_opt_elements_chk')

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
        self._rd_pass_cb.currentIndexChanged.connect(self._rd_pass_handler)

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

    def _rd_get_custom_passes(self):
        """
        Populates the pass combobox with default values and any custom passes found in the config.
        :return: None
        """
        _log.debug('_rd_get_custom_passes')
        output = []
        passes = self._rd_cfg_root.findall("./*/*[@type='PASS']")

        # Reset the CB
        self._rd_pass_cb.clear()

        self._rd_pass_cb.addItems([self._passes['beauty'],
                                   self._passes['prepass'],
                                   self._passes['custom']])

        for name in passes:
            name = name.attrib['realName']
            if name not in output and name not in self._passes.values():
                output.append(name)

        self._rd_pass_cb.insertItems(2, output)

        _log.info('last_pass = %s' % self._tgt_pass)
        pass_index = self._rd_pass_cb.findText(self._tgt_pass)
        if pass_index >= 0:
            self._rd_pass_cb.setCurrentIndex(pass_index)

    # Info

    def _rd_cfg_setup(self):
        """
        Handles finding and setting up the Radish config file, and assigning the
        _rd_cfg, _rd_cfg_root, _rd_cfg_path params.  Also populates the pass list with custom passes.
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
            # Get any custom passes from the config
            self._rd_get_custom_passes()

        except IOError:
            _log.info('Config not found.  Generating one instead')
            self._rd_cfg = _ETree.ElementTree(_ETree.Element('ROOT'))
            self._rd_cfg_root = self._rd_cfg.getroot()
            _xml_indent(self._rd_cfg_root)
            self._rd_cfg.write(self._rd_cfg_path)
            _log.info('New config saved')
            # Indicate new config file in GUI
            self._rd_config_le.setText(self._rd_cfg_path)
            self._rd_status_label.setText('No config found - Created new file at above address')
            # Set up pass combobox
            self._rd_get_custom_passes()

        except _ETree.ParseError:
            now = datetime.datetime.now()
            timestamp = now.strftime("%y%m%d-%H%M")
            backup_filepath = "%s.%s.BAK" % (self._rd_cfg_path, timestamp)
            _log.error("Config file is corrupt, and can't be read!")
            try:
                # Try to append config with timestamp - if we can't, that's because we backed up within the last minute
                # and it should be safe to just delete current corrupt config.
                os.rename(self._rd_cfg_path, backup_filepath)
                _log.info("Config backed up to %s" % backup_filepath)
            except OSError:
                os.remove(self._rd_cfg_path)
                _log.warning("Unable to back up config - There is already one with this timestamp!")
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
        if self._rd_pass_cb.currentText() == self._passes['custom']:
            self._tgt_pass = self._rd_pass_le.text()
        else:
            self._tgt_pass = self._rd_pass_cb.currentText()
        if _is_ascii(self._tgt_pass) is False:
            _log.error('Pass name must be a valid ASCII string!  Cut it out!')
            self._rd_status_label.setText('Pass name must be a valid ASCII string!  Cut it out!')
            settings_valid = False
        if self._tgt_pass == '':
            self._tgt_pass = 'BLANK'

        # Options
        self._options['lights'] = self._rd_opt_lights_chk.isChecked()
        self._options['layers'] = self._rd_opt_layers_chk.isChecked()
        self._options['resolution'] = self._rd_opt_resolution_chk.isChecked()
        self._options['effects'] = self._rd_opt_effects_chk.isChecked()
        self._options['elements'] = self._rd_opt_elements_chk.isChecked()

        _log.debug('Cam: %s  ---   Pass: %s  ---  Options: %s' % (self._tgt_cam, self._tgt_pass, self._options))

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
            _log.error('Unable to record scene state - _rd_get_settings() failed')
            return False

        # Try to find the camera and pass in the config - If we can't, add them
        cam_el = self._rd_cfg_root.find("./*[@realName='%s']" % self._tgt_cam)
        if cam_el is None:
            _log.info('%s is not in config file - adding it now' % self._tgt_cam)
            cam_el = _ETree.SubElement(self._rd_cfg_root, _xml_tag_cleaner(self._tgt_cam).upper(), {'realName': self._tgt_cam,
                                                                                                    'type': 'CAM'})
            pass_el = None
        else:
            pass_el = cam_el.find("./*[@realName='%s']" % self._tgt_pass)
        if pass_el is not None:
            # If there's already data on this pass, reset it
            self.rd_reset_pass(cam_el, pass_el, save=False)
        pass_el = _ETree.SubElement(cam_el, _xml_tag_cleaner(self._tgt_pass).upper(), {'realName': self._tgt_pass,
                                                                                       'type': 'PASS'})

        # -----------------------
        # Populate pass with data
        # -----------------------

        # ----------
        #   LAYERS
        # ----------
        # Recording Layers is straightforward - Just check the name to make sure it's valid, then save it to the config
        if self._options['layers']:
            layers_el = _ETree.SubElement(pass_el, 'LAYERS')  # Create LAYERS element
            layers_skipped = 0

            for i in range(_rt.layerManager.count):
                layer = _rt.layerManager.getLayer(i)

                # Validate name, skip and print error if it's not
                if _is_ascii(layer.name) is False:
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
        # Recording Lights is a bit more complicated - We have to account for instanced objects and variation in object
        # properties as well as name validation.
        # Get all the scene lights, then store each light, its instances, and relevant properties to save state.
        # Skip if their name is invalid, or if it's already been recorded (usually as an instance)
        if self._options['lights']:
            lights_el = _ETree.SubElement(pass_el, 'LIGHTS')  # Create LIGHTS element
            lights_ignored = []
            lights_skipped = 0

            # Iterate over all lights
            for light in _rt.lights:
                # Skip if it's in the ignore list
                if light.name in lights_ignored:
                    continue

                # Validate name, skip and print error if it's not
                if not _is_ascii(light.name):
                    _log.warning('Skipping %s  -  It contains non-ASCII characters' % _xml_tag_cleaner(light.name))
                    lights_skipped += 1
                    continue

                # Get instances, if there are any
                _log.debug('Checking light %s' % light.name)
                light_instances = _get_instances(light)
                # Check if there was an error, and skip if there was
                if light_instances is False:
                    _log.warning('Skipping %s  -  It contains Quotation or Apostrophe chars!' % light.name)
                    lights_skipped += 1
                    continue

                # Create entry for this light in XML object
                light_el = _ETree.SubElement(lights_el, _xml_tag_cleaner(light.name), {'realName': light.name,
                                                                                       'instanceCount': str(len(light_instances) - 1)})
                # Check if this light has an "on" or "enabled" property - save their state to the XML object if they do
                if _rt.isProperty(light, 'on'):
                    light_el.set('on', str(light.on))
                if _rt.isProperty(light, 'enabled'):
                    light_el.set('enabled', str(light.enabled))

                # Create sub-elements for instances of this light
                # Also add instances to lights_ignored, so we don't redundantly save them
                if len(light_instances) > 1:
                    _log.debug('Found %d instances of %s' % (len(light_instances), light.name))
                    for i in light_instances:
                        if not _is_ascii(i.name):
                            _log.warning('Skipping instance %s  -  It contains non-ASCII characters' % _xml_tag_cleaner(i.name))
                            lights_skipped += 1
                            continue
                        if i.name == light.name:  # The instance list includes the current light - skip it
                            continue
                        _ETree.SubElement(light_el, _xml_tag_cleaner(i.name), {'realName': i.name})
                        lights_ignored.append(i.name)

            if lights_skipped > 0:
                _log.warning('Skipped %d lights' % lights_skipped)

        # --------------
        #   RESOLUTION
        # --------------
        # Just grab the render resolution from Max's global variables
        if self._options['resolution']:
            _log.debug('Render Resolution: %dx%d' % (_rt.renderWidth, _rt.renderHeight))
            _ETree.SubElement(pass_el, 'RESOLUTION', {'width': str(_rt.renderWidth),
                                                      'height': str(_rt.renderHeight)})

        # -----------
        #   EFFECTS
        # -----------
        # Get number of atmospheric effects from a Max global, record their name and state
        if self._options['effects']:
            effects_el = _ETree.SubElement(pass_el, 'EFFECTS')
            effects_skipped = 0

            # Note that index starts at 1, not 0!  Thanks, Autodesk!
            for i in range(1, (_rt.numAtmospherics + 1)):
                effect = _rt.getAtmospheric(i)

                # Validate name, skip and print error if it's not
                if not _is_ascii(effect.name):
                    _log.warning('Skipping %s  -  It contains non-ASCII characters' % _xml_tag_cleaner(effect.name))
                    effects_skipped += 1
                    continue

                _ETree.SubElement(effects_el, _xml_tag_cleaner(effect.name), {'realName': effect.name,
                                                                              'isActive': str(_rt.isActive(effect))})
                _log.debug('Effect %s is %s' % (effect.name, _rt.isActive(effect)))

            if effects_skipped > 0:
                _log.warning('Skipped %d effects' % effects_skipped)

        # ------------
        #   ELEMENTS
        # ------------
        # Get number of render elements from the RenderElementMgr, record their name and state
        # Also log a warning if we detect multiple elements with the same name, as this will cause issues while loading
        # Since we aren't changing settings, we don't have to bother closing the Render Settings dialog
        if self._options['elements']:
            elements_el = _ETree.SubElement(pass_el, 'ELEMENTS')
            elements_list = []
            elements_skipped = 0
            reMgr = _rt.maxOps.getCurRenderElementMgr()

            # Note that index starts at 0 this time.  Thanks, Autodesk!
            for i in range(reMgr.NumRenderElements()):
                element = reMgr.GetRenderElement(i)

                # Validate name, skip and print error if it's not
                if not _is_ascii(element.elementName):
                    _log.warning('Skipping %s  -  It contains non-ASCII characters' % _xml_tag_cleaner(element.elementName))
                    elements_skipped += 1
                    continue

                _ETree.SubElement(elements_el, _xml_tag_cleaner(element.elementName), {'realName': element.elementName,
                                                                                       'enabled': str(element.enabled)})
                _log.debug('Element %s is %s' % (element.elementName, element.enabled))

                if element.elementName in elements_list:
                    _log.warning('There are multiple Render Elements named %s!  '
                                 'They will behave unpredictably when loaded!' % element.elementName)
                else:
                    elements_list.append(element.elementName)

            if elements_skipped > 0:
                _log.warning('Skipped %d elements' % elements_skipped)

        # -----------------------
        # Save the updated config
        # -----------------------
        self._rd_get_custom_passes()
        return self._rd_save_to_disk()

    def rd_load(self):
        """
        Load the config for the current camera pass and apply it to the scene.
        :return: Bool indicating success or failure.
        """
        # TODO: Add ability to restore saved resolution
        # TODO: Add ability to restore state of saved effects
        # TODO: Add ability to restore state of saved render elements
        _log.debug('rd_load')

        # Run _rd_get_settings(), and cancel loading if it returns an error
        if self._rd_get_settings() is False:
            _log.error('Unable to load scene state - _rd_get_settings() failed')
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
        if self._options['layers'] and layers_el is not None:
            layers_skipped = 0

            for tgt_layer in layers_el:
                layer = _rt.layerManager.getLayerFromName(tgt_layer.attrib['realName'])

                # Check if this layer is in the current scene
                if layer is None:
                    _log.warning('Layer %s not found in scene - Skipping' % tgt_layer.attrib['realName'])
                    layers_skipped += 1
                    continue

                layer.on = _xml_get_bool(tgt_layer.attrib['on'])

                _log.debug('Layer %s is Visible: %s' % (tgt_layer.attrib['realName'],
                                                        tgt_layer.attrib['on']))

            _log.info('%d Layers restored' % len(layers_el))
            if layers_skipped > 0:
                _log.warning('%d Layers skipped' % layers_skipped)

        # ----------
        #   LIGHTS
        # ----------
        # TODO: Check if instance count has changed, and manually set each recorded instance if it has.
        if self._options['lights'] and lights_el is not None:
            lights_skipped = 0

            for tgt_light in lights_el:
                light = _rt.getNodeByName(tgt_light.attrib['realName'])

                # Check if this light is in the current scene
                if light is None:
                    _log.warning('Light %s not found in scene - Skipping' % tgt_light.attrib['realName'])
                    lights_skipped += 1
                    continue

                # Lights have a few possible controls - VRay Lights have both.
                # Make sure we only try to apply settings that this light should have.
                if 'on' in tgt_light.attrib:
                    light.on = _xml_get_bool(tgt_light.attrib['on'])
                if 'enabled' in tgt_light.attrib:
                    light.enabled = _xml_get_bool(tgt_light.attrib['enabled'])

            _log.info('%d Unique Lights restored' % len(lights_el))
            if lights_skipped > 0:
                _log.warning('%d Lights skipped' % lights_skipped)

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

            if cam_el is None:
                _log.error('Cam %s not found!' % self._tgt_cam)
                return False

            pass_el = cam_el.find("./*[@realName='%s']" % self._tgt_pass)

            if pass_el is None:
                _log.warning('Pass %s not found!' % self._tgt_pass)
                return False

        _log.info('Resetting %s %s' % (cam_el.attrib['realName'], pass_el.attrib['realName']))
        # Clear the target pass
        cam_el.remove(pass_el)

        if save is True:
            self._rd_get_custom_passes()
            return self._rd_save_to_disk()
        else:
            return True

    def rd_reset_cam(self, cam_el=None, save=True):
        """
        Clears config data for the current camera.  If not passed kwargs, it will get the camera from GUI settings.
        :param cam_el: An ETree element object for the target Camera.
        :param save: Whether or not to re-save the config after running.  Defaults to True.
        :return: Bool indicating success or failure.
        """
        _log.debug('rd_reset_cam')

        # If we weren't passed a target camera, get it
        if cam_el is None:
            # Run _rd_get_settings(), and cancel resetting if it returns an error
            if self._rd_get_settings() is False:
                _log.error('Unable to reset selected camera')
                return False

            cam_el = self._rd_cfg_root.find("./*[@realName='%s']" % self._tgt_cam)

            if cam_el is None:
                _log.warning('Cam %s not found!' % self._tgt_cam)
                return False

        _log.info('Resetting %s' % cam_el.attrib['realName'])
        # Clear the target camera
        self._rd_cfg_root.remove(cam_el)

        if save is True:
            self._rd_get_custom_passes()
            return self._rd_save_to_disk()
        else:
            return True

    def rd_reset_all(self, save=True):
        """
        Entirely clears the loaded config file, except for the root node.
        :param save: Whether or not to re-save the config after running.  Defaults to True.
        :return: Bool indicating success or failure
        """
        _log.debug('rd_reset_all')

        _log.info('Resetting entire config...')
        # Remove all children of _rd_cfg_root
        for child in list(self._rd_cfg_root):
            _log.debug('Removing %s data' % child.attrib['realName'])
            self._rd_cfg_root.remove(child)

        if save is True:
            self._rd_get_custom_passes()
            return self._rd_save_to_disk()
        else:
            return True

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
