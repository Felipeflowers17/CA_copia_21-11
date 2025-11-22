# -*- coding: utf-8 -*-
"""
Panel de Herramientas.
Actualizado: 
1. Fix Ordenamiento: 'N/A' ahora se ordena correctamente al final.
2. Fix Visual: Diálogo de edición de puntos modernizado (Fluent Design).
"""

from PySide6.QtCore import Qt, Signal, QDate, QTime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QHeaderView, 
    QTableWidgetItem, QMenu, QMessageBox, QGroupBox, 
    QSplitter, QDialog, QLabel, QFrame
)
from PySide6.QtGui import QColor, QBrush

from qfluentwidgets import (
    SegmentedWidget, TitleLabel, BodyLabel, CalendarPicker, 
    SpinBox, PrimaryPushButton, CheckBox, TimePicker,
    TableWidget, LineEdit, ComboBox, PushButton, SubtitleLabel,
    InfoBar, InfoBarPosition, StrongBodyLabel, MessageBox
)

from sqlalchemy import update
from src.utils.logger import configurar_logger
from src.db.db_models import TipoReglaOrganismo, CaKeyword

logger = configurar_logger(__name__)

COLOR_PRIORITARIO = QColor(230, 255, 230)
COLOR_NO_DESEADO = QColor(255, 230, 230)
COLOR_NEUTRO = QColor(255, 255, 255)

# --- 1. FIX ORDENAMIENTO: Lógica Inteligente ---
class NumericTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        # Definimos una función para obtener el valor numérico real
        def get_sort_value(text):
            if text == "N/A": 
                return -9999999.0 # Valor muy bajo para que quede al final
            try:
                return float(text)
            except ValueError:
                return -9999998.0 # Si no es número, también al final
        
        return get_sort_value(self.text()) < get_sort_value(other.text())
# -----------------------------------------------

