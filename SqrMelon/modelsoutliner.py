import cgmath
from qtutil import *
from models import *
import icons

class ModelsModel(QAbstractItemModel):
    """
    ItemModel wrapped around a Models object,
    to expose it to our models outliner.
    """
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

        if isinstance(obj, ModelNodeBox) and role == Qt.DecorationRole:
            if obj.subtractive:
                return icons.get('box-sub-48')
            else:
                return icons.get('box-48')

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
    selectedModelNodesChanged = pyqtSignal(object, object)

    def __init__(self, models):
        super(ModelsOutliner, self).__init__()

        self.setLayout(vlayout())

        toolbar = hlayout()

        addModelButton = QPushButton(icons.get('Add Image-48'), '')
        addModelButton.clicked.connect(self._onAddModel)
        addModelButton.setIconSize(QSize(24, 24))
        addModelButton.setToolTip('Add model')
        addModelButton.setStatusTip('Add model')
        toolbar.addWidget(addModelButton)

        toolbar.addStretch(1)

        self._models = models
        self._model = ModelsModel(models)

        self._tree = QTreeView(self)
        self._tree.setModel(self._model)
        self._tree.setHeaderHidden(True)
        self._tree.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.layout().addLayout(toolbar)
        self.layout().addWidget(self._tree)

        self._tree.selectionModel().selectionChanged.connect(self._onSelectionChanged)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._onContextMenu)

        self._contextMenuModel = QMenu()
        self._contextMenuModelRenameAction = self._contextMenuModel.addAction(icons.get('rename-48'), 'Rename')
        self._contextMenuModelRenameAction.triggered.connect(self._onRenameModelOrNode)
        self._contextMenuModel.addAction(icons.get('duplicate-48'), 'Duplicate').triggered.connect(self._onDuplicateModelOrNode)
        self._contextMenuModel.addSeparator()
        self._contextMenuModelAddBoxAction = self._contextMenuModel.addAction(icons.get('box-48'), 'Add box')
        self._contextMenuModelAddBoxAction.triggered.connect(self._onAddBox)
        self._contextMenuModel.addSeparator()
        self._contextMenuModel.addAction(icons.get('delete-48'), 'Delete').triggered.connect(self._onDeleteModelOrNode)

        self._contextMenuModelNode = QMenu()
        self._contextMenuModelNodeRenameAction = self._contextMenuModelNode.addAction(icons.get('rename-48'), 'Rename')
        self._contextMenuModelNodeRenameAction.triggered.connect(self._onRenameModelOrNode)
        self._contextMenuModelNode.addAction(icons.get('duplicate-48'), 'Duplicate').triggered.connect(self._onDuplicateModelOrNode)
        self._contextMenuModelNode.addSeparator()
        self._contextMenuModelNode.addAction(icons.get('arrow-up-48'), 'Move up').triggered.connect(self._onMoveUpNode)
        self._contextMenuModelNode.addAction(icons.get('arrow-down-48'), 'Move down').triggered.connect(self._onMoveDownNode)
        self._contextMenuModelNode.addSeparator()
        self._contextMenuModelNode.addAction(icons.get('flip-48'), 'Toggle additive/subtractive').triggered.connect(self._onToggleAdditiveSubtractive)
        self._contextMenuModelNode.addSeparator()
        self._contextMenuModelNode.addAction(icons.get('delete-48'), 'Delete').triggered.connect(self._onDeleteModelOrNode)

    def _getSelectedModelNodes(self, model):
        result = set()
        if model is None:
            return result

        indexes = self._tree.selectedIndexes()
        for index in indexes:
            if (index is not None) and (index.isValid()):
                data = index.internalPointer()
                if isinstance(data, ModelNodeBase) and data.model == model:
                    result.add(data)
        return result

    def _getCurrentModel(self):
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
        model = self._getCurrentModel()
        modelNodes = self._getSelectedModelNodes(model)
        self.selectedModelNodesChanged.emit(model, modelNodes)

    def _onContextMenu(self, position):
        numSelectedModels = 0
        numSelectedModelNodes = 0
        for index in self._tree.selectedIndexes():
            if index.isValid():
                data = index.internalPointer()
                if isinstance(data, Model):
                    numSelectedModels += 1
                if isinstance(data, ModelNodeBase):
                    numSelectedModelNodes += 1
        if numSelectedModels > 0 and numSelectedModelNodes > 0:
            # If we have both a model and a node selected, we won't show a context menu
            return

        if numSelectedModels > 0:
            self._contextMenuModelRenameAction.setEnabled(numSelectedModels == 1)
            self._contextMenuModelAddBoxAction.setEnabled(numSelectedModels == 1)
            self._contextMenuModel.popup(self.mapToGlobal(position))
        elif numSelectedModelNodes > 0:
            self._contextMenuModelNodeRenameAction.setEnabled(numSelectedModelNodes == 1)
            self._contextMenuModelNode.popup(self.mapToGlobal(position))

    def _onAddBox(self):
        model = self._getCurrentModel()
        model.addBox()

    def _onDeleteModelOrNode(self):
        for index in reversed(self._tree.selectedIndexes()):
            if index.isValid():
                data = index.internalPointer()
                if isinstance(data, ModelNodeBase):
                    data.model.removeNode(data)
                if isinstance(data, Model):
                    self._models.removeModel(data)

    def _onRenameModelOrNode(self):
        index = self._tree.currentIndex()
        if index.isValid():
            data = index.internalPointer()
            text, ok = QInputDialog.getText(self, 'Rename', 'Name', QLineEdit.Normal, data.name)
            if ok:
                data.name = str(text)

    def _onDuplicateModelOrNode(self):
        for index in self._tree.selectedIndexes():
            if index.isValid():
                data = index.internalPointer()
                data.duplicate()
        self._tree.clearSelection()

    def _onToggleAdditiveSubtractive(self):
        for index in self._tree.selectedIndexes():
            if index.isValid():
                data = index.internalPointer()
                data.subtractive = not data.subtractive

    def _onMoveUpNode(self):
        for index in self._tree.selectedIndexes():
            if index.isValid():
                data = index.internalPointer()
                data.move(-1)
        self._tree.clearSelection()

    def _onMoveDownNode(self):
        for index in reversed(self._tree.selectedIndexes()):
            if index.isValid():
                data = index.internalPointer()
                data.move(1)
        self._tree.clearSelection()

    def _onAddModel(self):
        self._models.addModel()

    # Force select a specific Model and its ModelNodes.
    # Used by the modeler when clicking a model node
    def selectModelNodes(self, model, modelNodes):
        if model is not None:
            modelItem = self._model.index(self._models.models.index(model), 0)
            if modelNodes is None or len(modelNodes) == 0:
                self._tree.setCurrentIndex(modelItem)
            else:
                self._tree.selectionModel().clearSelection()
                for node in modelNodes:
                    modelIndex = self._model.index(model.nodes.index(node), 0, modelItem)
                    self._tree.selectionModel().select(modelIndex, QItemSelectionModel.Select)
                # modelNodeItem = self._model.index(model.nodes.index(modelNodes[0]), 0, modelItem)
                # self._tree.setCurrentIndex(modelNodeItem)
        else:
            self._tree.setCurrentIndex(QModelIndex())

    def reset(self):
        self._tree.reset()
