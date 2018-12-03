# Destroys instances of the dialog before recreating it
# This has to go first, before modules are reloaded or the ui var is redeclared.
try:
    rd_ui.close()
    _log.info('Closing old instances of UI...')
except:
    pass

# --------------------
#       Modules
# --------------------

import sys

# 3ds Max
import pymxs
import MaxPlus

# Misc
import sys
import os

# For 3ds Max - Temporarily add this file's directory to PATH
sys.path.append(os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))))

# Force reload of Radish modules
try:
    for m in sys.modules.keys():
        if m not in init_modules:
            del(sys.modules[m])
except NameError:
    init_modules = sys.modules.keys()

# Local modules
import radish_logger
_log = radish_logger.setup('Radish')
_log.info('Logger %s Active' % _log.name)
_log.info('Starting Radish...')

import radish_ui

_rt = pymxs.runtime


# --------------------
#    Dialog Setup
# --------------------

# Path to UI file
_uif = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))) + "\\radish_standalone.ui"

_app = MaxPlus.GetQMaxMainWindow()
rd_ui = radish_ui.RadishUI(_uif, _rt, _app)

# Punch it
rd_ui.show()
_log.info('GUI created')
