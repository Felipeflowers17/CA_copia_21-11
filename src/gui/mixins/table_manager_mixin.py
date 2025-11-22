# -*- coding: utf-8 -*-
from datetime import datetime, date
from PySide6.QtWidgets import (
    QWidget, QTableView, QAbstractItemView, QHeaderView
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor, QBrush, QFont
from PySide6.QtCore import Qt
from typing import List

from src.utils.logger import configurar_logger
from src.db.db_models import CaLicitacion
from src.gui.delegates import ElidedTextDelegate

logger = configurar_logger(__name__)

COLUMN_HEADERS_UNIFIED = [
    "Score", "Nombre", "Organismo", "Estado", "Fecha Pub.", "Fecha Cierre", "Monto", "Prov."
]
COLUMN_HEADERS = COLUMN_HEADERS_UNIFIED

class TableManagerMixin:
    
    def _crear_pestaña_tabla(self, placeholder: str, tab_id: str):
        return QWidget(), None, None, None

    def crear_tabla_view(self, model: QStandardItemModel, tab_id: str) -> QTableView:
        table_view = QTableView()
        table_view.setModel(model)
        
        table_view.setObjectName(tab_id)
        
        table_view.setSortingEnabled(True)
        table_view.sortByColumn(0, Qt.SortOrder.DescendingOrder) 
        
        table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table_view.setAlternatingRowColors(True)
        table_view.verticalHeader().setDefaultSectionSize(38)
        table_view.verticalHeader().hide()
        
        delegate = ElidedTextDelegate(table_view)
        table_view.setItemDelegateForColumn(1, delegate)
        table_view.setItemDelegateForColumn(2, delegate)

        header = table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed); table_view.setColumnWidth(0, 60)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents) 
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed); table_view.setColumnWidth(6, 110)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed); table_view.setColumnWidth(7, 50)

        return table_view

    def poblar_tabla(self, model: QStandardItemModel, data: List[CaLicitacion]):
        model.clear()
        model.setHorizontalHeaderLabels(COLUMN_HEADERS_UNIFIED)
        bold_font = QFont(); bold_font.setBold(True)

        for licitacion in data:
            # --- 0. SCORE ---
            score_item = QStandardItem()
            score_val = licitacion.puntuacion_final or 0
            score_item.setData(score_val, Qt.ItemDataRole.DisplayRole)
            score_item.setData(licitacion.ca_id, Qt.UserRole)
            
            detalles = getattr(licitacion, 'puntaje_detalle', []) or []
            if detalles and len(detalles) > 0:
                tooltip_text = "<b>Desglose del Puntaje:</b><br>"
                for det in detalles:
                    det_clean = str(det).replace("🏢", "").replace("🔑", "").strip()
                    tooltip_text += f"• {det_clean}<br>"
                score_item.setToolTip(tooltip_text)
            else:
                score_item.setToolTip("Sin detalle disponible")
            
            if score_val >= 10:
                score_item.setBackground(QBrush(QColor(220, 255, 220)))

            # --- 1. NOMBRE ---
            nombre_item = QStandardItem(licitacion.nombre)
            if (licitacion.seguimiento and (licitacion.seguimiento.es_favorito or licitacion.seguimiento.es_ofertada)):
                nombre_item.setFont(bold_font)
            
            search_data = f"{licitacion.codigo_ca} {licitacion.nombre} {licitacion.organismo.nombre if licitacion.organismo else ''}".lower()
            nombre_item.setData(search_data, Qt.UserRole)
            nombre_item.setData(licitacion.codigo_ca, Qt.UserRole + 1)
            
            # --- 2. ORGANISMO ---
            org_nombre = licitacion.organismo.nombre if licitacion.organismo else "No Especificado"
            organismo_item = QStandardItem(org_nombre)

            # --- 3. ESTADO ---
            estado_str = licitacion.estado_ca_texto or "N/A"
            if licitacion.estado_convocatoria == 2: estado_str += " (2°)"
            estado_item = QStandardItem(estado_str)
            # Guardamos ID convocatoria y Texto puro para filtros
            estado_item.setData(licitacion.estado_convocatoria, Qt.UserRole)
            estado_item.setData(licitacion.estado_ca_texto, Qt.UserRole + 2)

            # --- 4. FECHA PUB ---
            f_pub = licitacion.fecha_publicacion
            pub_str = f_pub.strftime("%d-%m") if f_pub else "-"
            pub_item = QStandardItem(pub_str)
            # CRITICO: Guardamos el objeto date real para filtrar por calendario
            pub_item.setData(f_pub, Qt.UserRole)

            # --- 5. FECHA CIERRE ---
            f_cierre = licitacion.fecha_cierre
            cierre_str = f_cierre.strftime("%d-%m %H:%M") if f_cierre else "-"
            cierre_item = QStandardItem(cierre_str)
            # CRITICO: Guardamos el objeto datetime real para filtrar por calendario
            cierre_item.setData(f_cierre, Qt.UserRole)

            # --- 6. MONTO ---
            monto_val = licitacion.monto_clp or 0
            monto_item = QStandardItem(f"$ {int(monto_val):,}".replace(",", ".") if monto_val else "-")
            monto_item.setData(monto_val, Qt.UserRole)

            # --- 7. PROVEEDORES ---
            prov_item = QStandardItem()
            prov_item.setData(licitacion.proveedores_cotizando or 0, Qt.ItemDataRole.DisplayRole)

            model.appendRow([score_item, nombre_item, organismo_item, estado_item, pub_item, cierre_item, monto_item, prov_item])

    def filter_table_view(
        self, 
        table_view: QTableView, 
        text: str, 
        only_2nd: bool, 
        min_amount: int,
        show_zeros: bool = False, 
        selected_states: list = None,
        # Nuevos Argumentos de Fecha
        pub_date_from: date = None,
        pub_date_to: date = None,
        close_date_from: date = None,
        close_date_to: date = None
    ):
        model = table_view.model()
        if not model: return
        
        filter_text = text.lower()
        selected_states = selected_states or []
        
        IDX_SCORE, IDX_NOMBRE, IDX_ESTADO, IDX_PUB, IDX_CIERRE, IDX_MONTO = 0, 1, 3, 4, 5, 6

        for row in range(model.rowCount()):
            should_show = True
            
            # 1. Filtro Ceros
            if not show_zeros:
                try:
                    if int(model.item(row, IDX_SCORE).data(Qt.ItemDataRole.DisplayRole) or 0) == 0: should_show = False
                except: pass
            
            # 2. Filtro Estados (Lista)
            if should_show and selected_states:
                estado_row = model.item(row, IDX_ESTADO).data(Qt.UserRole + 2)
                if estado_row not in selected_states: should_show = False

            # 3. Filtro Texto
            if should_show and filter_text:
                if filter_text not in str(model.item(row, IDX_NOMBRE).data(Qt.UserRole) or ""): should_show = False

            # 4. 2do Llamado (Checkbox dentro de estados o global)
            if should_show and only_2nd:
                 if int(model.item(row, IDX_ESTADO).data(Qt.UserRole) or 0) != 2: should_show = False
            
            # 5. Monto
            if should_show and min_amount > 0:
                if float(model.item(row, IDX_MONTO).data(Qt.UserRole) or 0) < min_amount: should_show = False

            # 6. FECHA PUBLICACION (Rango)
            if should_show and (pub_date_from or pub_date_to):
                row_date = model.item(row, IDX_PUB).data(Qt.UserRole) # Es un objeto date
                if not row_date:
                    should_show = False
                else:
                    if pub_date_from and row_date < pub_date_from: should_show = False
                    if pub_date_to and row_date > pub_date_to: should_show = False

            # 7. FECHA CIERRE (Rango)
            if should_show and (close_date_from or close_date_to):
                row_datetime = model.item(row, IDX_CIERRE).data(Qt.UserRole) # Es un objeto datetime
                if not row_datetime:
                    should_show = False
                else:
                    row_date_only = row_datetime.date()
                    if close_date_from and row_date_only < close_date_from: should_show = False
                    if close_date_to and row_date_only > close_date_to: should_show = False

            table_view.setRowHidden(row, not should_show)