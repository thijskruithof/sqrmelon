import cgmath
from qtutil import *
from models import *
import icons

class ModelsModel(QAbstractItemModel):
    def __init__(self, models):
        super(ModelsModel, self).__init__()

        self._models = models
        self._models.preNodeAddedToModel.connect(self._onPreNodeAddedToModel)
        self._models.postNodeAddedToModel.connect(self._onPostNodeAddedToModel)
        self._models.preNodeRemovedFromModel.connect(self._onPreNodeRemovedFromModel)
        self._models.postNodeRemovedFromModel.connect(self._onPostNodeRemovedFromModel)
        self._models.preModelAdded.connect(self._onPreModelAdded)
        self._models.postModelAdded.connect(self._onPostModelAdded)
        self._models.preModelRemoved.connect(self._onPreModelRemoved)
        self._models.postModelRemoved.connect(self._onPostModelRemoved)

    def _onPreModelAdded(self, model):
        self.beginInsertRows(QModelIndex(), len(self._models.models), len(self._models.models))

    def _onPostModelAdded(self, model):
        self.endInsertRows()

    def _onPreModelRemoved(self, model):
        modelRow = self._models.models.index(model)
        self.beginRemoveRows(QModelIndex(), modelRow, modelRow)

    def _onPostModelRemoved(self, model):
        self.endRemoveRows()

    def _onPreNodeAddedToModel(self, model, node):
        modelIndex = self.index(self._models.models.index(model), 0)
        self.beginInsertRows(modelIndex, len(model.nodes), len(model.nodes))

    def _onPostNodeAddedToModel(self, model, node):
        self.endInsertRows()

    def _onPreNodeRemovedFromModel(self, model, node):
        modelIndex = self.index(self._models.models.index(model), 0)
        nodeRow = model.nodes.index(node)
        self.beginRemoveRows(modelIndex, nodeRow, nodeRow)

    def _onPostNodeRemovedFromModel(self, model, node):
        self.endRemoveRows()

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
            if row >= 0 and row < len(self._models.models):
                return self.createIndex(row, column, self._models.models[row])
        else:
            model = parent.internalPointer()
            if row >= 0 and row < len(model.nodes):
                return self.createIndex(row, column, model.nodes[row])

        return QModelIndex()

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

        toolbar = hlayout()

        addModelButton = QPushButton(icons.get('Add Image-48'), '')
        addModelButton.clicked.connect(self._onAddModel)
        addModelButton.setIconSize(QSize(16, 16))
        addModelButton.setToolTip('Add model')
        addModelButton.setStatusTip('Add model')
        toolbar.addWidget(addModelButton)

        toolbar.addStretch(1)

        self._models = models
        self._model = ModelsModel(models)

        self._tree = QTreeView(self)
        self._tree.setModel(self._model)
        self._tree.setHeaderHidden(True)

        self.layout().addLayout(toolbar)
        self.layout().addWidget(self._tree)

        self._tree.selectionModel().selectionChanged.connect(self._onSelectionChanged)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._onContextMenu)

        self._contextMenuModel = QMenu()
        self._contextMenuModel.addAction(icons.get('box-48'), 'Add box').triggered.connect(self._onAddBox)
        self._contextMenuModel.addAction(icons.get('Delete Node-48'), 'Delete').triggered.connect(self._onDeleteModelOrNode)

        self._contextMenuModelNode = QMenu()
        self._contextMenuModelNode.addAction(icons.get('Delete Node-48'), 'Delete').triggered.connect(self._onDeleteModelOrNode)

    def _getSelectedModel(self):
        # Find out which model is selected
        index = self._tree.currentIndex()
        if (index is None) or not index.isValid():
            return None
        data = index.internalPointer()
        if isinstance(data, Model):
            return data
        if isinstance(data, ModelNodeBase):
            return data.model
        return None

    def _onSelectionChanged(self, selected, deselected):
        self.selectedModelChanged.emit(self._getSelectedModel())

    def _onContextMenu(self, position):
        index = self._tree.currentIndex()
        if index.isValid():
            data = index.internalPointer()
            if isinstance(data, Model):
                self._contextMenuModel.popup(self.mapToGlobal(position))
            if isinstance(data, ModelNodeBase):
                self._contextMenuModelNode.popup(self.mapToGlobal(position))

    def _onAddBox(self):
        model = self._getSelectedModel()
        model.addBox()

    def _onDeleteModelOrNode(self):
        index = self._tree.currentIndex()
        if index.isValid():
            data = index.internalPointer()
            if isinstance(data, ModelNodeBase):
                data.model.removeNode(data)
            if isinstance(data, Model):
                self._models.removeModel(data)

    def _onAddModel(self):
        self._models.addModel()

