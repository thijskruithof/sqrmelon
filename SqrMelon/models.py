import cgmath
from qtutil import *
from util import toPrettyXml, currentProjectFilePath
from xml.etree import cElementTree
from projutil import parseXMLWithIncludes
from xmlutil import vec3ToXmlAttrib, xmlAttribToVec3
from fileutil import FilePath


class Bounds(object):
    def __init__(self):
        self._min = None
        self._max = None

    def add(self, other):
        if isinstance(other, Bounds):
            self.add(other.min)
            self.add(other.max)
            return

        if self._min is None:
            self._min = other
            self._max = other
            return

        self._min = cgmath.Vec3(min(self._min[0], other[0]), min(self._min[1], other[1]), min(self._min[2], other[2]))
        self._max = cgmath.Vec3(max(self._max[0], other[0]), max(self._max[1], other[1]), max(self._max[2], other[2]))

    @property
    def isValid(self):
        return not self._min is None

    @property
    def min(self):
        return self._min

    @property
    def max(self):
        return self._max

    @property
    def center(self):
        return (self._min + self._max) * 0.5

class ModelNodeBase(object):
    """
    Base class for a node of the Model
    """
    def __init__(self):
        self._name = self.__class__.__name__[9:]
        self._translation = cgmath.Vec3(0.0,0.0,0.0)
        self._rotation = cgmath.Vec3(0.0,0.0,0.0)
        self._scale = 1.0
        self._model = None
        self._subtractive = False

    def duplicate(self, newModel=None):
        dupe = self.__class__()
        dupe._name = self._name
        dupe._translation = self._translation
        dupe._rotation = self._rotation
        dupe._scale = self._scale
        dupe._model = self._model if newModel is None else newModel
        return dupe

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, model):
        self._model = model

    @property
    def translation(self):
        return cgmath.Vec3(self._translation)

    @translation.setter
    def translation(self, tr):
        self._translation = cgmath.Vec3(tr)
        self._model._models.modelChanged.emit(self._model)

    @property
    def rotation(self):
        return cgmath.Vec3(self._rotation)

    @rotation.setter
    def rotation(self, r):
        self._rotation = cgmath.Vec3(r)
        self._model._models.modelChanged.emit(self._model)

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, v):
        self._scale = v
        self._model._models.modelChanged.emit(self._model)

    @property
    def subtractive(self):
        return self._subtractive

    @subtractive.setter
    def subtractive(self, s):
        self._subtractive = s
        self._model._models.modelChanged.emit(self._model)

    def move(self, indexDelta):
        self._model.onNodeMove(self, indexDelta)

    def getModelTransform(self):
        return cgmath.Mat44.scale(self._scale, self._scale, self._scale) * \
               cgmath.Mat44.rotateZ(self._rotation[2]) * \
               cgmath.Mat44.rotateY(self._rotation[1]) * \
               cgmath.Mat44.rotateX(self._rotation[0]) * \
               cgmath.Mat44.translate(self._translation[0], self._translation[1], self._translation[2])

    def saveToElementTree(self, parentElement):
        xNode = cElementTree.SubElement(parentElement, self.__class__.__name__,
            {'name': self.name,
             'translation' : vec3ToXmlAttrib(self._translation),
             'rotation': vec3ToXmlAttrib(self._rotation),
             'scale': str(self._scale),
             })
        return xNode

    def loadFromElementTree(self, element):
        self._name = element.attrib['name']
        self._translation = xmlAttribToVec3(element.attrib['translation'])
        self._rotation = xmlAttribToVec3(element.attrib['rotation'])
        self._scale = float(element.attrib['scale'])


