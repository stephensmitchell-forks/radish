# --------------------
#       Modules
# --------------------

# Logging
import logging

_log = logging.getLogger('Radish.IO')
_log.info('Logger %s Active' % _log.name)

# Misc
import xml.etree.ElementTree as _ETree
import datetime
import sys
import os

# Utilities
import radish_utilities as util
_xml_get_bool = util.xml_get_bool
_xml_tag_cleaner = util.xml_tag_cleaner
_xml_indent = util.xml_indent
_get_instances = util.get_instances
_is_ascii = util.is_ascii

class RadishIO(object):
    """
    A class to store data on scene states, as well as handle reading and writing those states to disk.
    By default it will initialize empty, but if it's passed a string keyword for a supported filetype it will try
    to load and parse that file.
    Supported keywords: XML
    """
    def __init__(self, runtime, config_type=None):
        """
        :param runtime: The pymxs runtime.
        :param config_type: Keyword, determines how to load and save from disk.
        """

        # ---------------
        #   Variables
        # ---------------
        self._rt = runtime

        # ---------------
        #   Class Attrs
        # ---------------
        self.cams = {}

        # ---------------
        #   Load Config
        # ---------------
        # If we got a valid config_type, then set up shorthand methods .read and .write to parse the config.
        # Also immediately load the config.
        if config_type is not None:
            if config_type == 'XML':
                self.read = self.read_config_xml
                self.write = self.write_config_xml
                self.read()
            else:
                _log.warning('Invalid config type "%s" passed to RadishIO - Supported types are: XML' % config_type)

        # End of Init
        # ---------------

    # -------------------
    #      Builtins
    # -------------------
    def __repr__(self):
        output = 'RadishIO Dump'
        output += '\r\r .cams {'
        for k, v in self.cams.items():
            output += '\r|\t %s' % k
            output += repr(v)
        output += '\r }'

        return output

    # -------------------
    #   Public Methods
    # -------------------

    def read_config_xml(self):
        """
        This finds and loads a XML config into RadishIO's memory.  If the file cannot be read, it will be backed up and
        RadishIO will be set up with a blank memory.
        :return: None
        """
        cfg_path = os.path.dirname(__file__) + '\\radishConfig.xml'
        try:
            _log.info('Trying to read config file %s' % cfg_path)
            cfg = _ETree.parse(cfg_path)
            cfg_root = cfg.getroot()

        except IOError:
            _log.warning('Config file not found - Starting with a blank slate')
            # Just to be safe, re-initialize cams as a blank dictionary.
            self.cams = {}
            return

        except _ETree.ParseError:
            _log.error('Config file is corrupt, and cannot be read!')
            now = datetime.datetime.now()
            timestamp = now.strftime('%y%m%d-%H%M')
            backup_filepath = '%s.%s.BAK' % (cfg_path, timestamp)
            try:
                # Try to append config with timestamp - if we can't, that's because we backed up within the last minute
                # and it should be safe to just delete current corrupt config.
                os.rename(cfg_path, backup_filepath)
                _log.info('Config backed up to %s' % backup_filepath)
            except OSError:
                _log.warning('Unable to back up config - A file already exists with this timestamp!')
                os.remove(cfg_path)

            # Again, just to be safe re-initialize cams as a blank dictionary
            self.cams = {}
            return

        except:
            _log.exception('Unknown error while reading config file - Starting with a blank slate')
            # Last time, I promise
            self.cams = {}
            return

        # If we made it here, then we've successfully loaded our XML config.  Time to parse it into RadishIO's memory.
        # Get all camera elements, then iterate over them to get their passes
        _log.info('Config loaded - Parsing...')
        try:
            for tgt_cam in cfg_root.findall("./*[@type='CAM']"):
                cam_name = tgt_cam.attrib['realName']
                _log.debug('Parsing Camera %s' % cam_name)

                # Get all passes under this camera, then iterate over them to populate pass info
                for tgt_pass in tgt_cam.findall("./*[@type='PASS']"):
                    pass_name = tgt_pass.attrib['realName']
                    rad_pass = self.set_pass(cam_name, pass_name)
                    _log.debug('Parsing Pass %s for Cam %s' % (pass_name, cam_name))

                    # Get Layers
                    _log.debug('Parsing Layers...')
                    for tgt_layer in tgt_pass.findall('./LAYERS/*'):
                        # Get attributes of this Layer
                        tgt_name = None
                        tgt_on = None
                        tgt_misc = {}
                        for k, v in tgt_layer.attrib.items():
                            if k == 'realName':
                                tgt_name = v
                            elif k == 'on':
                                tgt_on = _xml_get_bool(v)
                            else:
                                tgt_misc[k] = v

                        # Make a new RadishLayer
                        rad_pass.layers[tgt_name] = RadishLayer(name=tgt_name,
                                                                on=tgt_on,
                                                                misc=tgt_misc)

                    # Get Lights
                    _log.debug('Parsing Lights...')
                    for tgt_light in tgt_pass.findall('./LIGHTS/*'):
                        # Get the attributes of this Light
                        tgt_name = None
                        tgt_on = None
                        tgt_enabled = None
                        tgt_instances = []
                        tgt_misc = {}
                        for k, v in tgt_light.attrib.items():
                            if k == 'realName':
                                tgt_name = v
                            elif k == 'on':
                                tgt_on = _xml_get_bool(v)
                            elif k == 'enabled':
                                tgt_enabled = _xml_get_bool(v)
                            else:
                                tgt_misc[k] = v
                        for child in tgt_light.findall("./*"):
                            tgt_instances.append(child.attrib['realName'])

                        # Make a new RadishLight
                        rad_pass.lights[tgt_name] = RadishLight(name=tgt_name,
                                                                enabled=tgt_enabled,
                                                                on=tgt_on,
                                                                instances=tgt_instances,
                                                                misc=tgt_misc)

                    # Get Effects
                    _log.debug('Parsing Effects...')
                    for tgt_effect in tgt_pass.findall('./EFFECTS/*'):
                        # Get the attributes of this Effect
                        tgt_name = None
                        tgt_active = None
                        tgt_misc = {}
                        for k, v in tgt_effect.attrib.items():
                            if k == 'realName':
                                tgt_name = v
                            elif k == 'isActive':
                                tgt_active = _xml_get_bool(v)
                            else:
                                tgt_misc[k] = v

                        # Make a new RadishEffect
                        rad_pass.effects[tgt_name] = RadishEffect(name=tgt_name,
                                                                  active=tgt_active,
                                                                  misc=tgt_misc)

                    # Get Elements
                    _log.debug('Parsing Elements...')
                    for tgt_element in tgt_pass.findall('./ELEMENTS/*'):
                        # Get the attributes for this Element
                        tgt_name = None
                        tgt_enabled = None
                        tgt_misc = {}
                        for k, v in tgt_element.attrib.items():
                            if k == 'realName':
                                tgt_name = v
                            elif k == 'enabled':
                                tgt_enabled = v
                            else:
                                tgt_misc[k] = v

                        # Make a new RadishElement
                        rad_pass.elements[tgt_name] = RadishElement(name=tgt_name,
                                                                    enabled=tgt_enabled,
                                                                    misc=tgt_misc)
        except:
            _log.exception('Error parsing config %s!')
            # Reset data in case it's corrupt / partially loaded
            self.cams = {}


        _log.info('Config file successfully parsed')
        # DEBUG - Dump resulting RadishIO memory to log
        # _log.info(repr(self))


    def write_config_xml(self):
        # TODO: Implement writing of .misc{} attributes
        """
        This will parse RadishIO's memory into an XML ETree object and then write it to disk.
        :return: None
        """
        _log.info('Writing XML Config')
        # Set up empty XML ETree
        cfg_tree = _ETree.ElementTree(_ETree.Element('ROOT'))
        cfg_root = cfg_tree.getroot()

        # Iterate over cameras
        for src_cam in self.cams.itervalues():
            _log.debug('Parsing Camera %s' % src_cam.name)
            cfg_cam = _ETree.SubElement(cfg_root, _xml_tag_cleaner(src_cam.name.upper()), {'realName':src_cam.name,
                                                                                           'type':src_cam.type})
            # Iterate over this camera's passes
            for src_pass in src_cam.passes.itervalues():
                _log.debug('Parsing Pass %s for Cam %s' % (src_pass.name, src_cam.name))
                cfg_pass = _ETree.SubElement(cfg_cam, _xml_tag_cleaner(src_pass.name.upper()), {'realName':src_pass.name,
                                                                                                'type':src_pass.type})
                # Iterate over this passes' settings, adding them to the XML Tree if they contain data

                # Layers
                _log.debug('Layers...')
                if len(src_pass.layers) > 0:
                    cfg_layers = _ETree.SubElement(cfg_pass, 'LAYERS')
                    for src_layer in src_pass.layers.itervalues():
                        _ETree.SubElement(cfg_layers, _xml_tag_cleaner(src_layer.name), {'realName':src_layer.name,
                                                                                         'on':str(src_layer.on)})

                # Lights
                _log.debug('Lights...')
                if len(src_pass.lights) > 0:
                    cfg_lights = _ETree.SubElement(cfg_pass, 'LIGHTS')
                    for src_light in src_pass.lights.itervalues():
                        # Lights have variable attributes, so go over them one-by-one and build a dict of valid ones
                        light_attrs = {'realName':src_light.name,
                                       'instanceCount':str(len(src_light.instances))}
                        if src_light.enabled is not None:
                            light_attrs['enabled'] = str(src_light.enabled)
                        if src_light.on is not None:
                            light_attrs['on'] = str(src_light.on)
                        cfg_light = _ETree.SubElement(cfg_lights, _xml_tag_cleaner(src_light.name), light_attrs)

                        # If there are instances of this light, also add them as children
                        for instance in src_light.instances:
                            _ETree.SubElement(cfg_light, _xml_tag_cleaner(instance), {'realName':instance})

                # Effects
                _log.debug('Effects...')
                if len(src_pass.effects) > 0:
                    cfg_effects = _ETree.SubElement(cfg_pass, 'EFFECTS')
                    for src_effect in src_pass.effects.itervalues():
                        _ETree.SubElement(cfg_effects, _xml_tag_cleaner(src_effect.name), {'realName':src_effect.name,
                                                                                           'isActive':str(src_effect.active)})

                # Elements
                _log.debug('Elements...')
                if len(src_pass.elements) > 0:
                    cfg_elements = _ETree.SubElement(cfg_pass, 'ELEMENTS')
                    for src_element in src_pass.elements.itervalues():
                        _ETree.SubElement(cfg_elements, _xml_tag_cleaner(src_element.name), {'realName':src_element.name,
                                                                                             'enabled':str(src_element.enabled)})


        # XML Cleanup
        _xml_indent(cfg_root)

        # Save to disk
        cfg_path = os.path.dirname(__file__) + '\\radishConfig.xml'
        cfg_tmp = cfg_path.replace('radishConfig.xml', 'radishConfig.tmp')
        try:
            _log.debug('Writing to temp file %s...' % cfg_tmp)
            cfg_tree.write(cfg_tmp)
        except IOError:
            _log.exception('Unable to write config to disk!')
            return
        except:
            _log.exception('Unknown error while saving config to disk!')
            return

        # Replace .xml file with the new .tmp
        try:
            _log.debug('Replacing working config %s...' % cfg_path)
            os.remove(cfg_path)
            os.rename(cfg_tmp,cfg_path)
        except IOError:
            _log.exception('Unable to copy temp config file from %s to %s' % (cfg_tmp, cfg_path))
            return
        except:
            _log.exception('Unknown error while copying temp config file from %s to %s!' % (cfg_tmp, cfg_path))
            return

        _log.info('XML Config saved to %s' % cfg_path)


    def save_state(self, cam_name, pass_name, options):
        """
        Save the current scene state to RadishIO memory
        :param cam_name: String, name of camera
        :param pass_name: String, name of pass
        :param options: Dict, options from RadishUI
        :return: None
        """
        _log.debug('save_state')

        # Set up indicated pass, or get the pass if it's already in memory.
        # Note that the pass will not be cleared, so any data that is not overwritten will remain.
        tgt_pass = self.set_pass(cam_name, pass_name)
        _log.info('Saving Cam: %s  Pass: %s...' % (cam_name, pass_name))

        # -----------------------
        # Populate pass with data
        # -----------------------

        # ----------
        #   LAYERS
        # ----------
        # Recording Layers is straightforward - Just check the name to make sure it's valid, then add it to the pass
        if options['layers']:
            layers = {}
            layers_skipped = 0

            for i in range(self._rt.layerManager.count):
                layer = self._rt.layerManager.getLayer(i)

                layer_name = layer.name
                layer_on = layer.on

                # Validate name, skip and print error if it's not
                if _is_ascii(layer_name) is False:
                    _log.warning('Skipping %s  -  It contains non-ASCII characters' % _xml_tag_cleaner(layer_name))
                    layers_skipped += 1
                    continue

                layers[layer_name] = RadishLayer(layer_name,
                                                 layer_on)

                _log.debug('Recorded layer %s' % layer_name)

            if layers_skipped > 0:
                _log.warning('Skipped %d layers' % layers_skipped)

            tgt_pass.layers = layers
            _log.info('Saved Layers...')

        # ----------
        #   LIGHTS
        # ----------
        # Recording Lights is a bit more complicated - We have to account for instanced objects and variation in object
        # properties as well as name validation.
        # Get all the scene lights, then store each light, its instances, and relevant properties.
        # Skip if their name is invalid, or if they've already been recorded (as an instance)
        if options['lights']:
            lights = {}
            lights_ignored = []
            lights_skipped = 0

            # Iterate over all lights
            for light in self._rt.lights:

                light_name = light.name
                # Set blank properties, to be set later if found
                light_on = None
                light_enabled = None
                light_instances = []

                # Skip if it's in the ignore list
                if light_name in lights_ignored:
                    continue

                # Validate name, skip and print error if it's not
                if not _is_ascii(light_name):
                    _log.warning('Skipping %s  -  It contains non-ASCII characters' % _xml_tag_cleaner(light_name))
                    lights_skipped += 1
                    continue

                # Try to get instances, log error and skip if we can't.
                try:
                    light_instances_objs = _get_instances(light)
                    for i in light_instances_objs:
                        i_name = i.name
                        if not _is_ascii(i_name):
                            _log.warning('Skipping instance %s  -  It contains non-ASCII characters' % _xml_tag_cleaner(i_name))
                            lights_skipped += 1
                            continue
                        if i_name == light_name:  # The instance list includes the current light - skip it
                            continue
                        # Valid instance, add its name to our instance list and ignore list
                        light_instances.append(i_name)
                        lights_ignored.append(i_name)
                except ValueError:
                    _log.warning('Skipping %s  -  It contains Quotation or Apostrophe chars!' % light_name)
                    lights_skipped += 1
                    continue

                # Check if this light has an "on" or "enabled" property - save their state if they do
                if self._rt.isProperty(light, 'on'):
                    light_on = light.on
                if self._rt.isProperty(light, 'enabled'):
                    light_enabled = light.enabled

                # Save this light
                lights[light_name] = RadishLight(light_name,
                                                 light_enabled,
                                                 light_on,
                                                 light_instances)

                _log.debug('Recorded light %s' % light_name)

            if lights_skipped > 0:
                _log.warning('Skipped %d lights' % lights_skipped)

            tgt_pass.lights = lights
            _log.info('Saved Lights...')

        # -----------
        #   EFFECTS
        # -----------
        # Get number of atmospheric effects from a Max global, record their name and state
        # Also log a warning if we detect multiple elements with the same name, as this will cause issues while loading
        if options['effects']:
            effects = {}
            effects_list = []
            effects_skipped = 0

            # Note that index starts at 1, not 0!  Thanks, Autodesk!
            for i in range(1, (self._rt.numAtmospherics + 1)):
                effect = self._rt.getAtmospheric(i)

                effect_name = effect.name
                effect_active = self._rt.isActive(effect)

                # Validate name, skip and print error if it's not
                if not _is_ascii(effect_name):
                    _log.warning('Skipping %s  -  It contains non-ASCII characters' % _xml_tag_cleaner(effect_name))
                    effects_skipped += 1
                    continue

                # Save this effect
                effects[effect_name] = RadishEffect(effect_name,
                                                    effect_active)
                _log.debug('Recorded Effect %s' % effect_name)

                # Check for duplicate effect names
                if effect_name in effects_list:
                    _log.warning('There are multiple Atmospheric Effects named %s!  '
                                 'They will behave unpredictably when loaded!' % effect_name)
                else:
                    effects_list.append(effect_name)

            if effects_skipped > 0:
                _log.warning('Skipped %d effects' % effects_skipped)

            tgt_pass.effects = effects
            _log.info('Saved Effects...')

        # ------------
        #   ELEMENTS
        # ------------
        # Get number of render elements from the RenderElementMgr, record their name and state
        # Also log a warning if we detect multiple elements with the same name, as this will cause issues while loading
        # Since we aren't changing settings, we don't have to bother closing the Render Settings dialog
        if options['elements']:
            elements = {}
            elements_list = []
            elements_skipped = 0
            reMgr = self._rt.maxOps.getCurRenderElementMgr()

            # Note that index starts at 0 this time.  Thanks, Autodesk!
            for i in range(reMgr.NumRenderElements()):
                element = reMgr.GetRenderElement(i)

                element_name = element.elementName
                element_enabled = element.enabled

                # Validate name, skip and print error if it's not
                if not _is_ascii(element.elementName):
                    _log.warning('Skipping %s  -  It contains non-ASCII characters' % _xml_tag_cleaner(element_name))
                    elements_skipped += 1
                    continue

                # Save this element
                elements[element_name] = RadishElement(element_name,
                                                       element_enabled)
                _log.debug('Recorded Element %s' % element_name)

                # Check for duplicate element names
                if element_name in elements_list:
                    _log.warning('There are multiple Render Elements named %s!  '
                                 'They will behave unpredictably when loaded!' % element.elementName)
                else:
                    elements_list.append(element_name)

            if elements_skipped > 0:
                _log.warning('Skipped %d elements' % elements_skipped)

            tgt_pass.elements = elements
            _log.info('Saved Elements...')

        _log.info('Saved Cam: %s  Pass: %s' % (cam_name, pass_name))


    def load_state(self, cam_name, pass_name, options):
        """
        Load the requested state from RadishIO's memory.
        :param cam_name: String, name of camera.
        :param pass_name: String, name of pass.
        :param options: Dict, options from RadishUI.
        :return: None.
        """
        _log.debug('load_state')

        _log.info('Loading Cam:%s  Pass:%s' % (cam_name, pass_name))
        try:
            tgt_pass = self.get_pass(cam_name, pass_name)
        except ValueError:
            _log.exception('Unable to load state!')
            return

        # ----------
        #   LAYERS
        # ----------
        if options['layers'] and tgt_pass.layers:
            layers_skipped = 0

            for layer in tgt_pass.layers.itervalues():
                layer_name = layer.name
                layer_on = layer.on

                # Check if this layer is in the current scene
                tgt_layer = self._rt.layerManager.getLayerFromName(layer_name)
                if tgt_layer is None:
                    _log.warning('Layer %s not found in scene - Skipping' % layer_name)
                    layers_skipped += 1
                    continue

                tgt_layer.on = layer_on

                _log.debug('Layer %s is Visible: %s' % (layer_name,
                                                        layer_on))

            _log.info('%d Layers restored' % (len(tgt_pass.layers) - layers_skipped))
            if layers_skipped > 0:
                _log.warning('%d Layers skipped' % layers_skipped)

        # ----------
        #   LIGHTS
        # ----------
        # TODO: Check if instance count has changed, and manually set each recorded instance if it has.
        if options['lights'] and tgt_pass.lights:
            lights_skipped = 0

            for light in tgt_pass.lights.itervalues():
                light_name = light.name
                light_on = light.on
                light_enabled = light.enabled
                light_instances = light.instances

                # Check if this light is in the current scene
                tgt_light = self._rt.getNodeByName(light_name)
                if tgt_light is None:
                    _log.warning('Light %s not found in scene - Skipping' % light_name)
                    lights_skipped += 1
                    continue

                # Lights have a few possible controls - VRay Lights have both.
                # Make sure we only try to apply settings that this light should have.
                if light_on is not None:
                    tgt_light.on = light_on
                if light_enabled is not None:
                    tgt_light.enabled = light_enabled

            _log.info('%d Unique Lights restored' % (len(tgt_pass.lights) - lights_skipped))
            if lights_skipped > 0:
                _log.warning('%d Lights skipped' % lights_skipped)


    def set_cam(self, cam_name):
        if cam_name not in self.cams:
            _log.debug('Cam %s not found, creating new entry...' % cam_name)
            self.cams[cam_name] = RadishCam(cam_name)

        return self.cams[cam_name]

    def set_pass(self, cam_name, pass_name):
        """
        Shorthand to return the given pass for the given camera, creating these if necessary.
        """
        cam = self.set_cam(cam_name)
        if pass_name not in cam.passes:
            _log.debug('Pass %s in Cam %s not found, creating new entry...' % (pass_name, cam_name))
            cam.passes[pass_name] = RadishPass(pass_name)

        return cam.passes[pass_name]

    def get_pass(self, cam_name, pass_name):
        """
        Shorthand to return the given pass for the given camera.  Raises a ValueError if it's not found.
        """
        if cam_name in self.cams:
            if pass_name in self.cams[cam_name].passes:
                _log.debug('Got Pass %s in Cam %s' % (pass_name, cam_name))
                return self.cams[cam_name].passes[pass_name]

        raise ValueError('Could not find Cam %s  Pass %s' % (cam_name, pass_name))

    def get_all_passes(self):
        """
        Gets all passes from RadishIO's memory and return them as a list, with no duplicates.
        :return: List containing one of every pass in memory.
        """
        passes = []
        for c in self.cams.itervalues():
            for p in c.passes.itervalues():
                if p.name in passes:
                    continue
                else:
                    passes.append(p.name)
                    _log.debug('Found Pass %s' % p.name)

        return passes

    def reset_pass(self, cam_name, pass_name):
        """
        Shorthand to delete the specified pass.
        """
        # Run get_pass to check if pass exists
        self.get_pass(cam_name, pass_name)

        del self.cams[cam_name].passes[pass_name]
        _log.info('Reset Cam: %s  Pass: %s' % (cam_name, pass_name))

    def reset_cam(self, cam_name):
        """
        Shorthand to delete the specified cam.
        """
        # Check if camera is in memory, raise ValueError if it's not
        if cam_name in self.cams:
            del self.cams[cam_name]
            _log.info('Reset Cam: %s' % cam_name)
        else:
            raise ValueError('Could not find Cam %s' % cam_name)

    def reset_all(self):
        """
        Shorthand to clear Radish's memory.  Nuclear option.
        """
        self.cams = {}
        _log.info('Reset RadishIO Memory')


