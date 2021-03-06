import functools

from qtutil import *
from OpenGL.GL import *
from OpenGL.GLU import *
import cgmath
import mathutil
import math
from util import toPrettyXml, currentProjectFilePath
from xml.etree import cElementTree
from projutil import parseXMLWithIncludes
from xmlutil import vec3ToXmlAttrib, xmlAttribToVec3
import icons

class PrimitiveType:
    GRID = 0        # Grid in XZ plane
    CUBE = 1        # Unit cube (-1..1)
    ARROW = 2       # Arrow (on X axis), length 1
    LINE = 3        # Line (on X axis), length 1
    CIRCLE = 4      # Circle in YZ plane, radius 1
    SCREEN_RECT = 5 # Rectangle on screen (0, 0) - (1, 1)

class Primitives:
    def __init__(self):
        self._vertex_data = []
        self._firstVertexIndex = [ 0, 0, 0, 0, 0, 0 ]
        self._numVertices = [ 0, 0, 0, 0, 0, 0 ]

        numGridLines = 20
        gridSpacing = 0.25

        for i in range(-numGridLines, numGridLines+1):
            # line on X axis
            self._vertex_data.extend([i*gridSpacing, 0, -numGridLines*gridSpacing])
            self._vertex_data.extend([i*gridSpacing, 0, numGridLines*gridSpacing])
            # line on Z axis
            self._vertex_data.extend([-numGridLines * gridSpacing, 0, i * gridSpacing])
            self._vertex_data.extend([numGridLines * gridSpacing, 0, i * gridSpacing])

        self._firstVertexIndex[PrimitiveType.GRID] = 0
        self._numVertices[PrimitiveType.GRID] = (numGridLines*2+1)*4

        # Construct a unit cube [-1,-1,-1] .. [1,1,1]
        for a in range(-1, 2, 2):
            for b in range(-1, 2, 2):
                self._vertex_data.extend([-1.0, float(a), float(b)])
                self._vertex_data.extend([1.0, float(a), float(b)])
                self._vertex_data.extend([float(a), -1.0, float(b)])
                self._vertex_data.extend([float(a), 1.0, float(b)])
                self._vertex_data.extend([float(a), float(b), -1.0])
                self._vertex_data.extend([float(a), float(b), 1.0])

        self._firstVertexIndex[PrimitiveType.CUBE] = self._firstVertexIndex[PrimitiveType.GRID] + self._numVertices[PrimitiveType.GRID]
        self._numVertices[PrimitiveType.CUBE] = len(self._vertex_data)//3 - self._firstVertexIndex[PrimitiveType.CUBE]

        # Construct an arrow (on 1,0,0 axis)
        arrowTipLen = 0.05
        arrowTipWidth = 0.03
        self._vertex_data.extend([0.0, 0.0, 0.0])
        self._vertex_data.extend([1.0, 0.0, 0.0])
        self._vertex_data.extend([1.0-arrowTipLen, arrowTipWidth, arrowTipWidth])
        self._vertex_data.extend([1.0, 0.0, 0.0])
        self._vertex_data.extend([1.0-arrowTipLen, arrowTipWidth, -arrowTipWidth])
        self._vertex_data.extend([1.0, 0.0, 0.0])
        self._vertex_data.extend([1.0-arrowTipLen, -arrowTipWidth, arrowTipWidth])
        self._vertex_data.extend([1.0, 0.0, 0.0])
        self._vertex_data.extend([1.0-arrowTipLen, -arrowTipWidth, -arrowTipWidth])
        self._vertex_data.extend([1.0, 0.0, 0.0])

        self._firstVertexIndex[PrimitiveType.ARROW] = self._firstVertexIndex[PrimitiveType.CUBE] + self._numVertices[PrimitiveType.CUBE]
        self._numVertices[PrimitiveType.ARROW] = len(self._vertex_data)//3 - self._firstVertexIndex[PrimitiveType.ARROW]

        # Construct a single line (on 1,0,0 axis)
        self._vertex_data.extend([0.0, 0.0, 0.0])
        self._vertex_data.extend([1.0, 0.0, 0.0])
        self._firstVertexIndex[PrimitiveType.LINE] = self._firstVertexIndex[PrimitiveType.ARROW] + self._numVertices[PrimitiveType.ARROW]
        self._numVertices[PrimitiveType.LINE] = len(self._vertex_data)//3 - self._firstVertexIndex[PrimitiveType.LINE]

        # Construct a circle in YZ plane
        numCircleSegments = 64
        prevCirclePos = []
        for i in range(0, numCircleSegments+1):
            phi = ((2.0 * math.pi) / numCircleSegments)*float(i)
            circlePos = [0.0, math.cos(phi), math.sin(phi)]
            if i > 0:
                self._vertex_data.extend(prevCirclePos)
                self._vertex_data.extend(circlePos)
            prevCirclePos = circlePos
        self._firstVertexIndex[PrimitiveType.CIRCLE] = self._firstVertexIndex[PrimitiveType.LINE] + self._numVertices[PrimitiveType.LINE]
        self._numVertices[PrimitiveType.CIRCLE] = len(self._vertex_data)//3 - self._firstVertexIndex[PrimitiveType.CIRCLE]

        # Construct a screen rect (0,0) - (1,1)
        self._vertex_data.extend([0.0, 0.0, 0.0])   # BL
        self._vertex_data.extend([1.0, 0.0, 0.0])   # BR
        self._vertex_data.extend([1.0, 0.0, 0.0])   # BR
        self._vertex_data.extend([1.0, 1.0, 0.0])   # TR
        self._vertex_data.extend([1.0, 1.0, 0.0])   # TR
        self._vertex_data.extend([0.0, 1.0, 0.0])   # TL
        self._vertex_data.extend([0.0, 1.0, 0.0])   # TL
        self._vertex_data.extend([0.0, 0.0, 0.0])   # BL
        self._firstVertexIndex[PrimitiveType.SCREEN_RECT] = self._firstVertexIndex[PrimitiveType.CIRCLE] + self._numVertices[PrimitiveType.CIRCLE]
        self._numVertices[PrimitiveType.SCREEN_RECT] = len(self._vertex_data)//3 - self._firstVertexIndex[PrimitiveType.SCREEN_RECT]

    @property
    def vertexData(self):
        return self._vertex_data

    def draw(self, primitiveType):
        glDrawArrays(GL_LINES, self._firstVertexIndex[primitiveType], self._numVertices[primitiveType])
        return

    def _projectEdgeVertices(self, mvp, vertexIndex0, vertexIndex1):
        v0 = cgmath.Vec4(self._vertex_data[vertexIndex0 * 3], self._vertex_data[vertexIndex0 * 3 + 1],
                         self._vertex_data[vertexIndex0 * 3 + 2], 1.0)
        v1 = cgmath.Vec4(self._vertex_data[vertexIndex1 * 3 ], self._vertex_data[vertexIndex1 * 3 + 1],
                         self._vertex_data[vertexIndex1 * 3 + 2], 1.0)

        v0 = v0 * mvp
        v1 = v1 * mvp
        v0x = v0[0] / v0[3]
        v0y = v0[1] / v0[3]
        v1x = v1[0] / v1[3]
        v1y = v1[1] / v1[3]

        return mathutil.Vec2(v0x, v0y), mathutil.Vec2(v1x, v1y)

    def _getSqDistanceToLine(self, mvp, mousePos, vertexIndex0, vertexIndex1):
        v0, v1 = self._projectEdgeVertices(mvp, vertexIndex0, vertexIndex1)

        v1v0x = v1.x - v0.x
        v1v0y = v1.y - v0.y
        len = v1v0x*v1v0x + v1v0y*v1v0y

        if len <= 0.00001:
            # Line has length of nearly 0
            return (mousePos[0] - v0.x)*(mousePos[0] - v0.x) + (mousePos[1] - v0.y)*(mousePos[1] - v0.y)

        t = ((mousePos[0] - v0.x)*v1v0x + (mousePos[1] - v0.y) * v1v0y) / len
        t = max(0.0, min(1.0, t))

        px = v0.x + t * v1v0x
        py = v0.y + t * v1v0y

        distSq = (mousePos[0] - px)*(mousePos[0] - px) + (mousePos[1] - py)*(mousePos[1] - py)
        return distSq

    def isMouseOn(self, primitiveType, mvp, mouseScreenPos,  minMouseDistSq):
        firstVertexIndex = self._firstVertexIndex[primitiveType]
        for vertexIndex in range(firstVertexIndex, firstVertexIndex+self._numVertices[primitiveType], 2):
            if self._getSqDistanceToLine(mvp, mouseScreenPos, vertexIndex, vertexIndex+1) <= minMouseDistSq:
                return True
        return False

    # Rough implementation of Liang-Barsky's line-box intersection algorithm
    def _edgeClip2D(self, num, denom, c):
        if abs(denom) < 0.000001:
            return num < 0
        t = num/denom
        if denom > 0:
            if t > c.y:
                return False
            if t > c.x:
                c.x = t
        else:
            if t < c.x:
                return False
            if t < c.y:
                c.y = t
        return True

    def _edgeIntersectsRect2D(self, mvp, rectP0, rectP1, vertexIndex0, vertexIndex1):
        v0, v1 = self._projectEdgeVertices(mvp, vertexIndex0, vertexIndex1)
        dx = v1.x - v0.x
        dy = v1.y - v0.y

        # Single point, inside?
        if abs(dx) < 0.000001 and abs(dy) < 0.000001 and \
            v0.x >= rectP0.x and v0.x <= rectP1.x and v0.y >= rectP0.y and v0.y <= rectP1.y:
            return True

        c = mathutil.Vec2(0.0, 1.0)
        return self._edgeClip2D(rectP0.x - v0.x, dx, c) and self._edgeClip2D(v0.x - rectP1.x, -dx, c) and \
               self._edgeClip2D(rectP0.y - v0.y, dy, c) and self._edgeClip2D(v0.y - rectP1.y, -dy, c)

    # Determine if the projection of a primitive of a given type with the given mvp would intersect with the specified rectangle.
    def intersectsRect2D(self, primitiveType, mvp, rectP0, rectP1):
        firstVertexIndex = self._firstVertexIndex[primitiveType]
        for vertexIndex in range(firstVertexIndex, firstVertexIndex + self._numVertices[primitiveType], 2):
            if self._edgeIntersectsRect2D(mvp, rectP0, rectP1, vertexIndex, vertexIndex+1):
                return True
        return False

