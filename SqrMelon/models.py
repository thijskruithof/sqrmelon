import cgmath
from qtutil import *


class ModelNodeBase(object):
    """
    Base class for a node of the Model
    """
    def __init__(self):
        self._name = self.__class__.__name__[9:]
        self._translation = cgmath.Vec3(0,0,0)
        #self._rotation = cgmath.Vec3(0,0,0)
        self._scale = 1
        self._model = None

    @property
    def name(self):
        return self._name

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
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, v):
        self._scale = v

    def getModelTransform(self):
        # todo: add rotation as well
        return cgmath.Mat44.scale(self._scale, self._scale, self._scale) * cgmath.Mat44.translate(self._translation[0], self._translation[1], self._translation[2])

class ModelNodeBox(ModelNodeBase):
    """
    Box node of a model
    """
    def __init__(self):
        super(ModelNodeBox, self).__init__()
        self._size = cgmath.Vec3(1,1,1)

    def getModelTransform(self):
        return cgmath.Mat44.scale(self._size[0] * 0.5, self._size[1] * 0.5, self._size[2] * 0.5) * super(ModelNodeBox, self).getModelTransform()

    @property
    def size(self):
        return cgmath.Vec3(self._size)

    @size.setter
    def size(self, s):
        self._size = cgmath.Vec3(s)

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
