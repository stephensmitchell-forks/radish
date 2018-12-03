# Import PyMXS, MaxPlus, and set up shorthand vars
import pymxs
import MaxPlus
import logging

# PyMXS variable setup
rt = pymxs.runtime

# MaxPlus variable setup
maxScript = MaxPlus.Core.EvalMAXScript


# --------------------
#   Logging Classes
# --------------------
class LogToMaxListener(logging.Handler):
    def __init__(self):
        super(LogToMaxListener, self).__init__()
        # Apply a formatter to this handler on init
        self.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))

    def emit(self, record):
        output = self.format(record)
        # Always strip out quotations to be safe.  @ will force it to print literally.
        output = 'print @"' + output.replace('"', "'") + '"'
        maxScript(output)


# --------------------
#    Logging Setup
# --------------------
def setup(log_name=None, log_level=logging.DEBUG, log_handler=LogToMaxListener):
    """
    Sets up the program's logger.
    :param log_name: String. Name to give this logger, typically __name__ of calling program.
    :param log_level: A logging parameter, logging.DEBUG .INFO .WARNING etc.
    :param log_handler: A Handler class, defaults to SimpleHandler.
    :return: Logger object.
    """
    if log_name is not None:
        _log = logging.getLogger(log_name)
    else:
        _log = logging.getLogger()

    # Clean up any old handlers on this logger
    # These are from a user running the program multiple times in one session
    _log.debug('Cleaning up old handlers on logger %s...' % log_name)
    for handler in list(_log.handlers):
        _log.removeHandler(handler)

    _log.setLevel(log_level)
    _log.addHandler(log_handler())
    _log.info('Logger Set-Up')

    return _log
