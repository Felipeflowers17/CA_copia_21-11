# -*- coding: utf-8 -*-
"""
Interfaz de Gestión de Datos (Dashboard).
"""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import (
    ScrollArea, SettingCardGroup, PushSettingCard, FluentIcon as FIF,
    TitleLabel, BodyLabel
)

class DataInterface(ScrollArea):
    request_scraping = Signal()
    request_update_tabs = Signal()
    request_rules_view = Signal()
    request_recalculate = Signal()
    request_export_tabs = Signal()
    request_export_db = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = QWidget(self)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setObjectName("DataInterface")
        self.setStyleSheet("background-color: transparent;")
        self.view.setStyleSheet("background-color: transparent;")

        self.vBoxLayout = QVBoxLayout(self.view)
        self.vBoxLayout.setContentsMargins(36, 20, 36, 36)
        self.vBoxLayout.setSpacing(20)

        self.vBoxLayout.addWidget(TitleLabel("Gestión de Datos", self))
        
        self.groupIn = SettingCardGroup("Entrada de Datos", self)
        self.cardScraping = PushSettingCard("Obtener datos", FIF.DOWNLOAD, "Iniciar Nuevo Scraping (Fase 1)", "Buscar nuevas licitaciones.", self.groupIn)
        self.cardUpdate = PushSettingCard("Actualizar", FIF.SYNC, "Actualizar Pestañas", "Actualizar detalles (Fase 2) de todas las CAs.", self.groupIn)
        self.groupIn.addSettingCard(self.cardScraping)
        self.groupIn.addSettingCard(self.cardUpdate)
        self.vBoxLayout.addWidget(self.groupIn)

        self.groupLogic = SettingCardGroup("Lógica de Negocio", self)
        self.cardRules = PushSettingCard("Editar Reglas", FIF.PEOPLE, "Editar Puntajes y Organismos", "Modificar keywords y organismos.", self.groupLogic)
        self.cardRecalc = PushSettingCard("Recalcular", FIF.EDIT, "Recalcular Puntajes", "Aplicar reglas a datos guardados.", self.groupLogic)
        self.groupLogic.addSettingCard(self.cardRules)
        self.groupLogic.addSettingCard(self.cardRecalc)
        self.vBoxLayout.addWidget(self.groupLogic)
        
        self.groupOut = SettingCardGroup("Reportes", self)
        self.cardExpTabs = PushSettingCard("Exportar Pestañas", FIF.SHARE, "Exportar Vistas", "Generar reporte Excel/CSV.", self.groupOut)
        self.cardExpDB = PushSettingCard("Exportar Todo", FIF.SAVE, "Exportar BD Completa", "Respaldo total.", self.groupOut)
        self.groupOut.addSettingCard(self.cardExpTabs)
        self.groupOut.addSettingCard(self.cardExpDB)
        self.vBoxLayout.addWidget(self.groupOut)
        self.vBoxLayout.addStretch(1)

        self.cardScraping.clicked.connect(self.request_scraping.emit)
        self.cardUpdate.clicked.connect(self.request_update_tabs.emit)
        self.cardRules.clicked.connect(self.request_rules_view.emit)
        self.cardRecalc.clicked.connect(self.request_recalculate.emit)
        self.cardExpTabs.clicked.connect(self.request_export_tabs.emit)
        self.cardExpDB.clicked.connect(self.request_export_db.emit)