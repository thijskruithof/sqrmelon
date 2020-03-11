import functools

from qtutil import *
from OpenGL.GL import *
from OpenGL.GLU import *
import cgmath
import mathutil

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

        self._camera = cgmath.Mat44.translate(0, 0, 9)

        self._model =  cgmath.Mat44()
        self._view = cgmath.Mat44()

        self._panning = False
        self._zooming = False

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

        # A triangle
        vertex_data = [-1, -1, 10.0,
                       1, -1, 10.0,
                       0, 1, 10.0]

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
                out vec3 color;
                void main(){
                  color = vec3(1,0,0);
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
                log.error(logmsg)
                sys.exit(10)

            glAttachShader(program_id, shader_id)
            shader_ids.append(shader_id)

        glLinkProgram(program_id)

        # check if linking was successful
        result = glGetProgramiv(program_id, GL_LINK_STATUS)
        info_log_len = glGetProgramiv(program_id, GL_INFO_LOG_LENGTH)
        if info_log_len:
            logmsg = glGetProgramInfoLog(program_id)
            log.error(logmsg)
            sys.exit(11)

        glUseProgram(program_id)

        self._shader_program_id = program_id


    def paintGL(self):
        # view = inverse of camera, which is:
        self._view = \
            cgmath.Mat44.translate(-self._camera[12], -self._camera[13], -self._camera[14]) * \
            cgmath.Mat44(self._camera[0], self._camera[4], self._camera[8], 0, self._camera[1], self._camera[5], self._camera[9], 0, self._camera[2], self._camera[6], self._camera[10], 0, 0,0,0, 1)

        mvp = (self._model * self._view) * self._projection

        # Set MVP
        mvp_uni = glGetUniformLocation(self._shader_program_id, "MVP")
        glUniformMatrix4fv(mvp_uni, 1, False, (ctypes.c_float * 16)(*mvp))

        # Draw some triangles
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glDrawArrays(GL_TRIANGLES, 0, 3)

    def __onResize(self):
        self.repaint()

    def resizeGL(self, w, h):
        self._projection = cgmath.Mat44.scale(1, 1, -1) * cgmath.Mat44.perspective(1.74532925, w / h, 0.1, 100.0)

        glViewport(0, 0, w, h)

        self.__onResize()

    def mousePressEvent(self, mouseEvent):
        super(Modeler, self).mousePressEvent(mouseEvent)

        # Panning?
        if mouseEvent.buttons() & Qt.LeftButton:
            self._panning = True
            self._panStartMousePos = mathutil.Vec2(mouseEvent.posF().x(), mouseEvent.posF().y())
            self._panStartCamera = self._camera

        # Zooming?
        if mouseEvent.buttons() & Qt.RightButton:
            self._zooming = True
            self._zoomStartMousePos = mathutil.Vec2(mouseEvent.posF().x(), mouseEvent.posF().y())
            self._zoomStartCamera = self._camera

    def mouseMoveEvent(self, mouseEvent):
        super(Modeler, self).mouseMoveEvent(mouseEvent)

        if not self._panning and not self._zooming:
            return

        # Panning?
        if self._panning:
            panSpeed = 0.025
            deltaMouse = mathutil.Vec2(mouseEvent.posF().x(), mouseEvent.posF().y()) - self._panStartMousePos
            self._camera = self._panStartCamera * cgmath.Mat44.translate(deltaMouse[0] * -panSpeed, deltaMouse[1] * panSpeed, 0)
        # Zooming?
        elif self._zooming:
            zoomSpeed = 0.025
            deltaMouse = mathutil.Vec2(mouseEvent.posF().x(), mouseEvent.posF().y()) - self._zoomStartMousePos
            self._camera = self._zoomStartCamera * cgmath.Mat44.translate(0, 0, deltaMouse[1] * zoomSpeed)

        self.repaint()

    def mouseReleaseEvent(self, mouseEvent):
        super(Modeler, self).mouseReleaseEvent(mouseEvent)

        # Panning?
        if not (mouseEvent.buttons() & Qt.LeftButton):
            self._panning = False

        # Zooming?
        if not (mouseEvent.buttons() & Qt.RightButton):
            self._zooming = False