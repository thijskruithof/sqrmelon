from pycompat import *
import re
from xml.etree import cElementTree
from fileutil import FilePath
import xml.dom.minidom
import cgmath

def xmlFixSlashesRecursively(xElement):
    # replace backslashes in all text and values
    if xElement.text:
        xElement.text = xElement.text.replace('\\', '/')

    for key, value in xElement.attrib.items():
        xElement.attrib[key] = value.replace('\\', '/')

    for xChild in xElement:
        xmlFixSlashesRecursively(xChild)


def parseXMLWithIncludes(xmlFilePath):
    assert isinstance(xmlFilePath, FilePath)
    text = xmlFilePath.content()

    subs = []
    for result in re.finditer(r'<!--[ \t]*#[ \t]*include[ \t]+(.+)[ \t]*-->', text):
        inline = result.group(1).strip()
        inlineText = xmlFilePath.parent().join(inline).content()
        subs.append((result.start(0), result.end(0), inlineText))

    for start, end, repl in reversed(subs):
        text = '{}{}{}'.format(text[:start], repl, text[end:])

    xRoot = cElementTree.fromstring(text)
    xmlFixSlashesRecursively(xRoot)
    return xRoot



def toPrettyXml(root):
    root.text = None
    xmlFixSlashesRecursively(root)
    text = cElementTree.tostring(root)
    text = xml.dom.minidom.parseString(text).toprettyxml()
    text = text.replace('\r', '\n')
    return '\n'.join(line for line in text.split('\n') if line and line.strip())


def vec3ToXmlAttrib(vec3):
    return "%f,%f,%f" % (vec3[0], vec3[1], vec3[2])

def xmlAttribToVec3(attrib):
    vals = map(float, attrib.split(','))
    return cgmath.Vec3(vals[0], vals[1], vals[2])
