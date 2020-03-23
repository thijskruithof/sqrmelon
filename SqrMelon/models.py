import cgmath
from qtutil import *
from util import toPrettyXml, currentProjectFilePath
from xml.etree import cElementTree
from projutil import parseXMLWithIncludes
from xmlutil import vec3ToXmlAttrib, xmlAttribToVec3

class ModelNodeBase(object):
    """
    Base class for a node of the Model
    """
    def __init__(self):
        self._name = self.__class__.__name__[9:]
        self._translation = cgmath.Vec3(0,0,0)
        self._rotation = cgmath.Vec3(0,0,0)
        self._scale = 1.0
        self._model = None

    def duplicate(self):
        newNode = self.__class__()
        newNode._name = self._name
        newNode._translation = self._translation
        newNode._rotation = self._rotation
        newNode._scale = self._scale
        newNode._model = self._model
        return newNode

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

    @property
    def rotation(self):
        return cgmath.Vec3(self._rotation)

    @rotation.setter
    def rotation(self, r):
        self._rotation = cgmath.Vec3(r)

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, v):
        self._scale = v

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
        self._size = cgmath.Vec3(1,1,1)

    def duplicate(self):
        dupe = super(ModelNodeBox, self).duplicate()
        dupe._size = self._size
        self._model.onNodeDuplicated(self, dupe)
        return dupe

    def getModelTransform(self):
        return cgmath.Mat44.scale(self._size[0] * 0.5, self._size[1] * 0.5, self._size[2] * 0.5) * super(ModelNodeBox, self).getModelTransform()

    @property
    def size(self):
        return cgmath.Vec3(self._size)

    @size.setter
    def size(self, s):
        self._size = cgmath.Vec3(s)

    def saveToElementTree(self, parentElement):
        xNode = super(ModelNodeBox, self).saveToElementTree(parentElement)
        xNode.set('size', "%f,%f,%f" % (self._size[0], self._size[1], self._size[2]))
        return xNode

    def loadFromElementTree(self, element):
        super(ModelNodeBox, self).loadFromElementTree(element)
        self._size = xmlAttribToVec3(element.attrib['size'])

class Model(object):
    """
    Model consisting of a collection of nodes
    """
    def __init__(self):
        self._name = "Model"
        self._nodes = []
        self._models = None

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
        self._nodes.insert(self._nodes.index(originalNode)+1, newNode)
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