class ModifierAxis:
    X = 0
    Y = 1
    Z = 2
    NONE = 3

class ModifierMode:
    SELECT = 0
    TRANSLATE = 1
    ROTATE = 2
    SCALE_NONUNIFORM = 3

class ModelerViewport(QOpenGLWidget):
    selectedModelNodesChanged = pyqtSignal(object, object)
    modifierModeChanged = pyqtSignal(object)
    cameraChanged = pyqtSignal(object)

    """
    Modeler window/viewport
    """
    def __init__(self, models):
        super(ModelerViewport, self).__init__()

        self.setLayout(vlayout())

        self._updateMinMouseClickDist()

        self._primitives = Primitives()

        self._models = models
        self._currentModel = None
        self._currentModelNodes = set()

        self._cameraTransform = cgmath.Mat44.translate(0, 0, -2)
        self._modelTransform =  cgmath.Mat44()
        self._viewTransform = cgmath.Mat44()

        self._cameraPivot = cgmath.Vec3(0.0,0.0,0.0)
        self._adjustingCamera = False
        self._adjustCameraMode = 0

        self._selecting = False

        self._modifierMode = ModifierMode.SELECT
        self._modifierAxis = ModifierAxis.NONE

        self.setFocusPolicy(Qt.StrongFocus)

        self.installEventFilter(self)

    def _updateMinMouseClickDist(self):
        minDist = 5 / (0.5 * min(self.width(), self.height()))
        self._minMouseClickDistSq = minDist*minDist

    def initializeGL(self):
        glClearColor(0.7, 0.7, 0.7, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        glClearDepth(1.0)
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_DEPTH_TEST)
        glShadeModel(GL_SMOOTH)
        glDisable(GL_CULL_FACE)

        glEnable(GL_MULTISAMPLE)
        #glEnable(GL_LINE_SMOOTH)

        vertex_array_id = glGenVertexArrays(1)
        glBindVertexArray(vertex_array_id)

        # A grid in XZ plane

        attr_id = 0  # No particular reason for 0,
        # but must match the layout location in the shader.

        vertex_buffer = glGenBuffers(1)

        glBindBuffer(GL_ARRAY_BUFFER, vertex_buffer)

        array_type = (GLfloat * len(self._primitives.vertexData))
        glBufferData(GL_ARRAY_BUFFER,
                        len(self._primitives.vertexData) * ctypes.sizeof(ctypes.c_float),
                        array_type(*self._primitives.vertexData),
                        GL_STATIC_DRAW)

        glVertexAttribPointer(
            attr_id,  # attribute 0.
            3,  # components per vertex attribute
            GL_FLOAT,  # type
            False,  # to be normalized?
            0,  # stride
            None  # array buffer offset
        )
        glEnableVertexAttribArray(attr_id)  # use currently bound VAO

        shaders = {
            GL_VERTEX_SHADER: '''\
                #version 330 core
                layout(location = 0) in vec3 vertexPosition_modelspace;
                uniform mat4 MVP;
                void main(){
                  gl_Position = MVP * vec4(vertexPosition_modelspace, 1);
                }
                ''',
            GL_FRAGMENT_SHADER: '''\
                #version 330 core
                uniform vec4 color;
                out vec3 outColor;
                void main(){
                  outColor = color.xyz;
                }
                '''
        }

        program_id = glCreateProgram()
        shader_ids = []
        for shader_type, shader_src in shaders.items():
            shader_id = glCreateShader(shader_type)
            glShaderSource(shader_id, shader_src)

            glCompileShader(shader_id)

            # check if compilation was successful
            result = glGetShaderiv(shader_id, GL_COMPILE_STATUS)
            info_log_len = glGetShaderiv(shader_id, GL_INFO_LOG_LENGTH)
            if info_log_len:
                logmsg = glGetShaderInfoLog(shader_id)
                raise Exception(logmsg)

            glAttachShader(program_id, shader_id)
            shader_ids.append(shader_id)

        glLinkProgram(program_id)

        # check if linking was successful
        result = glGetProgramiv(program_id, GL_LINK_STATUS)
        info_log_len = glGetProgramiv(program_id, GL_INFO_LOG_LENGTH)
        if info_log_len:
            logmsg = glGetProgramInfoLog(program_id)
            raise Exception(logmsg)

        glUseProgram(program_id)

        self._uniform_mvp = glGetUniformLocation(program_id, "MVP")
        self._uniform_color = glGetUniformLocation(program_id, "color")

    def paintGL(self):
        # view = inverse of camera, which is:
        self._viewTransform = \
            cgmath.Mat44.translate(-self._cameraTransform[12], -self._cameraTransform[13], -self._cameraTransform[14]) * \
            cgmath.Mat44(self._cameraTransform[0], self._cameraTransform[4], self._cameraTransform[8], 0, self._cameraTransform[1], self._cameraTransform[5], self._cameraTransform[9], 0, self._cameraTransform[2], self._cameraTransform[6], self._cameraTransform[10], 0, 0, 0, 0, 1)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Draw grid
        mvp = self._viewTransform * self._projection
        glUniformMatrix4fv(self._uniform_mvp, 1, False, (ctypes.c_float * 16)(*mvp))
        glUniform4f(self._uniform_color, 0.5, 0.5, 0.5, 1.0)
        glLineWidth(1)
        self._primitives.draw(PrimitiveType.GRID)

        # Draw nodes
        if self._currentModel is not None:
            # glLineWidth(2)

            # Put current model node at the end of the list
            nodes = list(self._currentModel.nodes)
            if len(self._currentModelNodes) > 0:
                for node in self._currentModelNodes:
                    nodes.remove(node)
                for node in self._currentModelNodes:
                    nodes.append(node)

            # Draw all nodes
            for node in nodes:
                modelTransform = node.getModelTransform()
                mvp = (modelTransform * self._viewTransform) * self._projection
                glUniformMatrix4fv( self._uniform_mvp, 1, False, (ctypes.c_float * 16)(*mvp))
                if node in self._currentModelNodes:
                    glUniform4f(self._uniform_color, 1.0, 1.0, 0.0, 1.0)
                else:
                    glUniform4f(self._uniform_color, 0.0, 0.0, 0.5, 1.0)
                self._primitives.draw(PrimitiveType.CUBE)

            # Draw our modifier?
            if self._modifierMode != ModifierMode.SELECT and len(self._currentModelNodes) > 0:
                self._drawModifier()

        # Draw selection rect
        if self._selecting and (self._selectCurrentMouseScreenPos - self._selectStartMouseScreenPos).lengthSq > 0.0:
            self._drawSelectionRect()

    def _isModifierVisible(self):
        return len(self._currentModelNodes) > 0

    def _getModifierMVP(self):
        modelTransform = self._getCurrentMainModelNode().getModelTransform()
        modifierSize = 0.05 if self._modifierMode == ModifierMode.ROTATE else 0.10

        if self._modifierMode == ModifierMode.TRANSLATE:
            # Translation is in world space, simply emit world space axes
            nonScaledModelTransform = cgmath.Mat44.translate(modelTransform[12], modelTransform[13], modelTransform[14])
        else:
            # Orthonormalize modelTransform (remove scale)
            modelRight = cgmath.Vec3(modelTransform[0], modelTransform[1], modelTransform[2])
            modelUp = cgmath.Vec3(modelTransform[4], modelTransform[5], modelTransform[6])
            modelForward = cgmath.Vec3(modelTransform[8], modelTransform[9], modelTransform[10])
            modelRight.normalize()
            modelUp.normalize()
            modelForward.normalize()

            nonScaledModelTransform = cgmath.Mat44(modelRight[0], modelRight[1], modelRight[2], 0,
                                                   modelUp[0], modelUp[1], modelUp[2], 0,
                                                   modelForward[0], modelForward[1], modelForward[2], 0,
                                                   modelTransform[12], modelTransform[13], modelTransform[14], 1)

        mv = nonScaledModelTransform * self._viewTransform
        mvp = cgmath.Mat44.scale(modifierSize * mv[14], modifierSize * mv[14],
                                 modifierSize * mv[14]) * mv * self._projection

        return mvp

    # Draw a modifier, such as a translation gizmo.
    def _drawModifier(self):
        # glLineWidth(1.5)

        if self._modifierMode == ModifierMode.SELECT:
            return

        mvp = self._getModifierMVP()
        primitiveType = self._getModifierAxisPrimitiveType()

        # X
        glUniformMatrix4fv(self._uniform_mvp, 1, False, (ctypes.c_float * 16)(*mvp))
        if self._modifierAxis == ModifierAxis.X:
            glUniform4f(self._uniform_color, 1.0, 1.0, 0.0, 1.0)
        else:
            glUniform4f(self._uniform_color, 1.0, 0.0, 0.0, 1.0)
        self._primitives.draw(primitiveType)
        # Y
        mvp = cgmath.Mat44.rotateZ(math.radians(90)) * mvp
        glUniformMatrix4fv(self._uniform_mvp, 1, False, (ctypes.c_float * 16)(*mvp))
        if self._modifierAxis == ModifierAxis.Y:
            glUniform4f(self._uniform_color, 1.0, 1.0, 0.0, 1.0)
        else:
            glUniform4f(self._uniform_color, 0.0, 1.0, 0.0, 1.0)
        self._primitives.draw(primitiveType)
        # Z
        mvp = cgmath.Mat44.rotateY(math.radians(-90)) * mvp
        glUniformMatrix4fv(self._uniform_mvp, 1, False, (ctypes.c_float * 16)(*mvp))
        if self._modifierAxis == ModifierAxis.Z:
            glUniform4f(self._uniform_color, 1.0, 1.0, 0.0, 1.0)
        else:
            glUniform4f(self._uniform_color, 0.0, 0.0, 1.0, 1.0)
        self._primitives.draw(primitiveType)

    # Draw a rectangle for the selection
    def _drawSelectionRect(self):
        mvp = cgmath.Mat44.scale(self._selectCurrentMouseScreenPos[0] - self._selectStartMouseScreenPos[0], self._selectCurrentMouseScreenPos[1] - self._selectStartMouseScreenPos[1], 1.0) * \
            cgmath.Mat44.translate(self._selectStartMouseScreenPos[0], self._selectStartMouseScreenPos[1], 0.0)

        glUniformMatrix4fv(self._uniform_mvp, 1, False, (ctypes.c_float * 16)(*mvp))
        glUniform4f(self._uniform_color, 1.0, 0.9, 0.05, 1.0)
        self._primitives.draw(PrimitiveType.SCREEN_RECT)

    def _convertMousePosToScreenPos(self, mousePosX, mousePosY):
        screenX = (mousePosX / self.width()) * 2.0 - 1.0
        screenY = ((mousePosY / self.height()) * -2.0 + 1.0)
        return cgmath.Vec4(screenX, screenY, 0.0, 0.0)

    def _getModifierAxisPrimitiveType(self):
        if self._modifierMode == ModifierMode.TRANSLATE:
            return PrimitiveType.ARROW
        elif self._modifierMode == ModifierMode.ROTATE:
            return PrimitiveType.CIRCLE
        else:
            return PrimitiveType.LINE

    # Determine which modifier axis the given mouse position is overlapping with.
    def _getMouseOnModifierAxis(self, mousePosX, mousePosY):
        screenPos = self._convertMousePosToScreenPos(mousePosX, mousePosY)
        modifierMvp = self._getModifierMVP()

        if self._modifierMode != ModifierMode.SELECT:
            primitiveType = self._getModifierAxisPrimitiveType()

            # X axis?
            mvp = modifierMvp
            if self._primitives.isMouseOn(primitiveType, mvp, screenPos, self._minMouseClickDistSq):
                return ModifierAxis.X
            # Y axis?
            mvp = cgmath.Mat44.rotateZ(math.radians(90)) * mvp
            if self._primitives.isMouseOn(primitiveType, mvp, screenPos, self._minMouseClickDistSq):
                return ModifierAxis.Y
            # Z axis?
            mvp = cgmath.Mat44.rotateY(math.radians(-90)) * mvp
            if self._primitives.isMouseOn(primitiveType, mvp, screenPos, self._minMouseClickDistSq):
                return ModifierAxis.Z

        return ModifierAxis.NONE

    def _getModelNodesUnderScreenRect(self, rectP0, rectP1):

        if self._currentModel is None:
            return None

        overlappingNodes = []
        nodes = list(self._currentModel.nodes)

        for node in nodes:
            modelTransform = node.getModelTransform()
            mvp = (modelTransform * self._viewTransform) * self._projection

            if self._primitives.intersectsRect2D(PrimitiveType.CUBE, mvp, rectP0, rectP1):
                overlappingNodes.append(node)

        return overlappingNodes

    # Center our view on the selection
    # If there's no selection we'll center the view on the whole model
    def centerView(self):
        centerPos = cgmath.Vec3(0.0, 0.0, 0.0)
        radius = 1.0

        # Do we have any current nodes? If so, center view on them
        if len(self._currentModelNodes) > 0:
            bounds = None
            for node in self._currentModelNodes:
                if bounds is None:
                    bounds = node.getBounds()
                else:
                    bounds.add(node.getBounds())
            centerPos = bounds.center
            radius = (bounds.max - centerPos).length
        # Otherwise, is there a current model? If so, center view on it
        elif self._currentModel != None:
            bounds = self._currentModel.getBounds()
            centerPos = bounds.center
            radius = (bounds.max - centerPos).length

        translation = centerPos - self._cameraPivot

        self._cameraPivot = self._cameraPivot + translation
        # Move camera as well
        self._cameraTransform = self._cameraTransform * cgmath.Mat44.translate(translation[0], translation[1], translation[2])

        # Pull back camera
        currentDist = (cgmath.Vec3(self._cameraTransform[12], self._cameraTransform[13], self._cameraTransform[14]) - self._cameraPivot).length

        fovH = math.radians(30)
        fovW = (self.width()/float(self.height()))*fovH
        desiredDist = 2.0*max(radius/math.tan(fovH), radius/math.tan(fovW))

        self._cameraTransform = cgmath.Mat44.translate(0.0, 0.0, currentDist-desiredDist) * self._cameraTransform
        self.cameraChanged.emit(self._cameraTransform)
        self.update()

    def __onResize(self):
        self._updateMinMouseClickDist()
        self.update()

    def resizeGL(self, w, h):
        self._projection = cgmath.Mat44.scale(1.0, 1.0, -1.0) * cgmath.Mat44.perspective(math.radians(30), w / float(h), 0.1, 100.0)

        self.__onResize()

    def mousePressEvent(self, mouseEvent):
        super(ModelerViewport, self).mousePressEvent(mouseEvent)

        if self._adjustingCamera:
            return

        modifiers = QApplication.keyboardModifiers()

        # Pan/Rotate/Zoom?
        if modifiers == Qt.AltModifier:
            self._adjustingCamera = True
            self._adjustCameraStartMousePos = mathutil.Vec2(mouseEvent.localPos().x(), mouseEvent.localPos().y())
            self._adjustCameraStartCamera = self._cameraTransform
            self._adjustCameraPivot = self._cameraPivot

            # Panning?
            if mouseEvent.buttons() & Qt.MiddleButton:
                self._adjustCameraMode = 0
            # Rotating?
            elif mouseEvent.buttons() & Qt.LeftButton:
                self._adjustCameraMode = 1
            # Zooming?
            elif mouseEvent.buttons() & Qt.RightButton:
                self._adjustCameraMode = 2

        # Simple click?
        else:
            clickHandled = False

            # Did we click on the modifier, if its visible?
            if self._modifierMode != ModifierMode.SELECT and self._isModifierVisible():
                axis = self._getMouseOnModifierAxis(mouseEvent.localPos().x(), mouseEvent.localPos().y())

                if axis != ModifierAxis.NONE:
                    node = self._getCurrentMainModelNode()
                    clickHandled = True
                    self._modifierAxis = axis
                    self._modifyStartMouseScreenPos = self._convertMousePosToScreenPos(mouseEvent.localPos().x(), mouseEvent.localPos().y())

                    self._modifyStartModelTranslation = {}
                    self._modifyStartModelRotationMatrix = {}
                    self._modifyStartModelSize = {}

                    for node in self._currentModelNodes:
                        self._modifyStartModelTranslation[node] = node.translation
                        self._modifyStartModelRotationMatrix[node] = \
                            cgmath.Mat44.rotateZ(node.rotation[2]) * \
                            cgmath.Mat44.rotateY(node.rotation[1]) * \
                            cgmath.Mat44.rotateX(node.rotation[0])
                        self._modifyStartModelSize[node] = node.size

                    self.update()

            # Otherwise update our selection
            if self._currentModel is not None and not clickHandled:
                clickHandled = True
                self._selecting = True
                self._selectStartMouseScreenPos = self._convertMousePosToScreenPos(mouseEvent.localPos().x(), mouseEvent.localPos().y())
                self._selectCurrentMouseScreenPos = cgmath.Vec4(self._selectStartMouseScreenPos)

    # Create a rotation matrix from an axis and an angle
    # Somehow the one from cgmath.Mat44 wasn't correct (for me)
    def axisAngle(self, axis, angle):
        # https://www.euclideanspace.com/maths/geometry/rotations/conversions/angleToMatrix/
        c = math.cos(angle)
        s = math.sin(angle)
        t = 1 - c
        m00 = c + axis[0] * axis[0] * t
        m11 = c + axis[1] * axis[1] * t
        m22 = c + axis[2] * axis[2] * t

        tmp1 = axis[0] * axis[1] * t
        tmp2 = axis[2] * s
        m10 = tmp1 + tmp2
        m01 = tmp1 - tmp2
        tmp1 = axis[0] * axis[2] * t
        tmp2 = axis[1] * s
        m20 = tmp1 - tmp2
        m02 = tmp1 + tmp2
        tmp1 = axis[1] * axis[2] * t
        tmp2 = axis[0] * s
        m21 = tmp1 + tmp2
        m12 = tmp1 - tmp2

        return cgmath.Mat44(m00, m01, m02, 0, m10, m11, m12, 0, m20, m21, m22, 0, 0, 0, 0, 1)

    # Get the screen space direction of a modifier axis
    def _getModifierAxisScreenDir(self, modifierAxisDir):
        mvp = self._getModifierMVP()
        v0 = cgmath.Vec4(0.0,0.0,0.0,1.0) * mvp
        v1 = cgmath.Vec4(modifierAxisDir[0],modifierAxisDir[1],modifierAxisDir[2],1.0) * mvp
        v0 /= v0[3]
        v1 /= v1[3]
        a = v1 - v0
        return a.normalized()

    def _getCurrentMainModelNode(self):
        return next(iter(self._currentModelNodes))

    def mouseMoveEvent(self, mouseEvent):
        super(ModelerViewport, self).mouseMoveEvent(mouseEvent)

        # Panning/Rotating/Zooming?
        if self._adjustingCamera:
            # Panning?
            if self._adjustCameraMode == 0:
                panSpeed = 0.025
                deltaMouse = mathutil.Vec2(mouseEvent.localPos().x(), mouseEvent.localPos().y()) - self._adjustCameraStartMousePos
                self._cameraTransform = cgmath.Mat44.translate(deltaMouse[0] * -panSpeed, deltaMouse[1] * panSpeed, 0.0) * self._adjustCameraStartCamera
                self._cameraPivot = self._adjustCameraPivot + cgmath.Vec3(self._cameraTransform[12] - self._adjustCameraStartCamera[12], self._cameraTransform[13] - self._adjustCameraStartCamera[13], self._cameraTransform[14] - self._adjustCameraStartCamera[14])

            # Rotating?
            elif self._adjustCameraMode == 1:
                rotateSpeed = 0.010
                deltaMouse = mathutil.Vec2(mouseEvent.localPos().x(), mouseEvent.localPos().y()) - self._adjustCameraStartMousePos

                # Remove pivot
                self._cameraTransform = cgmath.Mat44(self._adjustCameraStartCamera) * cgmath.Mat44.translate(-self._adjustCameraPivot[0], -self._adjustCameraPivot[1], -self._adjustCameraPivot[2])

                # Rotate
                self._cameraTransform = self._cameraTransform * cgmath.Mat44.rotateY(deltaMouse[0] * rotateSpeed)
                self._cameraTransform = self._cameraTransform * self.axisAngle(cgmath.Vec3(1.0, 0.0, 0.0) * self._cameraTransform, deltaMouse[1] * -rotateSpeed)

                # Add pivot back
                self._cameraTransform = cgmath.Mat44(self._cameraTransform) * cgmath.Mat44.translate(self._adjustCameraPivot[0], self._adjustCameraPivot[1], self._adjustCameraPivot[2])

            # Zooming?
            elif self._adjustCameraMode == 2:
                zoomSpeed = 0.025
                deltaMouse = mathutil.Vec2(mouseEvent.localPos().x(), mouseEvent.localPos().y()) - self._adjustCameraStartMousePos
                self._cameraTransform = cgmath.Mat44.translate(0.0, 0.0, deltaMouse[1] * zoomSpeed) * self._adjustCameraStartCamera

            self.cameraChanged.emit(self._cameraTransform)

        # Dragging a translation modifier axis?
        elif self._modifierMode == ModifierMode.TRANSLATE and self._modifierAxis != ModifierAxis.NONE:
            deltaMouse = self._convertMousePosToScreenPos(mouseEvent.localPos().x(), mouseEvent.localPos().y()) - self._modifyStartMouseScreenPos
            if self._modifierAxis == ModifierAxis.X:
                axisDir = cgmath.Vec3(1.0,0.0,0.0)
            elif self._modifierAxis == ModifierAxis.Y:
                axisDir = cgmath.Vec3(0.0,1.0,0.0)
            else:
                axisDir = cgmath.Vec3(0.0,0.0,1.0)

            screenDir = self._getModifierAxisScreenDir(axisDir)
            delta = screenDir[0]*deltaMouse[0] + screenDir[1]*deltaMouse[1]

            for node in self._currentModelNodes:
                node.translation = axisDir * delta + self._modifyStartModelTranslation[node]

        # Dragging a rotation modifier axis?
        elif self._modifierMode == ModifierMode.ROTATE and self._modifierAxis != ModifierAxis.NONE:
            deltaMouse = self._convertMousePosToScreenPos(mouseEvent.localPos().x(), mouseEvent.localPos().y()) - self._modifyStartMouseScreenPos
            amount = deltaMouse[0]

            if self._modifierAxis == ModifierAxis.X:
                rot = cgmath.Mat44.rotateX(amount)
            elif self._modifierAxis == ModifierAxis.Y:
                rot = cgmath.Mat44.rotateY(amount)
            else:
                rot = cgmath.Mat44.rotateZ(amount)

            for node in self._currentModelNodes:
                node.rotation = (rot * self._modifyStartModelRotationMatrix[node]).eulerXYZ()

        # Dragging a scale modifier axis?
        elif self._modifierMode == ModifierMode.SCALE_NONUNIFORM and self._modifierAxis != ModifierAxis.NONE:
            deltaMouse = self._convertMousePosToScreenPos(mouseEvent.localPos().x(), mouseEvent.localPos().y()) - self._modifyStartMouseScreenPos
            if self._modifierAxis == ModifierAxis.X:
                axisDir = cgmath.Vec3(1.0,0.0,0.0)
            elif self._modifierAxis == ModifierAxis.Y:
                axisDir = cgmath.Vec3(0.0,1.0,0.0)
            else:
                axisDir = cgmath.Vec3(0.0,0.0,1.0)

            screenDir = self._getModifierAxisScreenDir(axisDir)
            delta = screenDir[0]*deltaMouse[0] + screenDir[1]*deltaMouse[1]

            for node in self._currentModelNodes:
                node.size = axisDir * delta * 0.5 + self._modifyStartModelSize[node]

        # Selecting nodes?
        elif self._selecting:
            self._selectCurrentMouseScreenPos = self._convertMousePosToScreenPos(mouseEvent.localPos().x(), mouseEvent.localPos().y())

        self.update()

    def mouseReleaseEvent(self, mouseEvent):
        super(ModelerViewport, self).mouseReleaseEvent(mouseEvent)

        # Panning/Rotating/Zooming?
        if self._adjustingCamera:
            # Panning?
            if self._adjustCameraMode == 0:
                self._adjustingCamera = (mouseEvent.buttons() & Qt.MiddleButton)
            # Rotating?
            elif self._adjustCameraMode == 1:
                self._adjustingCamera = (mouseEvent.buttons() & Qt.LeftButton)
            # Zooming?
            elif self._adjustCameraMode == 2:
                self._adjustingCamera = (mouseEvent.buttons() & Qt.RightButton)

        # Adjusting modifier?
        elif self._modifierMode != ModifierMode.SELECT and self._modifierAxis != ModifierAxis.NONE:
            self._modifierAxis = ModifierAxis.NONE
            self.update()

        # Selecting?
        elif self._selecting:
            self._selecting = False

            # Create rect with P0 is min (bottom left) and P1 is max (top right)
            rectP0 = mathutil.Vec2(min(self._selectStartMouseScreenPos[0], self._selectCurrentMouseScreenPos[0]), min(self._selectStartMouseScreenPos[1], self._selectCurrentMouseScreenPos[1]))
            rectP1 = mathutil.Vec2(max(self._selectStartMouseScreenPos[0], self._selectCurrentMouseScreenPos[0]), max(self._selectStartMouseScreenPos[1], self._selectCurrentMouseScreenPos[1]))

            # Enforce minimum size of selection rect
            boxSelect = False
            minRectSize = 2.0*math.sqrt(self._minMouseClickDistSq)
            rectSize = rectP1 - rectP0
            if abs(rectSize[0]) < minRectSize:
                rectP0[0] -= 0.5*(minRectSize - rectSize[0])
                rectP1[0] += 0.5*(minRectSize - rectSize[0])
            else:
                boxSelect = True
            if abs(rectSize[1]) < minRectSize:
                rectP0[1] -= 0.5*(minRectSize - rectSize[1])
                rectP1[1] += 0.5*(minRectSize - rectSize[1])
            else:
                boxSelect = True

            newSelectedNodes = self._getModelNodesUnderScreenRect(rectP0, rectP1)

            modifiers = QApplication.keyboardModifiers()

            # By holding Shift, the selection is extended instead of replaced.
            # (And by holding shift and clicking on a single item, that item can be excluded as well)
            if modifiers == Qt.ShiftModifier:
                if boxSelect:
                    for node in self._currentModelNodes:
                        if node not in newSelectedNodes:
                            newSelectedNodes.append(node)
                else:
                    clickedNodes = newSelectedNodes
                    newSelectedNodes = list(self._currentModelNodes)
                    for clickedNode in clickedNodes:
                        if clickedNode in newSelectedNodes:
                            newSelectedNodes.remove(clickedNode)
                        else:
                            newSelectedNodes.append(clickedNode)

            self.selectedModelNodesChanged.emit(self._currentModel, newSelectedNodes)
            self.update()


    def eventFilter(self, watched, event):
        if event.type() == QEvent.ShortcutOverride:
            if event.key() == Qt.Key_Q or \
                event.key() == Qt.Key_W or \
                event.key() == Qt.Key_E or \
                event.key() == Qt.Key_R or \
                event.key() == Qt.Key_F or \
                event.key() == Qt.Key_Escape:
                # Disable all shortcuts for these keys, as we really want to handle these ourselves.
                # (We have some overrides for these at the app level)
                self.keyPressEvent(event)
                return True

        return super(ModelerViewport, self).eventFilter(watched, event)

    def keyPressEvent(self, event):
        super(ModelerViewport, self).keyPressEvent(event)

        if event.key() == Qt.Key_Q or event.key() == Qt.Key_Escape:
            self.setModifierModeSelect()
        elif event.key() == Qt.Key_W:
            self.setModifierModeTranslate()
        elif event.key() == Qt.Key_E:
            self.setModifierModeRotate()
        elif event.key() == Qt.Key_R:
            self.setModifierModeScale()
        elif event.key() == Qt.Key_F:
            self.centerView()

    def setCurrentModelAndNodes(self, model, nodes):
        self._currentModel = model
        self._currentModelNodes = nodes
        self.update()

    def onModelChanged(self, model):
        if model == self._currentModel:
            self.update()

    def setModifierModeSelect(self):
        if self._modifierMode != ModifierMode.SELECT:
            self._modifierMode = ModifierMode.SELECT
            self.modifierModeChanged.emit(self._modifierMode)
            self.update()

    def setModifierModeTranslate(self):
        if self._modifierMode != ModifierMode.TRANSLATE:
            self._modifierMode = ModifierMode.TRANSLATE
            self._modifierAxis = ModifierAxis.NONE
            self.modifierModeChanged.emit(self._modifierMode)
            self.update()

    def setModifierModeRotate(self):
        if self._modifierMode != ModifierMode.ROTATE:
            self._modifierMode = ModifierMode.ROTATE
            self._modifierAxis = ModifierAxis.NONE
            self.modifierModeChanged.emit(self._modifierMode)
            self.update()

    def setModifierModeScale(self):
        if self._modifierMode != ModifierMode.SCALE_NONUNIFORM:
            self._modifierMode = ModifierMode.SCALE_NONUNIFORM
            self._modifierAxis = ModifierAxis.NONE
            self.modifierModeChanged.emit(self._modifierMode)
            self.update()

    def saveState(self):
        # save user camera position per scene
        userFile = currentProjectFilePath().ensureExt('user')
        if userFile.exists():
            xUser = parseXMLWithIncludes(userFile)
        else:
            xUser = cElementTree.Element('user')

        xMod = xUser.find('Modeler')
        if xMod is None:
            xMod = cElementTree.SubElement(xUser, 'Modeler')

        if not self._currentModel is None:
            xMod.set('CurrentModel', str(self._models.models.index(self._currentModel)))

        xMod.set('CameraTransform', ','.join(map(str, self._cameraTransform[:])))
        xMod.set('CameraPivot', ','.join(map(str, self._cameraPivot[:])))

        with userFile.edit() as fh:
            fh.write(toPrettyXml(xUser))

    def loadState(self):
        # save user camera position per scene
        userFile = currentProjectFilePath().ensureExt('user')
        if not userFile.exists():
            return

        xUser = parseXMLWithIncludes(userFile)
        if xUser is None:
            return

        xMod = xUser.find('Modeler')
        if xMod is None:
            return

        if 'CurrentModel' in xMod.attrib:
            currentModelIndex = int(xMod.attrib['CurrentModel'])
        else:
            currentModelIndex = -1
        if currentModelIndex >= 0 and currentModelIndex < len(self._models.models):
            self.selectedModelNodesChanged.emit(self._models.models[currentModelIndex], None)
        else:
            self.selectedModelNodesChanged.emit(None, None)

        ct = list(map(float, xMod.attrib['CameraTransform'].split(',')))
        self._cameraTransform = cgmath.Mat44(ct[0],ct[1],ct[2],ct[3],ct[4],ct[5],ct[6],ct[7],ct[8],ct[9],ct[10],ct[11],ct[12],ct[13],ct[14],ct[15])

        ct = list(map(float, xMod.attrib['CameraPivot'].split(',')))
        self._cameraPivot = cgmath.Vec3(ct[0], ct[1], ct[2])

        self.update()


