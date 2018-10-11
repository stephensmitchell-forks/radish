# Import PyMXS, MaxPlus, and set up shorthand vars
import pymxs
import MaxPlus
import logging

# PyMXS variable setup
rt = pymxs.runtime

# MaxPlus variable setup
maxScript = MaxPlus.Core.EvalMAXScript


# Custom Logging Classes
class CustomHandler(logging.Handler):
    def __init__(self):
        super(CustomHandler, self).__init__()
        # Apply a formatter to this handler on init
        self.setFormatter(logging.Formatter('%(levelname)s - %(name)s - %(message)s'))

    def emit(self, record):
        output = self.format(record)
        # Always strip out quotations to be safe.  @ will force it to print literally.
        output = 'print @"' + output.replace('"', "'") + '"'
        maxScript(output)


# Utility Functions
def max_out(x):
    """
    Print x to MAXScript Listener.
    """

    # Always convert to string and strip out quotations to be safe.  @ will force it to print literally.
    output = 'print @"' + str(x).replace('"', "'") + '"'
    maxScript(output)


def get_obj_props(obj):
    """
    Does what showProperties should do, and builds a dictionary of property:value pairs
    for a valid Max object.
    :param obj: The max object.
    :return: A dictionary of property:value pairs.
    """
    propList = rt.getPropNames(obj)
    propDict = {}

    for i in propList:
        propDict[i] = str(rt.getProperty(obj, i))

    return propDict


def pad_string(str1, str2, padding, x):
    """
    Concatenates two strings, padding the joint with whitespace so the second string
    begins at a certain position.  Pads with one space if it's already past that pos.
    :param str1: The first string
    :param str2: The second string
    :param padding: The minimum position for str2 to begin
    :param x: The character to pad with.  Defaults to ' '
    :return:
    """
    if x is None:
        x = ' '

    output = str1
    padding = padding - len(str1)

    if padding > 0:
        output = output + (x * padding)
    else:
        output = output + x

    output = output + str2
    return output


def get_instances(x):
    """
    A short MaxScript snippet to get instances of an object and return their objects in an array.
    :param x: The input object
    :return: An array of Max objects.  If there are no instances, it will only contain the source object.
    """
    max_out('DEBUG: get_instances(' + x.name + ')')
    instanceNames = maxScript('InstanceMgr.GetInstances $' + x.name + """ &instances
    out = #()
    for i in instances do append out i.name
    out""").Get()

    instanceObjs = []
    for i in instanceNames:
        instanceObjs.append(rt.getNodeByName(i))

    return instanceObjs


def xml_indent(el, depth=0, careful=False):
    """
    Formats an XML ETree with newlines and indents.
    By default, assumes that nothing is stored in el.text or el.tail.
    :param el: Root element of XML tree.
    :param depth: Used for recursive calls, stores depth in tree.
    :param careful: Checks for content in el.text and el.tail before overwriting.
    :return: None - Operates on existing tree.
    """
    # Prep newline and indent for child elements
    i = "\n" + depth*"\t"

    # Check if we're being careful or not, switch accordingly
    # If careful, append indent to contents of el.text and el.tail

    # If careless, replace contents
    if not careful:
        if len(el):
            el.text = i + "\t"  # Newline + Indent sub-elements
            el.tail = i  # Add newline after closing tag
            for el in el:  # Use same variable so that the last element in loop will remain accessible
                xml_indent(el, depth + 1)
            el.tail = i  # De-indent closing tag
        else:  # If there aren't sub-elements, just add a newline
            if not el.tail or not el.tail.strip():
                el.tail = i