class ModelNodeBox(ModelNodeBase):
    """
    Box node of a model
    """
    def __init__(self):
        super(ModelNodeBox, self).__init__()
        self._size = cgmath.Vec3(1.0,1.0,1.0)

    def duplicate(self, newModel=None):
        dupe = super(ModelNodeBox, self).duplicate(newModel)
        dupe._size = self._size
        dupe._model.onNodeDuplicated(self, dupe)
        return dupe

    def getModelTransform(self):
        return cgmath.Mat44.scale(self._size[0] * 0.5, self._size[1] * 0.5, self._size[2] * 0.5) * super(ModelNodeBox, self).getModelTransform()

    @property
    def size(self):
        return cgmath.Vec3(self._size)

    @size.setter
    def size(self, s):
        self._size = cgmath.Vec3(s)
        self._model._models.modelChanged.emit(self._model)

    def saveToElementTree(self, parentElement):
        xNode = super(ModelNodeBox, self).saveToElementTree(parentElement)
        xNode.set('size', "%f,%f,%f" % (self._size[0], self._size[1], self._size[2]))
        return xNode

    def loadFromElementTree(self, element):
        super(ModelNodeBox, self).loadFromElementTree(element)
        self._size = xmlAttribToVec3(element.attrib['size'])

    def getBounds(self):
        modelTransform = self.getModelTransform()
        bounds = Bounds()
        for z in range(-1,2,2):
            for y in range(-1, 2, 2):
                for x in range(-1, 2, 2):
                    p = cgmath.Vec4(float(x), float(y), float(z), 1.0)
                    p = modelTransform * p
                    bounds.add(cgmath.Vec3(p[0],p[1],p[2]))
        return bounds

    def getFieldFragmentShaderText(self):
        # Get model transform (without our own size in it)
        invModelTransform = super(ModelNodeBox, self).getModelTransform()
        invModelTransform.inverse()

        str = "\td = "
        if self._subtractive:
            str += "max(d, -"
        else:
            str += "min(d, "

        str += "fBox((p4*mat4(%f,%f,%f,%f,%f,%f,%f,%f,%f,%f,%f,%f,%f,%f,%f,%f)).xyz, vec3(%f,%f,%f)));\n" % (invModelTransform[0],invModelTransform[4],invModelTransform[8],invModelTransform[12], invModelTransform[1],invModelTransform[5],invModelTransform[9],invModelTransform[13], invModelTransform[2], invModelTransform[6],invModelTransform[10],invModelTransform[14], invModelTransform[3],invModelTransform[7],invModelTransform[11],invModelTransform[15], 0.5*self.size[0],0.5*self.size[1],0.5*self.size[2])
        return str

class Model(object):
    """
    Model consisting of a collection of nodes
    """
    def __init__(self):
        self._name = "Model"
        self._nodes = []
        self._models = None

    def duplicate(self):
        dupe = Model()
        dupe._name = self._name
        dupe._models = self._models
        dupe._nodes = []
        dupe._models.onModelDuplicated(self, dupe)
        # Duplicate our nodes (and have them added to ourself)
        for node in self._nodes:
            node.duplicate(dupe)

    @property
    def models(self):
        return self._models

    @models.setter
    def models(self, models):
        self._models = models

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def nodes(self):
        return tuple(self._nodes)

    def addBox(self):
        node = ModelNodeBox()
        node.model = self
        self._models.preNodeAddedToModel.emit(self, node)
        self._nodes.append(node)
        self._models.postNodeAddedToModel.emit(self, node)
        self._models.modelChanged.emit(self)
        return node

    def removeNode(self, node):
        self._models.preNodeRemovedFromModel.emit(self, node)
        self._nodes.remove(node)
        self._models.postNodeRemovedFromModel.emit(self, node)
        self._models.modelChanged.emit(self)

    def onNodeDuplicated(self, originalNode, newNode):
        self._models.preNodeAddedToModel.emit(self, newNode)
        self._nodes.insert(originalNode._model._nodes.index(originalNode)+1, newNode)
        self._models.postNodeAddedToModel.emit(self, newNode)
        self._models.modelChanged.emit(self)

    def onNodeMove(self, node, indexDelta):
        curIndex = self._nodes.index(node)
        newIndex = curIndex+indexDelta
        if newIndex < 0 or newIndex >= len(self._nodes) or newIndex == curIndex:
            return
        curNode = self._nodes[curIndex]
        newNode = self._nodes[newIndex]
        self._models.preNodeRemovedFromModel.emit(self, curNode)
        self._nodes.remove(curNode)
        self._models.postNodeRemovedFromModel.emit(self, curNode)
        self._models.preNodeRemovedFromModel.emit(self, newNode)
        self._nodes.remove(newNode)
        self._models.postNodeRemovedFromModel.emit(self, newNode)

        if curIndex < newIndex:
            self._models.preNodeAddedToModel.emit(self, newNode)
            self._nodes.insert(curIndex, newNode)
            self._models.postNodeAddedToModel.emit(self, newNode)
            self._models.preNodeAddedToModel.emit(self, curNode)
            self._nodes.insert(newIndex, curNode)
            self._models.postNodeAddedToModel.emit(self, curNode)
        else:
            self._models.preNodeAddedToModel.emit(self, curNode)
            self._nodes.insert(newIndex, curNode)
            self._models.postNodeAddedToModel.emit(self, curNode)
            self._models.preNodeAddedToModel.emit(self, newNode)
            self._nodes.insert(curIndex, newNode)
            self._models.postNodeAddedToModel.emit(self, newNode)

        self._models.modelChanged.emit(self)

    def saveToElementTree(self, parentElement):
        xModel = cElementTree.SubElement(parentElement, 'Model', {'name': self.name})
        for node in self.nodes:
            node.saveToElementTree(xModel)
        return xModel

    def loadFromElementTree(self, element):
        self._name = element.attrib['name']
        for xNode in element:
            nodeClass = globals()[xNode.tag]
            node = nodeClass()
            node.model = self
            self._nodes.append(node)
            node.loadFromElementTree(xNode)

    def getBounds(self):
        bounds = Bounds()
        for node in self.nodes:
            bounds.add(node.getBounds())
        return bounds

    def getFieldFragmentShaderText(self):
        bounds = self.getBounds()
        boundsRange = bounds.max - bounds.min
        # Add 5% border to bounds
        bounds.add(bounds.min - boundsRange * 0.05)
        bounds.add(bounds.max + boundsRange * 0.05)
        boundsRange = bounds.max - bounds.min

        # Make bounds uniform
        maxBoundRange = max(max(boundsRange[0], boundsRange[1]), boundsRange[2])
        boundsIncrease = cgmath.Vec3(maxBoundRange - boundsRange[0], maxBoundRange - boundsRange[1], maxBoundRange - boundsRange[2])
        bounds.add(bounds.min - boundsIncrease * 0.5)
        bounds.add(bounds.max + boundsIncrease * 0.5)
        boundsRange = bounds.max - bounds.min

        # str = "uniform float uSlice;\n"+\
        # "\n"+\
        # "void main()\n"+\
        # "{\n"+\
        # "\tvec3 p = vec3(gl_FragCoord.x,gl_FragCoord.y,uSlice)/uResolution.x;\n"+\
        # ("\tp = p * vec3(%f,%f,%f) + vec3(%f,%f,%f);\n" % (boundsRange[0],boundsRange[1],boundsRange[2],bounds.min[0],bounds.min[1],bounds.min[2])) +\
        # "\tvec4 p4 = vec4(p, 1.0);\n"+\
        # "\n"+\
        # "\tfloat d = 99999.0;\n"

        funcName = self.name.replace(' ', '')

        str = ("float f%s(vec3 p)\n" % funcName)+\
        "{\n"+\
        "\tvec4 p4 = vec4(p, 1.0);\n"+\
        "\n"+\
        "\tfloat d = 99999.0;\n"

        for node in self.nodes:
            str += node.getFieldFragmentShaderText()

        str += "\treturn d;\n"+\
        "}\n"
        return str

    def export(self, path):
        filePath = FilePath(path)
        filePath = filePath.join("%s.glsl" % self._name)
        filePath.ensureExists()

        str = self.getFieldFragmentShaderText()

        with filePath.edit() as fh:
            fh.write(str)

        return

