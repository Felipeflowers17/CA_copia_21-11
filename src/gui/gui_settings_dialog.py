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
    settings_changed = Signal() 

    def __init__(self, db_service: DbService, settings_manager: SettingsManager, parent: QWidget | None = None):
        super().__init__(parent)
        print("--- DEBUG: INICIANDO VENTANA DE REGLAS ---")
        
        self.setWindowTitle("Configuración de Reglas")
        self.setModal(True)
        self.setMinimumSize(800, 600)

        # Fondo blanco opaco
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; }
            QTabWidget::pane { border: 1px solid #C2C7CB; background: white; }
            QWidget#TabContent { background-color: #ffffff; }
        """)

        self.db_service = db_service
        self.settings_manager = settings_manager 
        self.config_ha_cambiado = False

        self.organismo_data_cache: dict[int, tuple[QTableWidgetItem, str, int | None]] = {}

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tab_keywords = self._crear_tab_keywords()
        self.tab_organismos = self._crear_tab_organismos()
        
        self.tabs.addTab(self.tab_keywords, "Gestión de Keywords")
        self.tabs.addTab(self.tab_organismos, "Gestión de Reglas de Organismo")

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.on_close)
        layout.addWidget(button_box)

        self._load_all_data()

    @Slot()
    def on_close(self):
        if self.config_ha_cambiado:
            self.settings_changed.emit()
        self.reject()

    def _load_all_data(self):
        print("DEBUG: Cargando datos iniciales...")
        self._load_keywords_table()
        self.organismo_data_cache.clear()
        self._load_organismos_table_master()

    # --- Pestaña de Keywords ---
    def _crear_tab_keywords(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("TabContent")
        layout = QHBoxLayout(widget)
        
        # Izquierda: Tabla
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
        
        # Derecha: Formulario
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
        
        # --- CORRECCIÓN DE CONEXIÓN ---
        # Usamos 'released' y conectamos DIRECTAMENTE sin lambda
        self.kw_add_button.released.connect(self._on_add_keyword)
        # ------------------------------
        
        right_layout.addWidget(self.kw_add_button)
        right_layout.addStretch()
        
        layout.addLayout(left_layout, 3)
        layout.addLayout(right_layout, 1)
        return widget
        
    def _load_keywords_table(self):
        self.keywords_table.setRowCount(0)
        try:
            keywords = self.db_service.get_all_keywords()
            print(f"DEBUG: Cargadas {len(keywords)} palabras.")
            self.keywords_table.setRowCount(len(keywords))
            for row, kw in enumerate(keywords):
                puntos_prod = kw.puntos_productos or 0
                puntos_nomb = kw.puntos_nombre or 0

                puntos_visual = 0
                tipo_visual = "General"

                if puntos_prod != 0:
                    tipo_visual = "Producto"
                    puntos_visual = puntos_prod
                elif puntos_nomb != 0:
                    tipo_visual = "Título/Desc"
                    puntos_visual = puntos_nomb

                self.keywords_table.setItem(row, 0, QTableWidgetItem(str(kw.keyword_id)))
                self.keywords_table.setItem(row, 1, QTableWidgetItem(kw.keyword))
                self.keywords_table.setItem(row, 2, QTableWidgetItem(tipo_visual))
                self.keywords_table.setItem(row, 3, QTableWidgetItem(str(puntos_visual)))
        except Exception as e:
            print(f"ERROR CARGANDO TABLA: {e}")
            logger.error(f"Error al cargar keywords: {e}")

    @Slot() # Decorador importante para recibir señales correctamente
    def _on_add_keyword(self):
        print("--- DEBUG: BOTÓN CLICK DETECTADO ---")
        
        keyword = self.kw_input.text().strip().lower()
        tipo = self.kw_tipo_combo.currentData()
        puntos = self.kw_puntos_spin.value()
        
        print(f"Intentando guardar: {keyword} | {tipo} | {puntos}")

        if not keyword:
            QMessageBox.warning(self, "Error", "El campo 'Keyword' no puede estar vacío.")
            return

        try:
            # Llamada a BD
            self.db_service.add_keyword(keyword, tipo, puntos)
            print("Guardado en BD OK.")
            
            self.config_ha_cambiado = True 
            self.kw_input.clear()
            self._load_keywords_table()
            
            QMessageBox.information(self, "Éxito", f"Se añadió: {keyword}")
            
        except Exception as e:
            print(f"ERROR AL GUARDAR: {e}")
            logger.error(f"Error al añadir keyword: {e}")
            msg = str(e)
            if "unique constraint" in msg.lower() or "llave duplicada" in msg.lower():
                 msg = "Esa palabra ya existe."
            QMessageBox.critical(self, "Error", f"No se pudo añadir:\n{msg}")

    @Slot()
    def _on_delete_keyword(self):
        selected_items = self.keywords_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Error", "Seleccione una fila para eliminar.")
            return
        row = selected_items[0].row()
        keyword_id = int(self.keywords_table.item(row, 0).text())
        keyword_texto = self.keywords_table.item(row, 1).text()
        
        if QMessageBox.question(self, "Confirmar", f"¿Eliminar '{keyword_texto}'?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            try:
                self.db_service.delete_keyword(keyword_id)
                self.config_ha_cambiado = True 
                self._load_keywords_table()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al eliminar: {e}")

    # --- Pestaña de Organismos ---
    def _crear_tab_organismos(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("TabContent") 
        layout = QVBoxLayout(widget)
        
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtrar Organismo:"))
        self.org_filter_input = QLineEdit()
        self.org_filter_input.setPlaceholderText("Buscar...")
        self.org_filter_input.textChanged.connect(self._on_filter_organismos)
        filter_layout.addWidget(self.org_filter_input)
        layout.addLayout(filter_layout)
        
        self.org_table = QTableWidget()
        self.org_table.setColumnCount(4)
        self.org_table.setHorizontalHeaderLabels(["ID", "Organismo", "Estado", "Puntos"])
        self.org_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.org_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.org_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.org_table.setColumnHidden(0, True)
        self.org_table.setSortingEnabled(True)
        layout.addWidget(self.org_table)
        
        self.org_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.org_table.customContextMenuRequested.connect(self._on_organismo_context_menu)
        
        layout.addWidget(QLabel("Click derecho para cambiar estado."))
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
            logger.error(f"Error organismos: {e}")
        finally:
            self.org_table.setSortingEnabled(True)

    @Slot(str)
    def _on_filter_organismos(self, text: str):
        texto = text.lower().strip()
        for row in range(self.org_table.rowCount()):
            item = self.org_table.item(row, 1) 
            self.org_table.setRowHidden(row, texto not in item.text().lower())

    @Slot(QTableWidgetItem)
    def _on_organismo_context_menu(self, pos):
        sel = self.org_table.selectedItems()
        if not sel: return
        row = self.org_table.row(sel[0])
        
        org_id = int(self.org_table.item(row, 0).text())
        nombre = self.org_table.item(row, 1).text()
        estado_data = self.org_table.item(row, 2).data(Qt.ItemDataRole.UserRole)
        curr_estado = estado_data[0] if estado_data else "No Prioritario"
        curr_puntos = estado_data[1] if estado_data else None

        menu = QMenu()
        a1 = menu.addAction("Prioritario")
        a2 = menu.addAction("No Deseado")
        a3 = menu.addAction("Neutro")
        
        if curr_estado == "Prioritario": a1.setEnabled(False)
        if curr_estado == "No Deseado": a2.setEnabled(False)
        if curr_estado == "No Prioritario": a3.setEnabled(False)

        a1.triggered.connect(lambda: self._on_set_prioritario(org_id, nombre, curr_puntos))
        a2.triggered.connect(lambda: self._on_set_no_deseado(org_id))
        a3.triggered.connect(lambda: self._on_set_no_prioritario(org_id))
        
        menu.exec(self.org_table.viewport().mapToGlobal(pos))

    def _on_set_prioritario(self, org_id, nombre, curr_pts):
        pts, ok = QInputDialog.getInt(self, "Puntos", f"Puntos para '{nombre}':", curr_pts or 5, 1, 100)
        if ok:
            try:
                self.db_service.set_organismo_regla(org_id, TipoReglaOrganismo.PRIORITARIO, pts)
                self.config_ha_cambiado = True
                self._load_organismos_table_master()
            except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def _on_set_no_deseado(self, org_id):
        try:
            self.db_service.set_organismo_regla(org_id, TipoReglaOrganismo.NO_DESEADO, None)
            self.config_ha_cambiado = True
            self._load_organismos_table_master()
        except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def _on_set_no_prioritario(self, org_id):
        try:
            self.db_service.delete_organismo_regla(org_id)
            self.config_ha_cambiado = True
            self._load_organismos_table_master()
        except Exception as e: QMessageBox.critical(self, "Error", str(e))