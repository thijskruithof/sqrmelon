import functools

from qtutil import *
from OpenGL.GL import *
from OpenGL.GLU import *
import cgmath
import mathutil
import math

class Modeler(QGLWidget):
    """
    Modeler window
    """
    def __init__(self):

        # We found that not setting a version in Ubunto didn't work
        glFormat = QGLFormat()
        glFormat.setVersion(4, 1)
        glFormat.setProfile(QGLFormat.CoreProfile)
        glFormat.setDefaultFormat(glFormat)

        super(Modeler, self).__init__()
        self.setLayout(vlayout())

        self._camera = cgmath.Mat44.translate(0, 1, 0)

        self._model =  cgmath.Mat44()
        self._view = cgmath.Mat44()

        self._adjustingCamera = False
        self._adjustCameraMode = 0

    def initializeGL(self):
        glClearColor(0.7, 0.7, 0.7, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        glClearDepth(1.0)
        glDepthFunc(GL_LESS)
        #glEnable(GL_DEPTH_TEST)
        glDisable(GL_DEPTH_TEST)
        glShadeModel(GL_SMOOTH)
        glDisable(GL_CULL_FACE)

        vertex_array_id = glGenVertexArrays(1)
        glBindVertexArray(vertex_array_id)

        # A grid in XZ plane
        vertex_data = []
        numGridLines = 20
        gridSpacing = 0.25

        for i in range(-numGridLines, numGridLines+1):
            # line on X axis
            vertex_data.append(i*gridSpacing)
            vertex_data.append(0)
            vertex_data.append(-numGridLines*gridSpacing)
            vertex_data.append(i*gridSpacing)
            vertex_data.append(0)
            vertex_data.append(numGridLines*gridSpacing)
            # line on Z axis
            vertex_data.append(-numGridLines*gridSpacing)
            vertex_data.append(0)
            vertex_data.append(i * gridSpacing)
            vertex_data.append(numGridLines * gridSpacing)
            vertex_data.append(0)
            vertex_data.append(i * gridSpacing)

        self._numGridVertices = (numGridLines*2+1)*4

        # vertex_data = [-1, -1, 10.0,
        #                1, -1, 10.0,
        #                1, -1, 10.0,
        #                0, 1, 10.0,
        #                0, 1, 10.0,
        #                -1, -1, 10.0]

        attr_id = 0  # No particular reason for 0,
        # but must match the layout location in the shader.

        vertex_buffer = glGenBuffers(1)

        glBindBuffer(GL_ARRAY_BUFFER, vertex_buffer)

        array_type = (GLfloat * len(vertex_data))
        glBufferData(GL_ARRAY_BUFFER,
                        len(vertex_data) * ctypes.sizeof(ctypes.c_float),
                        array_type(*vertex_data),
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
        self._view = \
            cgmath.Mat44.translate(-self._camera[12], -self._camera[13], -self._camera[14]) * \
            cgmath.Mat44(self._camera[0], self._camera[4], self._camera[8], 0, self._camera[1], self._camera[5], self._camera[9], 0, self._camera[2], self._camera[6], self._camera[10], 0, 0,0,0, 1)

        mvp = (self._model * self._view) * self._projection

        # Set MVP
        glUniformMatrix4fv( self._uniform_mvp, 1, False, (ctypes.c_float * 16)(*mvp))

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Draw grid
        glUniform4f(self._uniform_color, 0.5, 0.5, 0.5, 1.0)
        glDrawArrays(GL_LINES, 0, self._numGridVertices)

    def __onResize(self):
        self.repaint()

    def resizeGL(self, w, h):
        self._projection = cgmath.Mat44.scale(1, 1, -1) * cgmath.Mat44.perspective(1.74532925, w / h, 0.1, 100.0)

        glViewport(0, 0, w, h)

        self.__onResize()

    def mousePressEvent(self, mouseEvent):
        super(Modeler, self).mousePressEvent(mouseEvent)

        if self._adjustingCamera:
            return

        modifiers = QApplication.keyboardModifiers()
        if modifiers != Qt.AltModifier:
            return

        self._adjustingCamera = True
        self._adjustCameraStartMousePos = mathutil.Vec2(mouseEvent.posF().x(), mouseEvent.posF().y())
        self._adjustCameraStartCamera = self._camera

        # Panning?
        if mouseEvent.buttons() & Qt.MiddleButton:
            self._adjustCameraMode = 0
        # Rotating?
        elif mouseEvent.buttons() & Qt.LeftButton:
            self._adjustCameraMode = 1
        # Zooming?
        elif mouseEvent.buttons() & Qt.RightButton:
            self._adjustCameraMode = 2

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
#        return cgmath.Mat44(m00, m10, m20, 0, m01, m11, m21, 0, m02, m12, m22, 0, 0, 0, 0, 1)

    def mouseMoveEvent(self, mouseEvent):
        super(Modeler, self).mouseMoveEvent(mouseEvent)

        if not self._adjustingCamera:
            return

        # Panning?
        if self._adjustCameraMode == 0:
            panSpeed = 0.025
            deltaMouse = mathutil.Vec2(mouseEvent.posF().x(), mouseEvent.posF().y()) - self._adjustCameraStartMousePos
            self._camera = cgmath.Mat44.translate(deltaMouse[0] * -panSpeed, deltaMouse[1] * panSpeed, 0) *  self._adjustCameraStartCamera
        # Rotating?
        elif self._adjustCameraMode == 1:
            rotateSpeed = 0.010
            deltaMouse = mathutil.Vec2(mouseEvent.posF().x(), mouseEvent.posF().y()) - self._adjustCameraStartMousePos

            # Remove position
            self._camera = cgmath.Mat44(
                self._adjustCameraStartCamera[0], self._adjustCameraStartCamera[1], self._adjustCameraStartCamera[2], self._adjustCameraStartCamera[3],
                self._adjustCameraStartCamera[4], self._adjustCameraStartCamera[5], self._adjustCameraStartCamera[6], self._adjustCameraStartCamera[7],
                self._adjustCameraStartCamera[8], self._adjustCameraStartCamera[9], self._adjustCameraStartCamera[10], self._adjustCameraStartCamera[11],
                0,0,0,1)

            # Rotate
            self._camera = self._camera * cgmath.Mat44.rotateY(deltaMouse[0] * rotateSpeed)
            self._camera = self._camera * self.axisAngle(cgmath.Vec3(1, 0, 0) * self._camera, deltaMouse[1] * -rotateSpeed)

            # Add position back
            self._camera = cgmath.Mat44(
                self._camera[0], self._camera[1], self._camera[2],  self._camera[3],
                self._camera[4], self._camera[5], self._camera[6],  self._camera[7],
                self._camera[8], self._camera[9], self._camera[10], self._camera[11],
                self._adjustCameraStartCamera[12],self._adjustCameraStartCamera[13],self._adjustCameraStartCamera[14],1)

        # Zooming?
        elif self._adjustCameraMode == 2:
            zoomSpeed = 0.025
            deltaMouse = mathutil.Vec2(mouseEvent.posF().x(), mouseEvent.posF().y()) - self._adjustCameraStartMousePos
            self._camera = cgmath.Mat44.translate(0, 0, deltaMouse[1] * zoomSpeed) * self._adjustCameraStartCamera

        self.repaint()

    def mouseReleaseEvent(self, mouseEvent):
        super(Modeler, self).mouseReleaseEvent(mouseEvent)

        if not self._adjustingCamera:
            return

        # Panning?
        if self._adjustCameraMode == 0:
            self._adjustingCamera = (mouseEvent.buttons() & Qt.MiddleButton)
        # Rotating?
        elif self._adjustCameraMode == 1:
            self._adjustingCamera = (mouseEvent.buttons() & Qt.LeftButton)
        # Zooming?
        elif self._adjustCameraMode == 2:
            self._adjustingCamera = (mouseEvent.buttons() & Qt.RightButton)