class RadishCam(object):
    """
    RadishIO Cam data
    """
    def __init__(self, name):
        self.type = 'CAM'
        self.name = name
        self.passes = {}

        _log.debug('RadishCam %s Initialized' % self.name)

    def __repr__(self):
        indent = ('\r' + (1 * '|\t'))
        output = '%s .type: %s' % (indent, self.type)
        output += '%s .name: %s' % (indent, self.name)
        output += '%s .passes {' % indent
        for k, v in self.passes.items():
            output += '%s|\t%s' % (indent, k)
            output += repr(v)
        output += '%s}' % indent

        return output


class RadishPass(object):
    """
    RadishIO Pass data
    """
    def __init__(self, name):
        self.type = 'PASS'
        self.name = name
        self.layers = {}
        self.lights = {}
        self.effects = {}
        self.elements = {}
        self.resolution = {'x': None, 'y': None}

        _log.debug('RadishPass %s Initialized' % self.name)

    def __repr__(self):
        indent = ('\r' + (2 * '|\t'))
        output = '%s .type: %s' % (indent, self.type)
        output += '%s .name: %s' % (indent, self.name)
        output += '%s .layers {' % indent
        for k, v in self.layers.items():
            output += '%s|\t%s' % (indent, k)
            output += repr(v)
        output += '%s}' % indent

        output += '%s .lights {' % indent
        for k, v in self.lights.items():
            output += '%s|\t%s' % (indent, k)
            output += repr(v)
        output += '%s}' % indent

        output += '%s .effects {' % indent
        for k, v in self.effects.items():
            output += '%s|\t%s' % (indent, k)
            output += repr(v)
        output += '%s}' % indent

        output += '%s .elements {' % indent
        for k, v in self.elements.items():
            output += '%s|\t%s' % (indent, k)
            output += repr(v)
        output += '%s}' % indent

        return output


