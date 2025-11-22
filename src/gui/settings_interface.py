# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import (
    ScrollArea, SettingCardGroup, SettingCard, FluentIcon as FIF,
    TitleLabel, SpinBox
)

class SettingsInterface(ScrollArea):
    settings_changed = Signal()

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.view = QWidget(self); self.setWidget(self.view); self.setWidgetResizable(True); self.setObjectName("SettingsInterface")
        self.setStyleSheet("SettingsInterface, QWidget#SettingsInterface { background-color: transparent; }"); self.view.setStyleSheet("background-color: transparent;")
        self.vBoxLayout = QVBoxLayout(self.view); self.vBoxLayout.setContentsMargins(36, 20, 36, 36); self.vBoxLayout.setSpacing(20)
        self.vBoxLayout.addWidget(TitleLabel("Configuración", self))
        self._init_automation_section(); self.vBoxLayout.addStretch(1); self._load_current_settings()

    def _init_automation_section(self):
        self.groupAuto = SettingCardGroup("Piloto Automático", self)
        self.cardFase1 = SettingCard(FIF.SEARCH, "Búsqueda Fase 1", "Intervalo en horas (0 = Off)")
        self.spinFase1 = SpinBox(); self.spinFase1.setRange(0, 24); self.spinFase1.setFixedWidth(100); self.spinFase1.valueChanged.connect(lambda v: self._save_automation("auto_fase1_intervalo_horas", v))
        self.cardFase1.hBoxLayout.addWidget(self.spinFase1); self.cardFase1.hBoxLayout.addSpacing(16); self.groupAuto.addSettingCard(self.cardFase1)
        self.cardFase2 = SettingCard(FIF.SYNC, "Actualización Fase 2", "Intervalo en minutos (0 = Off)")
        self.spinFase2 = SpinBox(); self.spinFase2.setRange(0, 120); self.spinFase2.setFixedWidth(100); self.spinFase2.valueChanged.connect(lambda v: self._save_automation("auto_fase2_intervalo_minutos", v))
        self.cardFase2.hBoxLayout.addWidget(self.spinFase2); self.cardFase2.hBoxLayout.addSpacing(16); self.groupAuto.addSettingCard(self.cardFase2)
        self.vBoxLayout.addWidget(self.groupAuto)

    def _load_current_settings(self):
        self.settings_manager.load_settings()
        f1 = self.settings_manager.get_setting("auto_fase1_intervalo_horas")
        f2 = self.settings_manager.get_setting("auto_fase2_intervalo_minutos")
        self.spinFase1.setValue(int(f1) if f1 else 0)
        self.spinFase2.setValue(int(f2) if f2 else 0)

    def _save_automation(self, key, value):
        self.settings_manager.set_setting(key, value)
        self.settings_changed.emit()