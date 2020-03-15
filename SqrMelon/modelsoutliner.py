import cgmath
from qtutil import *
from models import *


class ModelsModel(QAbstractItemModel):
    def __init__(self, models):
        super(ModelsModel, self).__init__()

        self._models = models

    def rowCount(self, parent=QModelIndex()):
        # a row per model
        if not parent.isValid():
            return len(self._models.models)

        # a row per model's node
        data = parent.internalPointer()
        if isinstance(data, Model):
            return len(data.nodes)

        return 0

    def columnCount(self, parent = QModelIndex()):
        return 1

    def data(self, index, role):
        if not index.isValid():
            return None

        obj = index.internalPointer()

        if role == Qt.DisplayRole:
            return obj.name

        if role == Qt.UserRole:
            return obj

        return None

    def index(self, row, column, parent = QModelIndex()):
        if not parent.isValid():
            return self.createIndex(row, column, self._models.models[row])
        else:
            model = parent.internalPointer()
            return self.createIndex(row, column, model.nodes[row])

    def parent(self, child):
        if child.isValid():
            data = child.internalPointer()
            if isinstance(data, ModelNodeBase):
                model = data.model
                return self.createIndex(self._models.models.index(model), 0, model)

        return QModelIndex()





class ModelsOutliner(QWidget):
    """
    Models outliner window
    """

    selectedModelChanged = pyqtSignal(object)

    def __init__(self, models):
        super(ModelsOutliner, self).__init__()
        self.setLayout(vlayout())

        self._model = ModelsModel(models)

        self._tree = QTreeView(self)
        self._tree.setModel(self._model)
        self._tree.setHeaderHidden(True)

        self.layout().addWidget(self._tree)

        self._tree.selectionModel().selectionChanged.connect(self._onSelectionChanged)

    def _onSelectionChanged(self, selected, deselected):
        selectedModel = None

        # Find out which model is selected
        for index in selected.indexes():
            data = index.data(Qt.UserRole)
            if isinstance(data, Model):
                selectedModel = data
                break
            elif isinstance(data, ModelNodeBase):
                selectedModel = data.model
                break

        self.selectedModelChanged.emit(selectedModel)

