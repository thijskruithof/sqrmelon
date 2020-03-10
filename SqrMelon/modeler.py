import functools

from qtutil import *
from OpenGL.GL import *

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
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        # glDepthMask(GL_TRUE)
        glClearColor(0.7, 0.7, 0.7, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT)

    def __onResize(self):
        self.repaint()

    def resizeGL(self, w, h):
        self.__onResize()