class RadishLayer(object):
    """
    RadishIO Layer data.  If provided, misc should be a dictionary of additional properties.
    """
    def __init__(self, name, on=None, misc=None):
        self.type = 'LAYER'
        self.name = name
        self.on = on
        self.misc = misc

        _log.debug('RadishLayer %s Initialized' % self.name)

    def __repr__(self):
        indent = ('\r' + (3 * '|\t'))
        output = '%s .type: %s' % (indent, self.type)
        output += '%s .name: %s' % (indent, self.name)
        output += '%s .on: %s' % (indent, self.on)

        return output

class RadishLight(object):
    """
    RadishIO Light data.  If provided, misc should be a dictionary of additional properties.
    """
    def __init__(self, name, enabled=None, on=None, instances=[], misc=None):
        self.type = 'LIGHT'
        self.name = name
        self.enabled = enabled
        self.on = on
        self.instances = instances
        self.misc = misc

        _log.debug('RadishLight %s Initialized' % self.name)

    def __repr__(self):
        indent = ('\r' + (3 * '|\t'))
        output = '%s .type: %s' % (indent, self.type)
        output += '%s .name: %s' % (indent, self.name)
        output += '%s .enabled: %s' % (indent, self.enabled)
        output += '%s .on: %s' % (indent, self.on)
        output += '%s .instances: %s' % (indent, self.instances)

        return output

class RadishEffect(object):
    """
    RadishIO Effect data.  If provided, misc should be a dictionary of additional properties.
    """
    def __init__(self, name, active=None, misc=None):
        self.type = 'EFFECT'
        self.name = name
        self.active = active
        self.misc = misc

        _log.debug('RadishEffect %s Initialized' % self.name)

    def __repr__(self):
        indent = ('\r' + (3 * '|\t'))
        output = '%s .type: %s' % (indent, self.type)
        output += '%s .name: %s' % (indent, self.name)
        output += '%s .active: %s' % (indent, self.active)

        return output

class RadishElement(object):
    """
    RadishIO Render Element data.  If provided, misc should be a dictionary of additional properties.
    """
    def __init__(self, name, enabled=None, misc=None):
        self.type = 'ELEMENT'
        self.name = name
        self.enabled = enabled
        self.misc = misc

        _log.debug('RadishElement %s Initialized' % self.name)

    def __repr__(self):
        indent = ('\r' + (3 * '|\t'))
        output = '%s .type: %s' % (indent, self.type)
        output += '%s .name: %s' % (indent, self.name)
        output += '%s .enabled: %s' % (indent, self.enabled)

        return output


_log.debug('module loaded')