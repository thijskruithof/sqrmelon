from qtutil import *


# class Model(object):
#     def __init__(self):
#         self._name = "Unnamed"




class ModelsOutliner(QWidget):
    """
    Models outliner window
    """
    def __init__(self):
        super(ModelsOutliner, self).__init__()
        self.setLayout(vlayout())

        self._tree = QTreeView(self)

        self.layout().addWidget(self._tree)