# --- 2. FIX VISUAL: Nuevo Diálogo Moderno ---
class EditScoreDialog(QDialog):
    def __init__(self, org_name, current_val, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar Puntos")
        self.resize(380, 220)
        self.val = current_val
        
        # Estilo moderno igual al resto de la app
        self.setStyleSheet("""
            QDialog { background-color: palette(window); color: palette(text); }
            QLabel { font-size: 14px; color: #333; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Título del Organismo
        lbl_title = SubtitleLabel("Asignar Puntaje", self)
        layout.addWidget(lbl_title)
        
        lbl_desc = BodyLabel(f"Organismo:\n{org_name}", self)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #666; margin-bottom: 5px;")
        layout.addWidget(lbl_desc)
        
        # Control de Puntos
        h_spin = QHBoxLayout()
        h_spin.addWidget(StrongBodyLabel("Puntos:", self))
        self.spin = SpinBox()
        self.spin.setRange(1, 1000)
        self.spin.setValue(int(current_val))
        self.spin.setFixedWidth(120)
        h_spin.addWidget(self.spin)
        h_spin.addStretch()
        layout.addLayout(h_spin)
        
        layout.addStretch()
        
        # Botones
        h_btn = QHBoxLayout()
        btn_cancel = PushButton("Cancelar", self)
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = PrimaryPushButton("Guardar", self)
        btn_save.clicked.connect(self.accept)
        
        h_btn.addStretch()
        h_btn.addWidget(btn_cancel)
        h_btn.addWidget(btn_save)
        layout.addLayout(h_btn)

    def get_value(self):
        return self.spin.value()
# --------------------------------------------

class EditKeywordDialog(QDialog):
    def __init__(self, kw_id, name, p_nom, p_desc, p_prod, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar Keyword")
        self.resize(420, 350)
        self.kw_id = kw_id
        self.delete_requested = False
        
        self.setStyleSheet("""
            QDialog { background-color: palette(window); color: palette(text); }
            QGroupBox { font-weight: 600; border: 1px solid #e0e0e0; border-radius: 8px; margin-top: 12px; padding: 18px 12px 12px 12px; background-color: palette(base); }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 12px; padding: 0 5px; background-color: palette(window); }
        """)
        
        layout = QVBoxLayout(self); layout.setSpacing(20); layout.setContentsMargins(25, 25, 25, 25)
        
        vName = QVBoxLayout(); vName.setSpacing(8)
        vName.addWidget(StrongBodyLabel("Nombre de la Keyword:", self))
        self.txtName = LineEdit(); self.txtName.setText(name); self.txtName.setClearButtonEnabled(True); self.txtName.setFixedHeight(36)
        vName.addWidget(self.txtName); layout.addLayout(vName)
        
        gPts = QGroupBox("Configuración de Puntajes"); vPts = QVBoxLayout(); vPts.setSpacing(15)
        self.chkNom, self.spinNom = self._create_row("En Nombre (Título)", p_nom, vPts)
        self.chkDesc, self.spinDesc = self._create_row("En Descripción", p_desc, vPts)
        self.chkProd, self.spinProd = self._create_row("En Productos", p_prod, vPts)
        gPts.setLayout(vPts); layout.addWidget(gPts)
        
        layout.addStretch()
        hBtn = QHBoxLayout(); hBtn.setSpacing(15)
        self.btnDelete = PushButton("Eliminar Keyword", self)
        self.btnDelete.setStyleSheet("""
            QPushButton { background-color: #d9534f; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: 600; }
            QPushButton:hover { background-color: #c9302c; }
            QPushButton:pressed { background-color: #ac2925; }
        """)
        self.btnDelete.setCursor(Qt.PointingHandCursor); self.btnDelete.clicked.connect(self.on_delete)
        
        self.btnSave = PrimaryPushButton("Guardar Cambios", self); self.btnSave.setCursor(Qt.PointingHandCursor); self.btnSave.clicked.connect(self.accept)
        hBtn.addWidget(self.btnDelete); hBtn.addStretch(); hBtn.addWidget(self.btnSave); layout.addLayout(hBtn)

    def _create_row(self, label_text, value, parent_layout):
        h = QHBoxLayout()
        chk = CheckBox(label_text); is_active = (value != 0); chk.setChecked(is_active)
        spin = SpinBox(); spin.setRange(-100, 100); spin.setValue(value if value != 0 else 5)
        spin.setFixedWidth(130); spin.setAlignment(Qt.AlignCenter); spin.setEnabled(is_active)
        chk.stateChanged.connect(lambda: spin.setEnabled(chk.isChecked()))
        h.addWidget(chk); h.addStretch(); h.addWidget(spin); parent_layout.addLayout(h)
        line = QFrame(); line.setFrameShape(QFrame.HLine); line.setStyleSheet("background-color: #f0f0f0; margin-top: 5px;"); line.setFixedHeight(1)
        parent_layout.addWidget(line)
        return chk, spin

    def on_delete(self):
        w = MessageBox("Confirmar Eliminación", f"¿Eliminar '{self.txtName.text()}'?", self)
        w.yesButton.setText("Eliminar"); w.yesButton.setStyleSheet("background-color: #d9534f; color: white;")
        w.cancelButton.setText("Cancelar")
        if w.exec(): self.delete_requested = True; self.accept()

    def get_data(self):
        p_nom = self.spinNom.value() if self.chkNom.isChecked() else 0
        p_desc = self.spinDesc.value() if self.chkDesc.isChecked() else 0
        p_prod = self.spinProd.value() if self.chkProd.isChecked() else 0
        return self.txtName.text(), p_nom, p_desc, p_prod

class GuiToolsWidget(QWidget):
    start_scraping_signal = Signal(dict); start_export_signal = Signal(list); start_recalculate_signal = Signal(); settings_changed_signal = Signal(); autopilot_config_changed_signal = Signal()

    def __init__(self, db_service, settings_manager, parent=None):
        super().__init__(parent)
        self.setObjectName("gui_tools_widget"); self.db_service = db_service; self.settings_manager = settings_manager
        self.vBox = QVBoxLayout(self); self.vBox.setContentsMargins(20,20,20,20); self.vBox.setSpacing(15)
        self.vBox.addWidget(TitleLabel("Herramientas y Configuración", self))
        self.pivot = SegmentedWidget(self)
        for k,v in [("extraer","Extraer"), ("exportar","Exportar"), ("configuracion","Config. Puntajes"), ("avanzado","Avanzado")]: self.pivot.addItem(k,v)
        self.pivot.setCurrentItem("extraer"); self.vBox.addWidget(self.pivot)
        self.stackedWidget = QStackedWidget(self); self.vBox.addWidget(self.stackedWidget)
        self.pageExtract = self._create_extract_page(); self.stackedWidget.addWidget(self.pageExtract)
        self.pageExport = self._create_export_page(); self.stackedWidget.addWidget(self.pageExport)
        self.pageConfig = self._create_config_page(); self.stackedWidget.addWidget(self.pageConfig)
        self.pageAdvanced = self._create_advanced_page(); self.stackedWidget.addWidget(self.pageAdvanced)
        self.pivot.currentItemChanged.connect(lambda k: self.stackedWidget.setCurrentIndex(["extraer", "exportar", "configuracion", "avanzado"].index(k)))

    def _create_extract_page(self):
        w = QWidget(); l = QVBoxLayout(w); l.setSpacing(20)
        l.addWidget(SubtitleLabel("Scraping Manual (Fase 1)", w))
        gDates = QGroupBox("1. Rango de Fechas"); vDates = QVBoxLayout(); hDates = QHBoxLayout()
        vFrom = QVBoxLayout(); vFrom.addWidget(BodyLabel("Desde:", w)); self.dateFrom = CalendarPicker(w); self.dateFrom.setDate(QDate.currentDate().addDays(-7)); vFrom.addWidget(self.dateFrom)
        vTo = QVBoxLayout(); vTo.addWidget(BodyLabel("Hasta:", w)); self.dateTo = CalendarPicker(w); self.dateTo.setDate(QDate.currentDate()); vTo.addWidget(self.dateTo)
        hDates.addLayout(vFrom); hDates.addSpacing(30); hDates.addLayout(vTo); hDates.addStretch(); vDates.addLayout(hDates); gDates.setLayout(vDates); l.addWidget(gDates)
        gOpts = QGroupBox("2. Configuración"); vOpts = QVBoxLayout(); hPage = QHBoxLayout()
        hPage.addWidget(BodyLabel("Límite de Páginas (0 = Todo):", w)); self.spinPages = SpinBox(w); self.spinPages.setRange(0, 1000); self.spinPages.setValue(0); self.spinPages.setFixedWidth(120); hPage.addWidget(self.spinPages); hPage.addStretch(); vOpts.addLayout(hPage); gOpts.setLayout(vOpts); l.addWidget(gOpts)
        l.addSpacing(10); hBtn = QHBoxLayout(); b = PrimaryPushButton("Iniciar Extracción", w); b.setFixedWidth(220); b.clicked.connect(self._on_click_extract); hBtn.addStretch(); hBtn.addWidget(b); hBtn.addStretch(); l.addLayout(hBtn); l.addStretch()
        return w
    def _on_click_extract(self):
        try: df = self.dateFrom.date.toPython(); dt = self.dateTo.date.toPython()
        except: df = self.dateFrom.getDate().toPython(); dt = self.dateTo.getDate().toPython()
        self.start_scraping_signal.emit({"mode": "to_db", "date_from": df, "date_to": dt, "max_paginas": self.spinPages.value()})

    def _create_export_page(self):
        w = QWidget(); l = QVBoxLayout(w); l.setSpacing(20)
        l.addWidget(SubtitleLabel("Centro de Exportación", w))
        gItems = QGroupBox("1. Elementos a Exportar"); vItems = QVBoxLayout()
        self.chk_bd = CheckBox("Base de Datos Completa (Backup)", w); self.chk_config = CheckBox("Keywords y Organismos (Reglas)", w); self.chk_tabs = CheckBox("Todas las Pestañas (Candidatas, Seguimiento, Ofertadas)", w); self.chk_tabs.setChecked(True)
        vItems.addWidget(self.chk_bd); vItems.addWidget(self.chk_config); vItems.addWidget(self.chk_tabs); gItems.setLayout(vItems); l.addWidget(gItems)
        gFmt = QGroupBox("2. Formatos de Salida"); hFmt = QHBoxLayout()
        self.chk_excel = CheckBox("Excel (.xlsx)", w); self.chk_csv = CheckBox("CSV (.csv)", w); self.chk_excel.setChecked(True)
        hFmt.addWidget(self.chk_excel); hFmt.addSpacing(20); hFmt.addWidget(self.chk_csv); hFmt.addStretch(); gFmt.setLayout(hFmt); l.addWidget(gFmt)
        l.addSpacing(10); hBtn = QHBoxLayout(); b = PrimaryPushButton("Generar Exportaciones", w); b.setFixedWidth(220); b.clicked.connect(self._on_click_export); hBtn.addStretch(); hBtn.addWidget(b); hBtn.addStretch(); l.addLayout(hBtn); l.addStretch()
        return w
    def _on_click_export(self):
        fmts = []; tips = []
        if self.chk_excel.isChecked(): fmts.append("excel")
        if self.chk_csv.isChecked(): fmts.append("csv")
        if self.chk_bd.isChecked(): tips.append("bd_full")
        if self.chk_config.isChecked(): tips.append("config")
        if self.chk_tabs.isChecked(): tips.append("tabs")
        if not fmts or not tips: return
        lt = [{"tipo": t, "format": f, "scope": "all"} for t in tips for f in fmts]
        self.start_export_signal.emit(lt)

    def _create_advanced_page(self):
        w = QWidget(); l = QVBoxLayout(w); l.addWidget(SubtitleLabel("Piloto Automático", w))
        g1 = QGroupBox("Extracción Automática (Ayer)"); v1 = QVBoxLayout(); h1 = QHBoxLayout()
        self.chkAutoExtract = CheckBox("Habilitar", w); self.timeExtract = TimePicker(w, showSeconds=False) 
        h1.addWidget(self.chkAutoExtract); h1.addStretch(); h1.addWidget(BodyLabel("Hora de ejecución:", w)); h1.addWidget(self.timeExtract); v1.addLayout(h1); g1.setLayout(v1); l.addWidget(g1)
        g2 = QGroupBox("Actualización de Pestañas"); v2 = QVBoxLayout(); h2 = QHBoxLayout()
        self.chkAutoUpdate = CheckBox("Habilitar", w); self.timeUpdate = TimePicker(w, showSeconds=False) 
        h2.addWidget(self.chkAutoUpdate); h2.addStretch(); h2.addWidget(BodyLabel("Hora de ejecución:", w)); h2.addWidget(self.timeUpdate); v2.addLayout(h2); g2.setLayout(v2); l.addWidget(g2)
        l.addSpacing(20); hBtn = QHBoxLayout(); b = PrimaryPushButton("Guardar Configuración", w); b.setFixedWidth(250); b.clicked.connect(self._save_advanced); hBtn.addStretch(); hBtn.addWidget(b); hBtn.addStretch(); l.addLayout(hBtn); l.addStretch()
        self._load_advanced_settings(); return w
    def _load_advanced_settings(self):
        self.chkAutoExtract.setChecked(bool(self.settings_manager.get_setting("auto_extract_enabled")))
        self.chkAutoUpdate.setChecked(bool(self.settings_manager.get_setting("auto_update_enabled")))
        self.timeExtract.setTime(QTime.fromString(self.settings_manager.get_setting("auto_extract_time") or "08:00", "HH:mm"))
        self.timeUpdate.setTime(QTime.fromString(self.settings_manager.get_setting("auto_update_time") or "09:00", "HH:mm"))
    def _save_advanced(self):
        self.settings_manager.set_setting("auto_extract_enabled", self.chkAutoExtract.isChecked())
        self.settings_manager.set_setting("auto_update_enabled", self.chkAutoUpdate.isChecked())
        t_ext = self.timeExtract.time.toString("HH:mm") if hasattr(self.timeExtract, "time") else self.timeExtract.getTime().toString("HH:mm")
        t_upd = self.timeUpdate.time.toString("HH:mm") if hasattr(self.timeUpdate, "time") else self.timeUpdate.getTime().toString("HH:mm")
        self.settings_manager.set_setting("auto_extract_time", t_ext); self.settings_manager.set_setting("auto_update_time", t_upd)
        self.settings_manager.save_settings(self.settings_manager.config); self.autopilot_config_changed_signal.emit()
        InfoBar.success(title="Guardado", content="Configuración avanzada guardada correctamente.", orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP_RIGHT, duration=3000, parent=self.window())

    def _create_config_page(self):
        w = QWidget(); main_layout = QVBoxLayout(w); main_layout.setContentsMargins(0, 0, 0, 0); main_layout.addWidget(BodyLabel("Doble clic para EDITAR.", w))
        splitter = QSplitter(Qt.Vertical)
        org_widget = QWidget(); org_layout = QVBoxLayout(org_widget); org_layout.setContentsMargins(0, 10, 0, 10); hFilter = QHBoxLayout(); hFilter.addWidget(BodyLabel("Organismos:", w))
        self.txtFilterOrg = LineEdit(w); self.txtFilterOrg.setPlaceholderText("Filtrar..."); self.txtFilterOrg.textChanged.connect(self._filter_org_table); hFilter.addWidget(self.txtFilterOrg); org_layout.addLayout(hFilter)
        
        # --- TABLA ORGANISMOS ---
        self.tableOrg = TableWidget(w); self.tableOrg.setColumnCount(4); self.tableOrg.setHorizontalHeaderLabels(["ID", "Organismo", "Estado", "Puntos"])
        self.tableOrg.verticalHeader().hide(); self.tableOrg.setColumnHidden(0, True); header = self.tableOrg.horizontalHeader(); header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.tableOrg.cellDoubleClicked.connect(self._on_org_double_click)
        self.tableOrg.setSortingEnabled(True)
        org_layout.addWidget(self.tableOrg); splitter.addWidget(org_widget)

        kw_widget = QWidget(); kw_layout = QVBoxLayout(kw_widget); kw_layout.setContentsMargins(0, 10, 0, 10); hAddKw = QHBoxLayout()
        self.txtKw = LineEdit(w); self.txtKw.setPlaceholderText("Nueva keyword..."); btnAddKw = PushButton("Añadir", w); btnAddKw.clicked.connect(self._add_keyword)
        hAddKw.addWidget(BodyLabel("Nueva Keyword:", w)); hAddKw.addWidget(self.txtKw, 1); hAddKw.addWidget(btnAddKw); kw_layout.addLayout(hAddKw)
        
        # --- TABLA KEYWORDS ---
        self.tableKw = TableWidget(w); self.tableKw.setColumnCount(5); self.tableKw.setHorizontalHeaderLabels(["ID", "Keyword", "Pts Nom", "Pts Desc", "Pts Prod"])
        self.tableKw.verticalHeader().hide(); self.tableKw.setColumnHidden(0, True); headerKw = self.tableKw.horizontalHeader(); headerKw.setSectionResizeMode(1, QHeaderView.Stretch)
        self.tableKw.cellDoubleClicked.connect(self._on_kw_double_click)
        self.tableKw.setSortingEnabled(True)
        kw_layout.addWidget(self.tableKw); splitter.addWidget(kw_widget); main_layout.addWidget(splitter)

        self.btnSaveSettings = PrimaryPushButton("Guardar ajustes y Recalcular", w); self.btnSaveSettings.setFixedHeight(40); self.btnSaveSettings.clicked.connect(self._on_save_and_recalc); main_layout.addWidget(self.btnSaveSettings)
        self._load_org_data(); self._load_kw_data(); return w

    def _load_org_data(self):
        self.tableOrg.setSortingEnabled(False)
        self.tableOrg.setRowCount(0); orgs = self.db_service.get_all_organisms(); reglas = {r.organismo_id: r for r in self.db_service.get_all_organismo_reglas()}
        self.tableOrg.setRowCount(len(orgs))
        for row, org in enumerate(orgs):
            regla = reglas.get(org.organismo_id); color = COLOR_NEUTRO; estado_str = "Neutro"; puntos_str = "0"
            if regla:
                if regla.tipo == TipoReglaOrganismo.PRIORITARIO: color = COLOR_PRIORITARIO; estado_str = "Prioritario"; puntos_str = str(regla.puntos)
                elif regla.tipo == TipoReglaOrganismo.NO_DESEADO: color = COLOR_NO_DESEADO; estado_str = "No Deseado"; puntos_str = "N/A"
            
            item_id = QTableWidgetItem(str(org.organismo_id))
            item_nom = QTableWidgetItem(org.nombre)
            item_est = QTableWidgetItem(estado_str)
            # Usamos NumericTableWidgetItem CORREGIDO
            item_pts = NumericTableWidgetItem(puntos_str)
            
            for it in [item_id, item_nom, item_est, item_pts]: it.setBackground(QBrush(color)); it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.tableOrg.setItem(row, 0, item_id); self.tableOrg.setItem(row, 1, item_nom); self.tableOrg.setItem(row, 2, item_est); self.tableOrg.setItem(row, 3, item_pts)
        self.tableOrg.setSortingEnabled(True)

    def _filter_org_table(self, text):
        text = text.lower(); [self.tableOrg.setRowHidden(r, text not in self.tableOrg.item(r, 1).text().lower()) for r in range(self.tableOrg.rowCount())]
    
    # --- LÓGICA DE EDICIÓN ACTUALIZADA ---
    def _on_org_double_click(self, row, col):
        org_id = int(self.tableOrg.item(row, 0).text())
        org_name = self.tableOrg.item(row, 1).text()
        
        if col == 3: # Columna Puntos
             current_status = self.tableOrg.item(row, 2).text()
             current_pts_text = self.tableOrg.item(row, 3).text()
             
             # Si es No Deseado, no tiene sentido editar puntos (son N/A)
             if current_status == "No Deseado": return

             val_actual = int(current_pts_text) if current_pts_text.isdigit() else 5
             
             # USAR NUEVO DIÁLOGO MODERNO
             dialog = EditScoreDialog(org_name, val_actual, self)
             if dialog.exec():
                 val = dialog.get_value()
                 self.db_service.set_organismo_regla(org_id, TipoReglaOrganismo.PRIORITARIO, val)
                 self._load_org_data()
        else:
            menu = QMenu()
            menu.addAction("Prioritario").triggered.connect(lambda: self._set_org_rule_logic(org_id, "prioritario", org_name))
            menu.addAction("No Deseado").triggered.connect(lambda: self._set_org_rule_logic(org_id, "no_deseado", org_name))
            menu.addAction("Neutro").triggered.connect(lambda: self._set_org_rule_logic(org_id, "neutro", org_name))
            menu.exec(self.cursor().pos())
            
    def _menu_org(self, pos): self._on_org_double_click(self.tableOrg.itemAt(pos).row(), 0)
    def _set_org_rule_logic(self, org_id, tipo, nom):
        try:
            if tipo == "prioritario": self.db_service.set_organismo_regla(org_id, TipoReglaOrganismo.PRIORITARIO, 5)
            elif tipo == "no_deseado": self.db_service.set_organismo_regla(org_id, TipoReglaOrganismo.NO_DESEADO)
            else: self.db_service.delete_organismo_regla(org_id)
            self._load_org_data()
        except: pass

    def _load_kw_data(self):
        self.tableKw.setSortingEnabled(False)
        self.tableKw.setRowCount(0); kws = self.db_service.get_all_keywords()
        self.tableKw.setRowCount(len(kws))
        for r, k in enumerate(kws):
            self.tableKw.setItem(r, 0, QTableWidgetItem(str(k.keyword_id))); self.tableKw.setItem(r, 1, QTableWidgetItem(k.keyword))
            self.tableKw.setItem(r, 2, NumericTableWidgetItem(str(k.puntos_nombre))); self.tableKw.setItem(r, 3, NumericTableWidgetItem(str(k.puntos_descripcion)))
            self.tableKw.setItem(r, 4, NumericTableWidgetItem(str(k.puntos_productos)))
            for c in range(5): self.tableKw.item(r, c).setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        self.tableKw.setSortingEnabled(True)

    def _add_keyword(self):
        txt = self.txtKw.text().strip()
        if not txt: return
        try: self.db_service.add_keyword(txt, 0, 0, 0); self.txtKw.clear(); self._load_kw_data()
        except: pass

    def _on_kw_double_click(self, row, col):
        kw_id = int(self.tableKw.item(row, 0).text()); name = self.tableKw.item(row, 1).text()
        p1 = int(self.tableKw.item(row, 2).text()); p2 = int(self.tableKw.item(row, 3).text()); p3 = int(self.tableKw.item(row, 4).text())
        dialog = EditKeywordDialog(kw_id, name, p1, p2, p3, self)
        if dialog.exec():
            if dialog.delete_requested: self.db_service.delete_keyword(kw_id)
            else: n, a, b, c = dialog.get_data(); self._update_keyword_full(kw_id, n, a, b, c)
            self._load_kw_data()

    def _update_keyword_full(self, kw_id, name, p_nom, p_desc, p_prod):
        with self.db_service.session_factory() as session:
            try: stmt = update(CaKeyword).where(CaKeyword.keyword_id == kw_id).values(keyword=name, puntos_nombre=p_nom, puntos_descripcion=p_desc, puntos_productos=p_prod); session.execute(stmt); session.commit()
            except Exception as e: logger.error(f"Error update keyword: {e}")

    def _on_save_and_recalc(self):
        self.settings_changed_signal.emit(); self.start_recalculate_signal.emit()