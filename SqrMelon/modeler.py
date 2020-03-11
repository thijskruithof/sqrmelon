import functools

from qtutil import *
from OpenGL.GL import *
from OpenGL.GLU import *

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

    def initializeGL(self):
        glClearColor(0.7, 0.7, 0.7, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        glClearDepth(1.0)
        glDepthFunc(GL_LESS)
        glEnable(GL_DEPTH_TEST)
        glShadeModel(GL_SMOOTH)

        vertex_array_id = glGenVertexArrays(1)
        glBindVertexArray(vertex_array_id)

        # A triangle
        vertex_data = [-1, -1, 0,
                       1, -1, 0,
                       0, 1, 0]

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
                void main(){
                  gl_Position.xyz = vertexPosition_modelspace;
                  gl_Position.w = 1.0;
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



    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glDrawArrays(GL_TRIANGLES, 0, 3)

        # glLoadIdentity()
        # glTranslatef(-2.5, 0.5, -6.0)
        # glColor3f( 1.0, 1.5, 0.0 )
        # glPolygonMode(GL_FRONT, GL_FILL)
        # glBegin(GL_TRIANGLES)
        # glVertex3f(2.0,-1.2,0.0)
        # glVertex3f(2.6,0.0,0.0)
        # glVertex3f(2.9,-1.2,0.0)
        # glEnd()
        # glFlush()
        # glClear(GL_COLOR_BUFFER_BIT)
        #
        # glMatrixMode(GL_PROJECTION)
        # glLoadIdentity()
        # glOrtho(-0.5, +0.5, -0.5, +0.5, 4.0, 15.0)
        # glMatrixMode(GL_MODELVIEW)


    def __onResize(self):
        self.repaint()

    def resizeGL(self, w, h):
        side = min(w, h);
        glViewport((w - side) / 2, (h - side) / 2, side, side)

        self.__onResize()