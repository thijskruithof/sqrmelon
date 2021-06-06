from math import degrees, radians
import functools
import time

import cgmath
import icons
from qtutil import *
from mathutil import addVec3, multVec3, rotateVec3
from scene import CameraTransform

class CameraControlMode:
    FREE = 0
    ANIMATION = 1
    MODELER = 2

class Camera(QWidget):
    """
    Input that shows editable camera position and angles (degrees).
    Additionally contains event handlers for 3D flying keyboard & mouse input.
    """
    MOVE_SPEEDS = (0.5, 5.0, 30.0)
    TURN_SPEEDS = (0.2, 0.8, 3.0)
    MOUSE_SPEED = 3.0

    MOVE_LUT = {Qt.Key_A: (-1.0, 0.0, 0.0),
                Qt.Key_D: (1.0, 0.0, 0.0),
                Qt.Key_Q: (0.0, 1.0, 0.0),
                Qt.Key_E: (0.0, -1.0, 0.0),
                Qt.Key_S: (0.0, 0.0, -1.0),
                Qt.Key_W: (0.0, 0.0, 1.0)}

    TURN_LUT = {Qt.Key_Up: (1.0, 0.0, 0.0),
                Qt.Key_Down: (-1.0, 0.0, 0.0),
                Qt.Key_Left: (0.0, -1.0, 0.0),
                Qt.Key_Right: (0.0, 1.0, 0.0),
                Qt.Key_Home: (0.0, 0.0, -1.0),
                Qt.Key_End: (0.0, 0.0, 1.0)}

    cameraChanged = pyqtSignal()

    def __init__(self, animator, animationEditor, timer):
        super(Camera, self).__init__()
        self.setLayout(hlayout())

        self._freeCameraControlButton = QPushButton(icons.get('icons8-video-camera-50'), '')
        self._freeCameraControlButton.clicked.connect(self._setFreeCameraControl)
        self._freeCameraControlButton.setCheckable(True)
        self._freeCameraControlButton.setIconSize(QSize(24, 24))
        self._freeCameraControlButton.setToolTip("Free")
        self._animationCameraControlButton = QPushButton(icons.get('icons8-line-chart-50'), '')
        self._animationCameraControlButton.clicked.connect(self._setAnimationCameraControl)
        self._animationCameraControlButton.setCheckable(True)
        self._animationCameraControlButton.setIconSize(QSize(24, 24))
        self._animationCameraControlButton.setToolTip("Animation curves")
        self._modelerCameraControlButton = QPushButton(icons.get('icons8-grid-50'), '')
        self._modelerCameraControlButton.clicked.connect(self._setModelerCameraControl)
        self._modelerCameraControlButton.setCheckable(True)
        self._modelerCameraControlButton.setIconSize(QSize(24, 24))
        self._modelerCameraControlButton.setToolTip("Modeler viewport")

        self.layout().addWidget(self._freeCameraControlButton)
        self.layout().addWidget(self._animationCameraControlButton)
        self.layout().addWidget(self._modelerCameraControlButton)
        self.layout().addSpacing(24)

        self._cameraControlMode = CameraControlMode.FREE
        self.toggleBetweenFreeAndAnimation()

        timer.timeChanged.connect(self.__copyAnim)
        copyAnim = QPushButton(QIcon(icons.get('Film-Refresh-48')), '')
        copyAnim.setToolTip('Copy anim')
        copyAnim.setStatusTip('Copy anim')
        self.__animator = animator
        self.__animationEditor = animationEditor
        self._timer = timer
        copyAnim.clicked.connect(self.copyAnim)
        self.layout().addWidget(copyAnim)
        copyAnim.setIconSize(QSize(24, 24))

        self.__keyStates = {Qt.Key_Shift: False, Qt.Key_Control: False}
        for key in Camera.MOVE_LUT:
            self.__keyStates[key] = False
        for key in Camera.TURN_LUT:
            self.__keyStates[key] = False
        self.__data = CameraTransform()
        self.__modelerCameraTransform = cgmath.Mat44()
        self.__inputs = []
        for i, value in enumerate(self.__data):
            s = DoubleSpinBox(value)
            s.setMinimumWidth(50)
            self.__inputs.append(s)
            if i in (3,4,5):
                s.setSingleStep(5)
            self.layout().addWidget(s)
            s.valueChanged.connect(functools.partial(self.__setData, i))
        self.__prevTime = None
        self.__appLoop = QTimer()
        self.__appLoop.timeout.connect(self.flyUpdate)
        self.__appLoop.start(1.0 / 15.0)
        self.__drag = None
        self.__dirty = False

    def insertKey(self):
        channels = 'uOrigin.x', 'uOrigin.y', 'uOrigin.z', 'uAngles.x', 'uAngles.y', 'uAngles.z'
        self.__animationEditor.setKey(channels, tuple(self.__data[:]))

    def forwardPositionKey(self):
        self.__animationEditor.setTransformKey(tuple(self.__data.translate))

    def forwardRotationKey(self):
        self.__animationEditor.setTransformKey(tuple(self.__data.rotate))

    def __copyAnim(self, *args):
        if self._cameraControlMode == CameraControlMode.ANIMATION:
            self.copyAnim()

    def copyAnim(self):
        data = self.__animator.evaluate(self._timer.time)
        if 'uOrigin' not in data or 'uAngles' not in data:
            return
        self.__data = CameraTransform(*(data['uOrigin'] + data['uAngles']))
        self.cameraChanged.emit()

    def setModelerCameraTransform(self, cameraTransform):
        self.__modelerCameraTransform = cameraTransform
        if self._cameraControlMode == CameraControlMode.MODELER:
            cameraTransformInv = cgmath.Mat44(cameraTransform)
            cameraTransformInv.inverse()
            angles = cameraTransformInv.eulerXYZ()
            self.__data = CameraTransform(cameraTransform[12], cameraTransform[13], cameraTransform[14], -angles[0], angles[1], -angles[2])
            self.cameraChanged.emit()

    def toggleBetweenFreeAndAnimation(self, *args):
        if self._cameraControlMode == CameraControlMode.ANIMATION:
            self._cameraControlMode = CameraControlMode.FREE
        else:
            self._cameraControlMode = CameraControlMode.ANIMATION

        self._refreshCameraControlButton()

    def _refreshCameraControlButton(self):
        self._freeCameraControlButton.setChecked(self._cameraControlMode == CameraControlMode.FREE)
        self._animationCameraControlButton.setChecked(self._cameraControlMode == CameraControlMode.ANIMATION)
        self._modelerCameraControlButton.setChecked(self._cameraControlMode == CameraControlMode.MODELER)

    def _setFreeCameraControl(self):
        self._cameraControlMode = CameraControlMode.FREE
        self._refreshCameraControlButton()

    def _setAnimationCameraControl(self):
        self._cameraControlMode = CameraControlMode.ANIMATION
        self._refreshCameraControlButton()

    def _setModelerCameraControl(self):
        self._cameraControlMode = CameraControlMode.MODELER
        self._refreshCameraControlButton()
        self.setModelerCameraTransform(self.__modelerCameraTransform)

    def __setData(self, index, value):
        """ Called from the UI, performing unit conversion on angles """
        if index in (3, 4, 5):
            value = radians(value)
        self.__data[index] = value
        self.cameraChanged.emit()

    def data(self):
        return self.__data

    def setData(self, *args):
        self.__data = CameraTransform(*args)

    def releaseAll(self):
        for key in self.__keyStates:
            self.__keyStates[key] = False
        self.__drag = None

    def camera(self):
        return tuple(self.__data)

    def setCamera(self, data):
        self.__data = CameraTransform(*data)

    def flyMouseStart(self, event):
        self.__drag = event.pos(), self.__data.rotate

    def flyMouseUpdate(self, event, size):
        if self.__drag is None:
            return
        delta = event.pos() - self.__drag[0]
        scale = (size.width() + size.height()) * 0.5
        ry = (delta.x() / scale) * Camera.MOUSE_SPEED
        rx = (delta.y() / scale) * Camera.MOUSE_SPEED
        if rx or ry:
            self.__data.rotate = (self.__drag[1][0] - rx,
                                  self.__drag[1][1] + ry,
                                  self.__data.rotate[2])
            self.__dirty = True

    def flyMouseEnd(self, event):
        self.__drag = None

    def flyKeyboardInput(self, keyEvent, state):
        if keyEvent.key() in self.__keyStates:
            self.__keyStates[keyEvent.key()] = state

    def flyUpdate(self):
        if self.__prevTime is None:
            self.__prevTime = time.time()
            return
        deltaTime = time.time() - self.__prevTime
        self.__prevTime = time.time()

        # track whether a key was pressed
        dirtyTranslate = False
        dirtyRotate = False

        speedId = 1 - int(self.__keyStates[Qt.Key_Control]) + int(self.__keyStates[Qt.Key_Shift])

        # compute move vector
        translate = (0.0, 0.0, 0.0)
        for key in Camera.MOVE_LUT:
            if not self.__keyStates[key]:
                continue
            dirtyTranslate = True
            translate = addVec3(translate, Camera.MOVE_LUT[key])

        # compute rotate angles
        for key in Camera.TURN_LUT:
            if not self.__keyStates[key]:
                continue
            dirtyRotate = True
            rotate = multVec3(Camera.TURN_LUT[key], deltaTime * Camera.TURN_SPEEDS[speedId])
            if rotate[0] or rotate[1] or rotate[2]:
                self.__data.rotate = addVec3(self.__data.rotate, rotate)

        # if no keys were pressed, we're done
        dirty = dirtyTranslate | dirtyRotate | self.__dirty
        self.__dirty = False
        if not dirty:
            return

        if dirtyTranslate:
            translate = multVec3(translate, deltaTime * Camera.MOVE_SPEEDS[speedId])
            self.__data.translate = addVec3(self.__data.translate, rotateVec3(translate, self.__data.rotate))

        for i in range(len(self.__data)):
            value = self.__data[i]
            if i in (3, 4, 5):
                value = degrees(value)
            self.__inputs[i].setValueSilent(value)
        self.cameraChanged.emit()