class Models(QObject):
    """
    Collection of models
    """
    preModelAdded = pyqtSignal(object)
    postModelAdded = pyqtSignal(object)
    preModelRemoved = pyqtSignal(object)
    postModelRemoved = pyqtSignal(object)
    preNodeAddedToModel = pyqtSignal(object, object)
    postNodeAddedToModel = pyqtSignal(object, object)
    preNodeRemovedFromModel = pyqtSignal(object, object)
    postNodeRemovedFromModel = pyqtSignal(object, object)
    modelChanged = pyqtSignal(object)

    def __init__(self):
        super(Models, self).__init__()
        self._models = []

        # Always start with a box
        m = self.addModel()
        b = m.addBox()
        b.size = cgmath.Vec3(0.2, 0.1, 0.1)
        b.translation = cgmath.Vec3(0.0, 0.5, 0.0)
        m.addBox()

    @property
    def models(self):
        return tuple(self._models)

    def addModel(self):
        model = Model()
        model.models = self
        self.preModelAdded.emit(model)
        self._models.append(model)
        self.postModelAdded.emit(model)
        return model

    def removeModel(self, model):
        self.preModelRemoved.emit(model)
        self._models.remove(model)
        self.postModelRemoved.emit(model)

    def onModelDuplicated(self, originalModel, newModel):
        self.preModelAdded.emit(newModel)
        self._models.insert(self._models.index(originalModel) + 1, newModel)
        self.postModelAdded.emit(newModel)

    def saveToProject(self):
        project = currentProjectFilePath()
        root = parseXMLWithIncludes(project)

        xModels = cElementTree.SubElement(root, 'Models')
        for model in self._models:
            model.saveToElementTree(xModels)

        with project.edit() as fh:
            fh.write(toPrettyXml(root))

    def loadFromProject(self):
        # Clear all
        while len(self._models) > 0:
            self.removeModel(self._models[0])

        project = currentProjectFilePath()
        if project and project.exists():
            text = project.content()

            try:
                root = cElementTree.fromstring(text)
            except:
                root = None

            if root is not None:
                xModels = root.find('Models')
                if not xModels is None:
                    for xModel in xModels.findall('Model'):
                        model = Model()
                        model.models = self
                        model.loadFromElementTree(xModel)
                        self._models.append(model)


