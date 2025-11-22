# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QComboBox,
    QPushButton, QDialogButtonBox, QLineEdit, QTabWidget, QWidget,
    QTableWidget, QAbstractItemView, QHeaderView, QMessageBox,
    QTableWidgetItem, QMenu, QInputDialog
)
from PySide6.QtGui import QColor, QBrush
from PySide6.QtCore import Signal, Slot, Qt

from src.utils.logger import configurar_logger
from src.db.db_service import DbService
from src.db.db_models import (
    CaKeyword, CaOrganismo, TipoReglaOrganismo,
)
from src.utils.settings_manager import SettingsManager

logger = configurar_logger(__name__)

COLOR_PRIORITARIO = QColor(230, 255, 230)
COLOR_NO_DESEADO = QColor(255, 230, 230)
COLOR_NEUTRO = QColor("white")


class GuiSettingsDialog(QDialog):
    """
    Ventana de diálogo modal para gestionar reglas.
    """
    settings_changed = Signal() 

    def __init__(self, db_service: DbService, settings_manager: SettingsManager, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Configuración de Reglas")
        self.setModal(True)
        self.setMinimumSize(800, 600)

        self.db_service = db_service
        self.settings_manager = settings_manager 
        self.config_ha_cambiado = False

        self.organismo_data_cache: dict[int, tuple[QTableWidgetItem, str, int | None]] = {}

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # --- Creación de Pestañas ---
        self.tab_keywords = self._crear_tab_keywords()
        self.tab_organismos = self._crear_tab_organismos()
        
        self.tabs.addTab(self.tab_keywords, "Gestión de Keywords")
        self.tabs.addTab(self.tab_organismos, "Gestión de Reglas de Organismo")

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.on_close)
        layout.addWidget(button_box)

        try:
            self._load_all_data()
        except Exception as e:
            logger.error(f"Error fatal al cargar datos para el diálogo: {e}")
            QMessageBox.critical(self, "Error de Carga", f"No se pudieron cargar los datos de configuración desde la BD:\n{e}")

    @Slot()
    def on_close(self):
        if self.config_ha_cambiado:
            self.settings_changed.emit()
        self.reject()

    def _load_all_data(self):
        self._load_keywords_table()
        self.organismo_data_cache.clear()
        self._load_organismos_table_master()

    # --- Pestaña de Keywords ---
    def _crear_tab_keywords(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Keywords Actuales:"))
        self.keywords_table = QTableWidget()
        self.keywords_table.setColumnCount(4)
        self.keywords_table.setHorizontalHeaderLabels(["ID", "Keyword", "Tipo", "Puntos"])
        self.keywords_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.keywords_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.keywords_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.keywords_table.setColumnHidden(0, True)
        left_layout.addWidget(self.keywords_table)
        self.kw_delete_button = QPushButton("Eliminar Keyword Seleccionada")
        self.kw_delete_button.clicked.connect(self._on_delete_keyword)
        left_layout.addWidget(self.kw_delete_button)
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Añadir Nueva Keyword:"))
        right_layout.addWidget(QLabel("Palabra:"))
        self.kw_input = QLineEdit()
        right_layout.addWidget(self.kw_input)
        right_layout.addWidget(QLabel("Tipo de Keyword:"))
        self.kw_tipo_combo = QComboBox()
        self.kw_tipo_combo.addItem("Título Positivo (Suma)", "titulo_pos")
        self.kw_tipo_combo.addItem("Título Negativo (Resta)", "titulo_neg")
        self.kw_tipo_combo.addItem("Producto clave (Suma)", "producto")
        right_layout.addWidget(self.kw_tipo_combo)
        right_layout.addWidget(QLabel("Puntos:"))
        self.kw_puntos_spin = QSpinBox()
        self.kw_puntos_spin.setRange(-100, 100)
        self.kw_puntos_spin.setValue(5)
        right_layout.addWidget(self.kw_puntos_spin)
        self.kw_add_button = QPushButton("Añadir Keyword")
        self.kw_add_button.clicked.connect(self._on_add_keyword)
        right_layout.addWidget(self.kw_add_button)
        right_layout.addStretch()
        layout.addLayout(left_layout, 3)
        layout.addLayout(right_layout, 1)
        return widget
        
    def _load_keywords_table(self):
        self.keywords_table.setRowCount(0)
        try:
            keywords = self.db_service.get_all_keywords()
            self.keywords_table.setRowCount(len(keywords))
            for row, kw in enumerate(keywords):
                self.keywords_table.setItem(row, 0, QTableWidgetItem(str(kw.keyword_id)))
                self.keywords_table.setItem(row, 1, QTableWidgetItem(kw.keyword))
                self.keywords_table.setItem(row, 2, QTableWidgetItem(kw.tipo))
                self.keywords_table.setItem(row, 3, QTableWidgetItem(str(kw.puntos)))
        except Exception as e:
            logger.error(f"Error al cargar keywords: {e}")
            QMessageBox.critical(self, "Error", f"No se pudieron cargar las keywords: {e}")

    @Slot()
    def _on_add_keyword(self):
        keyword = self.kw_input.text().strip().lower()
        tipo = self.kw_tipo_combo.currentData()
        puntos = self.kw_puntos_spin.value()
        if not keyword:
            QMessageBox.warning(self, "Error", "El campo 'Keyword' no puede estar vacío.")
            return
        try:
            self.db_service.add_keyword(keyword, tipo, puntos)
            self.config_ha_cambiado = True 
            self.kw_input.clear()
            self._load_keywords_table()
        except Exception as e:
            logger.error(f"Error al añadir keyword: {e}")
            QMessageBox.critical(self, "Error", f"No se pudo añadir la keyword (¿ya existe?):\n{e}")

    @Slot()
    def _on_delete_keyword(self):
        selected_items = self.keywords_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Error", "Seleccione una fila para eliminar.")
            return
        row = selected_items[0].row()
        keyword_id_text = self.keywords_table.item(row, 0).text()
        keyword_id = int(keyword_id_text)
        keyword_texto = self.keywords_table.item(row, 1).text()
        confirm = QMessageBox.question(
            self, "Confirmar", f"¿Está seguro de que quiere eliminar la keyword '{keyword_texto}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self.db_service.delete_keyword(keyword_id)
                self.config_ha_cambiado = True 
                self._load_keywords_table()
            except Exception as e:
                logger.error(f"Error al eliminar keyword: {e}")
                QMessageBox.critical(self, "Error", f"No se pudo eliminar la keyword:\n{e}")

    # --- Pestaña de Organismos ---
    def _crear_tab_organismos(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtrar Organismo:"))
        self.org_filter_input = QLineEdit()
        self.org_filter_input.setPlaceholderText("Escriba nombre de organismo para filtrar...")
        self.org_filter_input.textChanged.connect(self._on_filter_organismos)
        filter_layout.addWidget(self.org_filter_input)
        layout.addLayout(filter_layout)
        self.org_table = QTableWidget()
        self.org_table.setColumnCount(4)
        self.org_table.setHorizontalHeaderLabels(["Organismo ID", "Nombre Organismo", "Estado", "Puntos"])
        self.org_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.org_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.org_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.org_table.setColumnHidden(0, True)
        self.org_table.setSortingEnabled(True)
        layout.addWidget(self.org_table)
        self.org_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.org_table.customContextMenuRequested.connect(self._on_organismo_context_menu)
        layout.addWidget(QLabel("Haga clic derecho en un organismo para cambiar su estado (Prioritario, No Deseado, No Prioritario)."))
        return widget

    def _load_organismos_table_master(self):
        self.org_table.setSortingEnabled(False) 
        self.org_table.setRowCount(0)
        self.organismo_data_cache.clear()
        try:
            all_organisms = self.db_service.get_all_organisms()
            all_reglas = self.db_service.get_all_organismo_reglas()
            reglas_map = {regla.organismo_id: regla for regla in all_reglas}
            self.org_table.setRowCount(len(all_organisms))
            for row, org in enumerate(all_organisms):
                estado_str = "No Prioritario"
                puntos_str = "---"
                puntos_val = None
                color = COLOR_NEUTRO
                regla = reglas_map.get(org.organismo_id)
                if regla:
                    if regla.tipo == TipoReglaOrganismo.PRIORITARIO:
                        estado_str = "Prioritario"
                        puntos_str = str(regla.puntos)
                        puntos_val = regla.puntos
                        color = COLOR_PRIORITARIO
                    elif regla.tipo == TipoReglaOrganismo.NO_DESEADO:
                        estado_str = "No Deseado"
                        puntos_str = "N/A"
                        color = COLOR_NO_DESEADO
                item_id = QTableWidgetItem(str(org.organismo_id))
                item_nombre = QTableWidgetItem(org.nombre)
                item_estado = QTableWidgetItem(estado_str)
                item_puntos = QTableWidgetItem(puntos_str)
                item_id.setData(Qt.ItemDataRole.UserRole, org.organismo_id) 
                item_estado.setData(Qt.ItemDataRole.UserRole, (estado_str, puntos_val))
                for item in (item_id, item_nombre, item_estado, item_puntos):
                    item.setBackground(QBrush(color))
                self.org_table.setItem(row, 0, item_id)
                self.org_table.setItem(row, 1, item_nombre)
                self.org_table.setItem(row, 2, item_estado)
                self.org_table.setItem(row, 3, item_puntos)
        except Exception as e:
            logger.error(f"Error al cargar tabla maestra de organismos: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los organismos: {e}")
        finally:
            self.org_table.setSortingEnabled(True)

    @Slot(str)
    def _on_filter_organismos(self, text: str):
        texto_filtro = text.lower().strip()
        for row in range(self.org_table.rowCount()):
            nombre_item = self.org_table.item(row, 1) 
            if nombre_item:
                nombre = nombre_item.text().lower()
                self.org_table.setRowHidden(row, texto_filtro not in nombre)

    @Slot(QTableWidgetItem)
    def _on_organismo_context_menu(self, pos):
        selected_items = self.org_table.selectedItems()
        if not selected_items:
            return
        selected_row = self.org_table.row(selected_items[0])
        org_id_item = self.org_table.item(selected_row, 0)
        org_nombre_item = self.org_table.item(selected_row, 1)
        estado_item = self.org_table.item(selected_row, 2)
        if not (org_id_item and org_nombre_item and estado_item):
            return
        organismo_id = int(org_id_item.text())
        organismo_nombre = org_nombre_item.text()
        current_estado, current_puntos = estado_item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu()
        menu.setWindowTitle(f"Opciones para: {organismo_nombre}")
        action_prioritario = menu.addAction("Mover a 'Prioritario'")
        action_no_deseado = menu.addAction("Mover a 'No Deseado'")
        action_no_prioritario = menu.addAction("Mover a 'No Prioritario' (Neutro)")
        if current_estado == "Prioritario":
            action_prioritario.setEnabled(False)
        elif current_estado == "No Deseado":
            action_no_deseado.setEnabled(False)
        elif current_estado == "No Prioritario":
            action_no_prioritario.setEnabled(False)
        action_prioritario.triggered.connect(
            lambda: self._on_set_prioritario(organismo_id, organismo_nombre, current_puntos)
        )
        action_no_deseado.triggered.connect(
            lambda: self._on_set_no_deseado(organismo_id)
        )
        action_no_prioritario.triggered.connect(
            lambda: self._on_set_no_prioritario(organismo_id)
        )
        menu.exec(self.org_table.viewport().mapToGlobal(pos))

    @Slot()
    def _on_set_prioritario(self, organismo_id: int, organismo_nombre: str, current_puntos: int | None):
        default_puntos = current_puntos if current_puntos is not None else 5
        puntos, ok = QInputDialog.getInt(
            self, "Definir Puntos",
            f"Ingrese los puntos para:\n'{organismo_nombre}'",
            default_puntos, 1, 100
        )
        if ok:
            try:
                self.db_service.set_organismo_regla(
                    organismo_id=organismo_id,
                    tipo=TipoReglaOrganismo.PRIORITARIO,
                    puntos=puntos
                )
                self.config_ha_cambiado = True 
                self._load_organismos_table_master()
            except Exception as e:
                logger.error(f"Error al mover a Prioritario: {e}")
                QMessageBox.critical(self, "Error", f"No se pudo guardar la regla:\n{e}")

    @Slot()
    def _on_set_no_deseado(self, organismo_id: int):
        try:
            self.db_service.set_organismo_regla(
                organismo_id=organismo_id,
                tipo=TipoReglaOrganismo.NO_DESEADO,
                puntos=None
            )
            self.config_ha_cambiado = True 
            self._load_organismos_table_master()
        except Exception as e:
            logger.error(f"Error al mover a No Deseado: {e}")
            QMessageBox.critical(self, "Error", f"No se pudo guardar la regla:\n{e}")

    @Slot()
    def _on_set_no_prioritario(self, organismo_id: int):
        try:
            self.db_service.delete_organismo_regla(organismo_id)
            self.config_ha_cambiado = True 
            self._load_organismos_table_master()
        except Exception as e:
            logger.error(f"Error al mover a No Prioritario: {e}")
            QMessageBox.critical(self, "Error", f"No se pudo eliminar la regla:\n{e}")