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
xml_bool = util.xml_get_bool

class RadishIO(object):
    def __init__(self):
        self.cams = {}

        # End of Init
        # ---------------

    # -------------------
    #      Builtins
    # -------------------
    def __repr__(self):
        output = '\rRadishIO Instance'
        output += '\r .cams {'
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
        for tgt_cam in cfg_root.findall("./*[@type='CAM']"):
            cam_name = tgt_cam.attrib['realName']

            # Get all passes under this camera, then iterate over them to populate pass info
            for tgt_pass in tgt_cam.findall("./*[@type='PASS']"):
                pass_name = tgt_pass.attrib['realName']
                rad_pass = self.set_pass(cam_name, pass_name)

                # Get Layers
                for tgt_layer in tgt_pass.findall('./LAYERS/*'):
                    # Get attributes of this Layer
                    tgt_name = None
                    tgt_on = True
                    tgt_misc = {}
                    for k, v in tgt_layer.attrib.items():
                        if k == 'realName':
                            tgt_name = v
                        elif k == 'on':
                            tgt_on = xml_bool(v)
                        else:
                            tgt_misc[k] = v

                    # Make a new RadishLayer
                    rad_pass.layers[tgt_name] = RadishLayer(tgt_name, tgt_on, tgt_misc)

                # Get Lights
                for tgt_light in tgt_pass.findall('./LIGHTS/*'):
                    # Get the attributes of this Light
                    tgt_name = None
                    tgt_on = True
                    tgt_enabled = False
                    tgt_instances = []
                    tgt_misc = {}
                    for k, v in tgt_light.attrib.items():
                        if k == 'realName':
                            tgt_name = v
                        elif k == 'on':
                            tgt_on = v
                        elif k == 'enabled':
                            tgt_enabled = v
                        else:
                            tgt_misc[k] = v
                    for child in tgt_light.findall("./*"):
                        tgt_instances.append([child.attrib['realName']])

                    # Make a new RadishLight
                    rad_pass.lights[tgt_name] = RadishLight(tgt_name,tgt_enabled,tgt_on,tgt_instances,tgt_misc)

                # Get Effects

                # Get Elements


        # DEBUG - Dump resulting RadishIO memory to log
        _log.info(repr(self))

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
    def __init__(self, name, on=False, misc={}):
        self.type = 'LAYER'
        self.name = name
        self.on = on

        if len(misc) > 0:
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
    def __init__(self, name, enabled=None, on=None, instances=[], misc={}):
        self.type = 'LIGHT'
        self.name = name
        self.enabled = enabled
        self.on = on
        self.instances = []

        if len(misc) > 0:
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
    def __init__(self, name, active=None, misc={}):
        self.type = 'EFFECT'
        self.name = name
        self.active = active

        if len(misc) > 0:
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
    def __init__(self, name, enabled=None, misc={}):
        self.type = 'ELEMENT'
        self.name = name
        self.enabled = enabled

        if len(misc) > 0:
            self.misc = misc

        _log.debug('RadishElement %s Initialized' % self.name)

    def __repr__(self):
        indent = ('\r' + (3 * '|\t'))
        output = '%s .type: %s' % (indent, self.type)
        output += '%s .name: %s' % (indent, self.name)
        output += '%s .enabled: %s' % (indent, self.enabled)

        return output


_log.debug('module loaded')