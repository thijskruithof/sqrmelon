"""
Utility that wraps OpenGL textures, frame buffers and render buffers.
"""
from pycompat import *
import contextlib
from OpenGL.GL import *
from qtutil import *


class Texture(object):
    """
    Creates a GL texture2D.
    The static members below are all color formats at this point in time &
    make it only 1 variable instead of 3.

    Call use() to bind the texture with Gl.
    """

    FORMAT_RGBA8_UNorm = QOpenGLTexture.RGBA8_UNorm
    FORMAT_R32F = QOpenGLTexture.R32F
    FORMAT_RGBA32F = QOpenGLTexture.RGBA32F
    FORMAT_D32F = QOpenGLTexture.D32F


    def __init__(self, format, width, height, tile=True, img=None):
        """
        :param format: One of the above static members describing the pixel format.
        :param int width: Width in pixels
        :param int height: Height in pixels
        :param bool tile: Sets GL_CLAMP or GL_REPEAT accordingly.
        :param QImage img: An image to upload to the texture. (Should be a QImage)
        """
        self._width = width
        self._height = height

        if img is None:
            self._tex = QOpenGLTexture(QOpenGLTexture.Target2D)
            self._tex.setFormat(format)
            self._tex.setSize(width, height, 1)
            self._tex.allocateStorage()
        else:
            self._tex = QOpenGLTexture(img, QOpenGLTexture.MipMapGeneration.GenerateMipMaps.DontGenerateMipMaps)

        if not tile:
            self._tex.setWrapMode(QOpenGLTexture.ClampToEdge)
        else:
            self._tex.setWrapMode(QOpenGLTexture.Repeat)

    def id(self):
        return self._tex.textureId()

    def use(self):
        self._tex.bind()

    def width(self):
        return self._width

    def height(self):
        return self._height

    def save(self, filePath, ch=None):
        if filePath.hasExt('.r32'):
            import struct
            # heightfield export
            pixels = self._width * self._height
            buffer = (ctypes.c_float * pixels)()
            glGetTexImage(GL_TEXTURE_2D, 0, GL_RED, GL_FLOAT, buffer)
            with filePath.edit(flag='wb') as fh:
                fh.write(struct.pack('%sf' % pixels, *buffer))
            return
        from qtutil import QImage
        pixels = self._width * self._height
        buffer = (ctypes.c_ubyte * (pixels * 4))()
        mirror = (ctypes.c_ubyte * (pixels * 4))()
        glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_UNSIGNED_BYTE, buffer)
        for i in range(0, pixels * 4, 4):
            if ch is None:
                mirror[i:i + 4] = (buffer[i + 2], buffer[i + 1], buffer[i], buffer[i + 3])
            else:
                mirror[i:i + 4] = (buffer[i + ch], buffer[i + ch], buffer[i + ch], 255)
        QImage(mirror, self._width, self._height, QImage.Format_ARGB32).save(filePath)


class Texture3D(object):
    RGBA32F = GL_RGBA32F, GL_RGBA, GL_FLOAT

    def __init__(self, channels, resolution, tile=True, data=None):
        # for channels refer to the options in Texture
        self._width = resolution
        self._height = resolution
        self._depth = resolution

        self._channels = channels

        self._id = glGenTextures(1)

        self.use()
        glTexImage3D(GL_TEXTURE_3D, 0, channels[0], resolution, resolution, resolution, 0, channels[1], channels[2], None)
        glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        if not tile:
            glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

    def setSlicePixels(self, sliceIndex, data2d):
        self.use()
        glTexSubImage3D(GL_TEXTURE_3D, 0,  0,0, sliceIndex, self._width, self._height, 1, self._channels[1], self._channels[2], data2d)

    def use(self):
        glBindTexture(GL_TEXTURE_3D, self._id)

    def width(self):
        return self._width

    def height(self):
        return self._height

    def depth(self):
        return self._depth

    def id(self):
        return self._id


class Cubemap(object):

    def __init__(self, channels, size, contents=None):
        self.__size = size
        self.__id = glGenTextures(1)

        self.use()
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        data = None
        for i in range(6):
            if contents is not None:
                data = contents[i]
            glTexImage2D(GL_TEXTURE_CUBE_MAP_POSITIVE_X + i, 0, channels[0], size, size, 0, channels[1], channels[2], data)

    def id(self):
        return self.__id

    def use(self):
        glBindTexture(GL_TEXTURE_CUBE_MAP, self.__id)

    def size(self):
        return self.__size


