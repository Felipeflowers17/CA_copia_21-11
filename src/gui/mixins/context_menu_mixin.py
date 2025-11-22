# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt
from src.utils.logger import configurar_logger
import webbrowser

logger = configurar_logger(__name__)

class ContextMenuMixin:
    """
    Maneja los menús de clic derecho para las tablas.
    Actualizado para soportar ProxyModel (usando data() e index() en lugar de item()).
    """

    def mostrar_menu_contextual(self, pos):
        sender_table = self.sender()
        if not sender_table: return

        index = sender_table.indexAt(pos)
        if not index.isValid(): return
        
        row = index.row()
        model = sender_table.model()
        
        # --- CORRECCIÓN: Usar métodos abstractos compatibles con ProxyModel ---
        
        # 1. Obtener el Código CA
        # En TableManagerMixin, guardamos el código en la Columna 1 (Nombre), bajo UserRole + 1
        idx_nombre = model.index(row, 1)
        codigo_ca = model.data(idx_nombre, Qt.UserRole + 1)
        
        # Fallback por si falla la carga del dato específico, intentamos el texto visible
        if not codigo_ca:
            codigo_ca = model.data(idx_nombre, Qt.DisplayRole)

        # 2. Obtener el ID Interno (ca_id)
        # Guardado en la Columna 0 (Score), bajo UserRole
        idx_score = model.index(row, 0)
        ca_id = model.data(idx_score, Qt.UserRole)

        if not ca_id: 
            return

        # ---------------------------------------------------------------------

        menu = QMenu(self)
        table_name = sender_table.objectName()
        
        # Convertir a string por seguridad
        codigo_str = str(codigo_ca) if codigo_ca else ""

        # --- Pestaña 1: CANDIDATAS ---
        if table_name == "tab_unified": 
            act_web = QAction("Ver ficha en Web", self)
            act_web.triggered.connect(lambda: self.abrir_link_web(codigo_str))
            menu.addAction(act_web)

            menu.addSeparator()

            act_fav = QAction("Favoritos", self)
            act_fav.triggered.connect(lambda: self.gestionar_estado(ca_id, "favorito", True))
            menu.addAction(act_fav)
            
            act_ofer = QAction("Ofertadas", self)
            act_ofer.triggered.connect(lambda: self.gestionar_estado(ca_id, "ofertada", True))
            menu.addAction(act_ofer)
            
            menu.addSeparator()
            
            act_hide = QAction("Ocultar", self)
            act_hide.triggered.connect(lambda: self.gestionar_ocultar(ca_id))
            menu.addAction(act_hide)

        # --- Pestaña 2: SEGUIMIENTO (Favoritas) ---
        elif table_name == "tab_seguimiento":
            act_web = QAction("Ver ficha en Web", self)
            act_web.triggered.connect(lambda: self.abrir_link_web(codigo_str))
            menu.addAction(act_web)
            
            menu.addSeparator()

            act_unfav = QAction("Quitar de Favoritos", self)
            act_unfav.triggered.connect(lambda: self.gestionar_estado(ca_id, "favorito", False))
            menu.addAction(act_unfav)

        # --- Pestaña 3: OFERTADAS ---
        elif table_name == "tab_ofertadas":
            act_web = QAction("Ver ficha en Web", self)
            act_web.triggered.connect(lambda: self.abrir_link_web(codigo_str))
            menu.addAction(act_web)

            menu.addSeparator()
            
            act_unofer = QAction("Quitar de Ofertadas", self)
            act_unofer.triggered.connect(lambda: self.gestionar_estado(ca_id, "ofertada", False))
            menu.addAction(act_unofer)

        menu.exec(sender_table.viewport().mapToGlobal(pos))

    def gestionar_estado(self, ca_id, tipo, estado):
        logger.info(f"Cambiando estado {tipo}={estado} para ID {ca_id}")
        def task():
            if tipo == "favorito":
                self.db_service.gestionar_favorito(ca_id, estado)
            elif tipo == "ofertada":
                self.db_service.gestionar_ofertada(ca_id, estado)
        self.start_task(task=task, on_finished=self.on_load_data_thread)

    def gestionar_ocultar(self, ca_id):
        logger.info(f"Ocultando ID {ca_id}")
        def task():
            self.db_service.ocultar_licitacion(ca_id)
        self.start_task(task=task, on_finished=self.on_load_data_thread)

    def abrir_link_web(self, codigo_ca):
        if not codigo_ca: return
        # Limpieza básica por si el código viene sucio
        clean_code = codigo_ca.split(" ")[0].strip()
        url = f"https://buscador.mercadopublico.cl/ficha?code={clean_code}"
        webbrowser.open(url)