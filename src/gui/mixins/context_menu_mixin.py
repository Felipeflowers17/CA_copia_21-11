# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt, Slot, QUrl
from PySide6.QtGui import QDesktopServices, QAction, QIcon
from PySide6.QtWidgets import QMenu, QMessageBox, QWidgetAction, QPushButton
from qfluentwidgets import FluentIcon as FIF
from src.utils.logger import configurar_logger

logger = configurar_logger(__name__)

class ContextMenuMixin:
    """
    Maneja la creación y lógica del menú contextual (clic derecho) en las tablas.
    """

    @Slot(object)
    def mostrar_menu_contextual(self, pos):
        source_view = self.sender()
        if not source_view: return

        index = source_view.indexAt(pos)
        if not index.isValid(): return

        proxy_model = source_view.model()
        row = index.row()
        
        # Recuperar ID
        idx_score = proxy_model.index(row, 0) 
        ca_id = proxy_model.data(idx_score, Qt.UserRole + 1)
        if not ca_id: ca_id = proxy_model.data(idx_score, Qt.UserRole) # Fallback

        if not ca_id:
            logger.warning("Menú Contextual: No se pudo recuperar el ca_id.")
            return

        idx_nombre = proxy_model.index(row, 1)
        nombre_ca = proxy_model.data(idx_nombre, Qt.DisplayRole)
        
        # --- CONSTRUCCIÓN DEL MENÚ VISUAL ---
        menu = QMenu()
        # Estilo base para que se vea limpio
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #f0f0f0;
            }
            QMenu::separator {
                height: 1px;
                background: #e0e0e0;
                margin: 4px 10px;
            }
        """)
        
        # 1. Ver en Web
        # CORRECCIÓN: Se agrega .icon() a FIF.GLOBE
        action_web = QAction(FIF.GLOBE.icon(), "Ver ficha en Web", self)
        action_web.triggered.connect(lambda: self._abrir_web_por_id(ca_id))
        menu.addAction(action_web)
        
        menu.addSeparator()

        # 2. Favoritos
        action_fav = QAction(FIF.HEART.icon(), "Marcar como Favorita", self)
        action_fav.triggered.connect(lambda: self._mover_a_favoritos(ca_id))
        menu.addAction(action_fav)

        action_unfav = QAction(FIF.UNPIN.icon(), "Quitar de Favoritos", self)
        action_unfav.triggered.connect(lambda: self._quitar_de_favoritos(ca_id))
        menu.addAction(action_unfav)
        
        menu.addSeparator()
        
        # 3. Ofertadas
        action_ofertar = QAction(FIF.SHOPPING_CART.icon(), "Marcar como Ofertada", self)
        action_ofertar.triggered.connect(lambda: self._marcar_ofertada(ca_id))
        menu.addAction(action_ofertar)
        
        action_unofertar = QAction(FIF.REMOVE_FROM.icon(), "Desmarcar Ofertada", self)
        action_unofertar.triggered.connect(lambda: self._desmarcar_ofertada(ca_id))
        menu.addAction(action_unofertar)

        menu.addSeparator()
        
        # 4. ACCIÓN ROJA PERSONALIZADA (Usando QWidgetAction)
        # Creamos un botón que parezca un ítem de menú pero rojo
        btn_delete = QPushButton("  Ocultar / Eliminar Licitación")
        btn_delete.setIcon(FIF.DELETE.icon())
        btn_delete.setStyleSheet("""
            QPushButton {
                text-align: left;
                color: #d9534f; /* Rojo suave */
                background-color: transparent;
                border: none;
                padding: 6px 14px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #ffe6e6; /* Fondo rojizo al pasar mouse */
            }
        """)
        # Conectamos el clic del botón a la lógica Y cerramos el menú manualmente
        btn_delete.clicked.connect(lambda: [menu.close(), self._ocultar_licitacion(ca_id, nombre_ca)])
        
        # Insertamos el botón en el menú
        act_widget = QWidgetAction(menu)
        act_widget.setDefaultWidget(btn_delete)
        menu.addAction(act_widget)

        menu.exec(source_view.viewport().mapToGlobal(pos))

    def _abrir_web_por_id(self, ca_id):
        self.start_task(
            task=self.db_service.get_licitacion_by_id,
            on_result=self._open_url_callback,
            task_args=(ca_id,)
        )

    def _open_url_callback(self, licitacion):
        if licitacion and licitacion.codigo_ca:
            url = f"https://buscador.mercadopublico.cl/ficha?code={licitacion.codigo_ca}"
            QDesktopServices.openUrl(QUrl(url))

    def _mover_a_favoritos(self, ca_id):
        self.start_task(
            task=self.db_service.gestionar_favorito,
            on_finished=self.on_load_data_thread,
            task_args=(ca_id, True)
        )

    def _quitar_de_favoritos(self, ca_id):
        self.start_task(
            task=self.db_service.gestionar_favorito,
            on_finished=self.on_load_data_thread,
            task_args=(ca_id, False)
        )

    def _marcar_ofertada(self, ca_id):
        self.start_task(
            task=self.db_service.gestionar_ofertada,
            on_finished=self.on_load_data_thread,
            task_args=(ca_id, True)
        )

    def _desmarcar_ofertada(self, ca_id):
        self.start_task(
            task=self.db_service.gestionar_ofertada,
            on_finished=self.on_load_data_thread,
            task_args=(ca_id, False)
        )

    def _ocultar_licitacion(self, ca_id, nombre):
        confirm = QMessageBox.question(
            self, "Confirmar Eliminación",
            f"¿Estás seguro de ocultar/eliminar la licitación?\n\n{nombre}",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.start_task(
                task=self.db_service.eliminar_ca_definitivamente,
                on_finished=self.on_load_data_thread,
                task_args=(ca_id,)
            )