class RenderBuffer(object):
    R8 = GL_R8
    R8UI = GL_R8UI
    R8I = GL_R8I
    R16UI = GL_R16UI
    R16I = GL_R16I
    R32UI = GL_R32UI
    R32I = GL_R32I
    RG8 = GL_RG8
    RG8UI = GL_RG8UI
    RG8I = GL_RG8I
    RG16UI = GL_RG16UI
    RG16I = GL_RG16I
    RG32UI = GL_RG32UI
    RG32I = GL_RG32I
    RGB8 = GL_RGB8
    RGB565 = GL_RGB565
    RGBA8 = GL_RGBA8
    SRGB8_ALPHA8 = GL_SRGB8_ALPHA8
    RGB5_A1 = GL_RGB5_A1
    RGBA4 = GL_RGBA4
    RGB10_A2 = GL_RGB10_A2
    RGBA8UI = GL_RGBA8UI
    RGBA8I = GL_RGBA8I
    RGB10_A2UI = GL_RGB10_A2UI
    RGBA16UI = GL_RGBA16UI
    RGBA16I = GL_RGBA16I
    RGBA32I = GL_RGBA32I
    RGBA32UI = GL_RGBA32UI
    DEPTH_COMPONENT16 = GL_DEPTH_COMPONENT16
    DEPTH_COMPONENT24 = GL_DEPTH_COMPONENT24
    DEPTH_COMPONENT32F = GL_DEPTH_COMPONENT32F
    DEPTH24_STENCIL8 = GL_DEPTH24_STENCIL8
    DEPTH32F_STENCIL8 = GL_DEPTH32F_STENCIL8
    STENCIL_INDEX8 = GL_STENCIL_INDEX8
    # common aliases
    FLOAT_DEPTH = GL_DEPTH_COMPONENT32F
    FLOAT_DEPTH_STENCIL = GL_DEPTH32F_STENCIL8

    def __init__(self, channels, width, height):
        self.__id = glGenRenderbuffers(1)
        self.use()
        glRenderbufferStorage(GL_RENDERBUFFER, channels, width, height)

    def id(self):
        return self.__id

    def use(self):
        glBindRenderbuffer(GL_RENDERBUFFER, self.__id)


class FrameBuffer(object):
    """
    Utility to set up a frame buffer and manage its color & render buffers.

    Call use() to render into the buffer and automatically bind all the color buffers as well as adjust glViewport.
    """

    def __init__(self, width, height):
        self.__id = glGenFramebuffers(1)
        self.__stats = [None]
        self.__buffers = []
        assert isinstance(width, int)
        assert isinstance(height, int)
        self.__width = width
        self.__height = height

    def width(self):
        return self.__width

    def height(self):
        return self.__height

    def use(self, soft=False):
        glBindFramebuffer(GL_FRAMEBUFFER, self.__id)
        if soft:
            return
        glDrawBuffers(len(self.__buffers), self.__buffers)
        glViewport(0, 0, self.__width, self.__height)

    @contextlib.contextmanager
    def useInContext(self, screenSize, soft=False):
        self.use(soft)
        yield
        FrameBuffer.clear()
        glViewport(0, 0, *screenSize)

    @staticmethod
    def clear():
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

    def id(self):
        return self.__id

    def addTexture(self, texture):
        # TODO: check if given texture has right channels (depth, rgba, depth-stencil), etc
        assert (texture.width() == self.__width)
        assert (texture.height() == self.__height)
        bid = GL_COLOR_ATTACHMENT0 + len(self.__stats)
        self.__stats.append(texture)
        self.__buffers.append(bid)
        self.use(True)
        if isinstance(texture, RenderBuffer):
            glFramebufferRenderbuffer(GL_FRAMEBUFFER, bid, GL_RENDERBUFFER, texture.id())
        else:  # buffer is a texture
            glFramebufferTexture2D(GL_FRAMEBUFFER, bid, GL_TEXTURE_2D, texture.id(), 0)

    def initDepthStencil(self, depthStencil):
        # TODO: check if given texture has right channels DEPTH_STENCIL texture
        if self.__stats[0] is not None:
            raise RuntimeError('FrameBuffer already has a depth, stencil or depth_stencil attachment.')
        self.use(True)
        if isinstance(depthStencil, RenderBuffer):
            glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_RENDERBUFFER, depthStencil.id())
        else:  # buffer is a texture
            glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, depthStencil.id(), 0)
        self.__stats[0] = depthStencil

    def initDepth(self, depth):
        # TODO: check if given texture has right channels, DEPTH texture
        if self.__stats[0] is not None:
            raise RuntimeError('FrameBuffer already has a depth, stencil or depth_stencil attachment.')
        self.use(True)
        if isinstance(depth, RenderBuffer):
            glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, depth.id())
        else:  # buffer is a texture
            glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, depth.id(), 0)
        self.__stats[0] = depth

    def initStencil(self, stencil):
        # TODO: check if given texture has right channels, STENCIL texture
        if self.__stats[0] is not None:
            raise RuntimeError('FrameBuffer already has a depth, stencil or depth_stencil attachment.')
        self.use(True)
        if isinstance(stencil, RenderBuffer):
            glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_STENCIL_ATTACHMENT, GL_RENDERBUFFER, stencil.id())
        else:  # buffer is a texture
            glFramebufferTexture2D(GL_FRAMEBUFFER, GL_STENCIL_ATTACHMENT, GL_TEXTURE_2D, stencil.id(), 0)
        self.__stats[0] = stencil

    def depth(self):
        return self.__stats[0]

    def textures(self):
        for i in range(1, len(self.__stats)):
            yield self.__stats[i]
