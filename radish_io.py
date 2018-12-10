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

class RadishIO(object):
    """
    A class to store data on scene states, as well as handle reading and writing those states to disk.
    By default it will initialize empty, but if it's passed a string keyword for a supported filetype it will try
    to load and parse that file.
    Supported keywords: XML
    """
    def __init__(self, config_type=None):
        self.cams = {}

        if config_type is not None:
            if config_type == 'XML':
                self.read_config_xml()
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
                _log.debug('...Layers...')
                if len(src_pass.layers) > 0:
                    cfg_layers = _ETree.SubElement(cfg_pass, 'LAYERS')
                    for src_layer in src_pass.layers.itervalues():
                        _ETree.SubElement(cfg_layers, _xml_tag_cleaner(src_layer.name), {'realName':src_layer.name,
                                                                                         'on':str(src_layer.on)})

                # Lights
                _log.debug('...Lights...')
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
                _log.debug('...Effects...')
                if len(src_pass.effects) > 0:
                    cfg_effects = _ETree.SubElement(cfg_pass, 'EFFECTS')
                    for src_effect in src_pass.effects.itervalues():
                        _ETree.SubElement(cfg_effects, _xml_tag_cleaner(src_effect.name), {'realName':src_effect.name,
                                                                                           'isActive':str(src_effect.active)})

                # Elements
                _log.debug('...Elements...')
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
        # TODO: Re-implement old save code to work with RadishIO's internal memory
        _log.debug('save_state')

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
        Shorthand to return the given pass for the given camera, or None if they don't exist.
        """
        if cam_name in self.cams:
            if pass_name in self.cams[cam_name].passes:
                _log.debug('Got Pass %s in Cam %s' % (pass_name, cam_name))
                return self.cams[cam_name].passes[pass_name]

        _log.warning('Pass %s in Cam %s not found!' % (pass_name, cam_name))
        return None


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