class Modeler(QWidget):
    def __init__(self, models):
        super(Modeler, self).__init__()

        self.setLayout(vlayout())

        toolbar = hlayout()

        self._viewport = ModelerViewport(models)
        self._viewport.modifierModeChanged.connect(self._modifierModeChanged)

        self._selectButton = QPushButton(icons.get('icons8-cursor-50'), '')
        self._selectButton.clicked.connect(self._viewport.setModifierModeSelect)
        self._selectButton.setIconSize(QSize(24, 24))
        self._selectButton.setToolTip('Select')
        self._selectButton.setStatusTip('Select')
        self._selectButton.setCheckable(True)
        self._selectButton.setChecked(True)
        toolbar.addWidget(self._selectButton)

        self._translateButton = QPushButton(icons.get('icons8-move-50'), '')
        self._translateButton.clicked.connect(self._viewport.setModifierModeTranslate)
        self._translateButton.setIconSize(QSize(24, 24))
        self._translateButton.setToolTip('Translate')
        self._translateButton.setStatusTip('Translate')
        self._translateButton.setCheckable(True)
        toolbar.addWidget(self._translateButton)

        self._rotateButton = QPushButton(icons.get('icons8-3d-rotate-50'), '')
        self._rotateButton.clicked.connect(self._viewport.setModifierModeRotate)
        self._rotateButton.setIconSize(QSize(24, 24))
        self._rotateButton.setToolTip('Rotate')
        self._rotateButton.setStatusTip('Rotate')
        self._rotateButton.setCheckable(True)
        toolbar.addWidget(self._rotateButton)

        self._scaleButton = QPushButton(icons.get('icons8-scale-tool-50'), '')
        self._scaleButton.clicked.connect(self._viewport.setModifierModeScale)
        self._scaleButton.setIconSize(QSize(24, 24))
        self._scaleButton.setToolTip('Scale')
        self._scaleButton.setStatusTip('Scale')
        self._scaleButton.setCheckable(True)
        toolbar.addWidget(self._scaleButton)

        toolbar.addSpacing(10)

        centerViewButton = QPushButton(icons.get('icons8-zoom-to-extents-50'), '')
        centerViewButton.clicked.connect(self._viewport.centerView)
        centerViewButton.setIconSize(QSize(24, 24))
        centerViewButton.setToolTip('Center View (f)')
        centerViewButton.setStatusTip('Center View (f)')
        toolbar.addWidget(centerViewButton)

        toolbar.addStretch(1)

        self.layout().addLayout(toolbar)
        self.layout().addWidget(self._viewport)
        self.layout().setStretch(1, 1)

    @property
    def viewport(self):
        return self._viewport

    def _modifierModeChanged(self, newMode):
        self._selectButton.setChecked(newMode == ModifierMode.SELECT)
        self._translateButton.setChecked(newMode == ModifierMode.TRANSLATE)
        self._rotateButton.setChecked(newMode == ModifierMode.ROTATE)
        self._scaleButton.setChecked(newMode == ModifierMode.SCALE_NONUNIFORM)

