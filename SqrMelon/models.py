import cgmath


class ModelNodeBase(object):
    def __init__(self):
        self._name = self.__class__.__name__
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
    def __init__(self):
        self._name = "Unnamed model"
        self._nodes = []

    @property
    def name(self):
        return self._name

    @property
    def nodes(self):
        return tuple(self._nodes)

    def addNode(self, node):
        node.model = self
        self._nodes.append(node)


class Models(object):
    def __init__(self):
        self._models = []

        # temp:
        m = Model()
        m.addNode(ModelNodeBox())
        m.addNode(ModelNodeBox())
        m.nodes[0].size = cgmath.Vec3(0.2, 0.1, 0.1)
        m.nodes[0].translation = cgmath.Vec3(0.0, 0.5, 0.0)
        self._models.append(m)

        m = Model()
        m.addNode(ModelNodeBox())
        self._models.append(m)

    @property
    def models(self):
        return tuple(self._models)