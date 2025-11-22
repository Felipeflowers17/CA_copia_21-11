# -*- coding: utf-8 -*-
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
        
        table_view.setObjectName(tab_id)
        table_view.setSortingEnabled(True)
        
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
        model.setRowCount(0)
        model.setHorizontalHeaderLabels(COLUMN_HEADERS_UNIFIED)
        bold_font = QFont(); bold_font.setBold(True)

        for licitacion in data:
            score_item = QStandardItem()
            score_val = licitacion.puntuacion_final or 0
            score_item.setData(score_val, Qt.ItemDataRole.DisplayRole)
            score_item.setData(licitacion.ca_id, Qt.UserRole)
            
            detalles = getattr(licitacion, 'puntaje_detalle', []) or []
            if detalles and len(detalles) > 0:
                tooltip_text = "<b>Desglose del Puntaje:</b><br>"
                for det in detalles:
                    det_clean = str(det).replace("<", "").replace(">", "").strip()
                    tooltip_text += f"• {det_clean}<br>"
                score_item.setToolTip(tooltip_text)
            else:
                score_item.setToolTip("Sin detalle disponible")
            
            if score_val >= 10:
                score_item.setBackground(QBrush(QColor(220, 255, 220)))

            nombre_item = QStandardItem(licitacion.nombre)
            if (licitacion.seguimiento and (licitacion.seguimiento.es_favorito or licitacion.seguimiento.es_ofertada)):
                nombre_item.setFont(bold_font)
            
            search_data = f"{licitacion.codigo_ca} {licitacion.nombre} {licitacion.organismo.nombre if licitacion.organismo else ''}".lower()
            nombre_item.setData(search_data, Qt.UserRole)
            nombre_item.setData(licitacion.codigo_ca, Qt.UserRole + 1)
            
            org_nombre = licitacion.organismo.nombre if licitacion.organismo else "No Especificado"
            organismo_item = QStandardItem(org_nombre)

            estado_str = licitacion.estado_ca_texto or "N/A"
            if licitacion.estado_convocatoria == 2: estado_str += " (2°)"
            estado_item = QStandardItem(estado_str)
            estado_item.setData(licitacion.estado_convocatoria, Qt.UserRole)
            estado_item.setData(licitacion.estado_ca_texto, Qt.UserRole + 2)

            f_pub = licitacion.fecha_publicacion
            pub_str = f_pub.strftime("%d-%m") if f_pub else "-"
            pub_item = QStandardItem(pub_str)
            pub_item.setData(f_pub, Qt.UserRole)

            f_cierre = licitacion.fecha_cierre
            cierre_str = f_cierre.strftime("%d-%m %H:%M") if f_cierre else "-"
            cierre_item = QStandardItem(cierre_str)
            cierre_item.setData(f_cierre, Qt.UserRole)

            monto_val = licitacion.monto_clp or 0
            monto_item = QStandardItem(f"$ {int(monto_val):,}".replace(",", ".") if monto_val else "-")
            monto_item.setData(monto_val, Qt.UserRole)

            prov_item = QStandardItem()
            prov_item.setData(licitacion.proveedores_cotizando or 0, Qt.ItemDataRole.DisplayRole)

            model.appendRow([score_item, nombre_item, organismo_item, estado_item, pub_item, cierre_item, monto_item, prov_item])