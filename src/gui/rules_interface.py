# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QHeaderView, 
    QTableWidgetItem, QAbstractItemView, QMenu, QInputDialog
)
from qfluentwidgets import (
    ScrollArea, FluentIcon as FIF,
    TitleLabel, BodyLabel, StrongBodyLabel, SubtitleLabel, SpinBox, ComboBox, PrimaryPushButton, 
    TableWidget, LineEdit, CardWidget, InfoBar, SearchLineEdit
)

class RulesInterface(ScrollArea):
    rules_changed = Signal()

    def __init__(self, db_service, settings_manager, parent=None):
        super().__init__(parent)
        self.db_service = db_service
        self.settings_manager = settings_manager
        self.view = QWidget(self); self.setWidget(self.view); self.setWidgetResizable(True); self.setObjectName("RulesInterface")
        self.setStyleSheet("RulesInterface, QWidget#RulesInterface { background-color: transparent; } QMenu { background-color: #ffffff; border: 1px solid #d0d0d0; border-radius: 8px; padding: 4px; } QMenu::item { padding: 6px 24px; border-radius: 4px; color: #000000; } QMenu::item:selected { background-color: #e0e0e0; }")
        self.view.setStyleSheet("background-color: transparent;")
        self.vBoxLayout = QVBoxLayout(self.view); self.vBoxLayout.setContentsMargins(36, 20, 36, 36); self.vBoxLayout.setSpacing(20)
        self.vBoxLayout.addWidget(TitleLabel("Reglas de Puntuación", self))
        self._init_threshold_section(); self.vBoxLayout.addSpacing(10)
        self._init_keywords_section(); self.vBoxLayout.addSpacing(10)
        self._init_organisms_section(); self.vBoxLayout.addStretch(1)
        self._load_threshold(); self._load_keywords_table(); self._load_organisms_table()

    def _init_threshold_section(self):
        self.cardUmbral = CardWidget(self); layout = QVBoxLayout(self.cardUmbral); layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(StrongBodyLabel("Umbral de Aceptación", self)); layout.addWidget(BodyLabel("Puntaje mínimo para 'Candidatas'.", self)); layout.addSpacing(10)
        h = QHBoxLayout(); h.addWidget(BodyLabel("Puntaje Mínimo:", self)); self.spinUmbral = SpinBox(); self.spinUmbral.setRange(0, 1000); self.spinUmbral.setFixedWidth(100); self.spinUmbral.valueChanged.connect(self._save_threshold)
        h.addWidget(self.spinUmbral); h.addStretch(1); layout.addLayout(h); self.vBoxLayout.addWidget(self.cardUmbral)

    def _load_threshold(self):
        self.settings_manager.load_settings()
        try: val = int(self.settings_manager.get_setting("umbral_puntaje_minimo") or 5)
        except: val = 5
        self.spinUmbral.setValue(val)

    def _save_threshold(self, val): self.settings_manager.set_setting("umbral_puntaje_minimo", val); self.rules_changed.emit()

    def _init_keywords_section(self):
        self.vBoxLayout.addWidget(SubtitleLabel("Keywords", self))
        self.cardKw = CardWidget(self); l = QVBoxLayout(self.cardKw); l.setContentsMargins(20,20,20,20); l.setSpacing(15)
        l.addWidget(BodyLabel("Define palabras clave.", self))
        h = QHBoxLayout(); self.txtKw = LineEdit(); self.txtKw.setPlaceholderText("Nueva keyword...")
        self.comboKwType = ComboBox(); self.comboKwType.addItems(["Título/Desc (+)", "Título/Desc (-)", "Producto (+)"]); self.comboKwType.setFixedWidth(160)
        self.spinKwPoints = SpinBox(); self.spinKwPoints.setRange(-1000, 1000); self.spinKwPoints.setValue(10); self.spinKwPoints.setFixedWidth(100)
        b = PrimaryPushButton("Agregar", self); b.clicked.connect(self._add_keyword)
        h.addWidget(self.txtKw); h.addWidget(self.comboKwType); h.addWidget(self.spinKwPoints); h.addWidget(b); l.addLayout(h)
        self.tableKw = TableWidget(self); self.tableKw.setColumnCount(4); self.tableKw.setHorizontalHeaderLabels(["ID", "Palabra", "Tipo", "Puntos"]); self.tableKw.verticalHeader().hide(); self.tableKw.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch); self.tableKw.setColumnHidden(0, True); self.tableKw.setMinimumHeight(250)
        self.tableKw.doubleClicked.connect(self._delete_keyword_prompt); l.addWidget(self.tableKw); self.vBoxLayout.addWidget(self.cardKw)

    def _init_organisms_section(self):
        self.vBoxLayout.addWidget(SubtitleLabel("Organismos", self))
        self.cardOrg = CardWidget(self); l = QVBoxLayout(self.cardOrg); l.setContentsMargins(20,20,20,20); l.setSpacing(10)
        l.addWidget(BodyLabel("Clic derecho para asignar reglas.", self))
        self.searchOrg = SearchLineEdit(); self.searchOrg.setPlaceholderText("Filtrar organismo..."); self.searchOrg.textChanged.connect(self._filter_organisms_table); l.addWidget(self.searchOrg)
        self.tableOrg = TableWidget(self); self.tableOrg.setColumnCount(4); self.tableOrg.setHorizontalHeaderLabels(["ID", "Organismo", "Estado", "Puntos"]); self.tableOrg.verticalHeader().hide(); self.tableOrg.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch); self.tableOrg.setColumnHidden(0, True); self.tableOrg.setMinimumHeight(400)
        self.tableOrg.setContextMenuPolicy(Qt.CustomContextMenu); self.tableOrg.customContextMenuRequested.connect(self._show_org_context_menu)
        l.addWidget(self.tableOrg); self.vBoxLayout.addWidget(self.cardOrg)

    def _load_keywords_table(self):
        self.tableKw.setRowCount(0); kws = self.db_service.get_all_keywords()
        self.tableKw.setRowCount(len(kws))
        for r, k in enumerate(kws):
            self.tableKw.setItem(r, 0, QTableWidgetItem(str(k.keyword_id))); self.tableKw.setItem(r, 1, QTableWidgetItem(k.keyword))
            t = k.tipo
            if t == "titulo_pos": t="Título (+)"
            elif t=="titulo_neg": t="Título (-)"
            elif t=="producto": t="Producto (+)"
            self.tableKw.setItem(r, 2, QTableWidgetItem(t)); self.tableKw.setItem(r, 3, QTableWidgetItem(str(k.puntos)))

    def _add_keyword(self):
        t = self.txtKw.text().strip(); 
        if not t: return
        ts = ["titulo_pos", "titulo_neg", "producto"][self.comboKwType.currentIndex()]
        try: self.db_service.add_keyword(t, ts, self.spinKwPoints.value()); self.txtKw.clear(); self._load_keywords_table(); self.rules_changed.emit(); InfoBar.success("OK", "Keyword agregada.", duration=2000, parent=self)
        except Exception as e: InfoBar.error("Error", str(e), parent=self)

    def _delete_keyword_prompt(self, idx):
        self.db_service.delete_keyword(int(self.tableKw.item(idx.row(), 0).text())); self._load_keywords_table(); self.rules_changed.emit(); InfoBar.warning("Eliminado", "Keyword eliminada.", duration=2000, parent=self)

    def _load_organisms_table(self):
        self.tableOrg.setRowCount(0); orgs = self.db_service.get_all_organisms(); reglas = {r.organismo_id: r for r in self.db_service.get_all_organismo_reglas()}
        self.tableOrg.setRowCount(len(orgs))
        for r, o in enumerate(orgs):
            est = "Neutro"; pts = "-"
            if o.organismo_id in reglas:
                rg = reglas[o.organismo_id]
                if rg.tipo == "prioritario": est="Prioritario"
                elif rg.tipo == "no_deseado": est="No Deseado"
                pts = str(rg.puntos) if rg.puntos is not None else "-"
            self.tableOrg.setItem(r, 0, QTableWidgetItem(str(o.organismo_id))); self.tableOrg.setItem(r, 1, QTableWidgetItem(o.nombre))
            self.tableOrg.setItem(r, 2, QTableWidgetItem(est)); self.tableOrg.setItem(r, 3, QTableWidgetItem(pts))
            if est == "Prioritario": self.tableOrg.item(r, 1).setBackground(Qt.darkGreen); self.tableOrg.item(r, 1).setForeground(Qt.white)
            elif est == "No Deseado": self.tableOrg.item(r, 1).setBackground(Qt.darkRed); self.tableOrg.item(r, 1).setForeground(Qt.white)

    def _filter_organisms_table(self, txt):
        t = txt.lower()
        for r in range(self.tableOrg.rowCount()): self.tableOrg.setRowHidden(r, t not in self.tableOrg.item(r, 1).text().lower())

    def _show_org_context_menu(self, pos):
        idx = self.tableOrg.indexAt(pos)
        if not idx.isValid(): return
        oid = int(self.tableOrg.item(idx.row(), 0).text()); nom = self.tableOrg.item(idx.row(), 1).text()
        m = QMenu(self)
        a1 = m.addAction("Prioritario (+)"); a2 = m.addAction("No Deseado (X)"); m.addSeparator(); a3 = m.addAction("Neutro")
        act = m.exec(self.tableOrg.mapToGlobal(pos))
        if act == a1: self._set_rule(oid, nom, "prioritario")
        elif act == a2: self._set_rule(oid, nom, "no_deseado")
        elif act == a3: self.db_service.delete_organismo_regla(oid); self._load_organisms_table(); self.rules_changed.emit()

    def _set_rule(self, oid, nom, tipo):
        pt = 0
        if tipo == "prioritario":
            v, k = QInputDialog.getInt(self, "Puntos", f"Puntos para '{nom}':", 10, 1, 1000)
            if k: pt = v
            else: return
        elif tipo == "no_deseado":
            v, k = QInputDialog.getInt(self, "Puntos", f"Resta para '{nom}':", -100, -9999, -1)
            if k: pt = v
            else: return
        try: self.db_service.set_organismo_regla(oid, tipo, pt); self._load_organisms_table(); self.rules_changed.emit(); InfoBar.success("OK", "Regla guardada.", duration=2000, parent=self)
        except Exception as e: InfoBar.error("Error", str(e), parent=self)