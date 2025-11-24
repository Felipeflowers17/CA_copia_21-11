# -*- coding: utf-8 -*-
from PySide6.QtGui import QStandardItem, QBrush, QColor
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableView, QHeaderView, QAbstractItemView

COLUMN_HEADERS = [
    "Score", 
    "Nombre", 
    "Organismo", 
    "Estado", 
    "Fecha Pub.", 
    "Fecha Cierre", 
    "Monto"
]

class TableManagerMixin:
    def crear_tabla_view(self, model, object_name):
        table = QTableView(self)
        table.setObjectName(object_name)
        table.setModel(model)
        
        model.setHorizontalHeaderLabels(COLUMN_HEADERS)
        
        # Configuración de comportamiento
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.horizontalHeader().setStretchLastSection(True)
        
        # Configuración de anchos
        table.setColumnWidth(0, 60)   # Score
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch) # Nombre
        table.setColumnWidth(2, 180)  # Organismo
        table.setColumnWidth(3, 100)  # Estado
        table.setColumnWidth(4, 90)   # Fecha Pub
        table.setColumnWidth(5, 110)  # Fecha Cierre
        table.setColumnWidth(6, 100)  # Monto
        
        table.setSortingEnabled(True)
        
        # --- CRÍTICO: Habilitar menú contextual (Click Derecho) ---
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        # ----------------------------------------------------------

        from src.gui.delegates import ElidedTextDelegate
        table.setItemDelegateForColumn(1, ElidedTextDelegate(table))
        table.setItemDelegateForColumn(2, ElidedTextDelegate(table))
        
        return table

    def poblar_tabla(self, model, data_list):
        model.removeRows(0, model.rowCount())
        
        for data in data_list:
            # Score
            score = getattr(data, 'puntuacion_final', 0)
            item_score = QStandardItem(str(score))
            item_score.setData(score, Qt.DisplayRole) 
            # ID oculto para lógica de negocio (Doble click, Menú contextual)
            item_score.setData(getattr(data, 'ca_id', None), Qt.UserRole + 1)
            
            # --- RECUPERAR TOOLTIP (Detalle del puntaje) ---
            detalles = getattr(data, 'puntaje_detalle', [])
            if detalles and isinstance(detalles, list):
                tooltip_text = "\n".join(str(d) for d in detalles)
                item_score.setToolTip(tooltip_text)
            # -----------------------------------------------
            
            # Colores (Solo celda Score)
            bg_color = None
            if score >= 500: bg_color = QColor("#dff6dd") 
            elif score >= 10: bg_color = QColor("#e6f7ff") 
            elif score == 0: bg_color = QColor("#ffffff") 
            elif score < 0: bg_color = QColor("#ffe6e6") 
            
            if bg_color: item_score.setBackground(QBrush(bg_color))

            # Nombre
            nombre = getattr(data, 'nombre', 'Sin Nombre') or 'Sin Nombre'
            item_nombre = QStandardItem(nombre)
            item_nombre.setToolTip(nombre)
            item_nombre.setData(nombre, Qt.UserRole)

            # Organismo
            org_obj = getattr(data, 'organismo', None)
            org_nombre = org_obj.nombre if org_obj else 'N/A'
            item_org = QStandardItem(org_nombre)
            item_org.setToolTip(org_nombre)
            item_org.setData(org_nombre, Qt.UserRole) 

            # Estado
            estado_txt = getattr(data, 'estado_ca_texto', 'N/A') or 'N/A'
            item_estado = QStandardItem(estado_txt)
            item_estado.setData(getattr(data, 'estado_convocatoria', 0), Qt.UserRole)
            item_estado.setData(estado_txt, Qt.UserRole + 2)

            # Fecha Pub
            f_pub = getattr(data, 'fecha_publicacion', None)
            f_pub_str = f_pub.strftime("%d-%m") if f_pub else ""
            item_fpub = QStandardItem(f_pub_str)
            item_fpub.setData(f_pub, Qt.UserRole)

            # Fecha Cierre
            f_cierre = getattr(data, 'fecha_cierre', None)
            f_cierre_str = f_cierre.strftime("%d-%m %H:%M") if f_cierre else ""
            item_fcierre = QStandardItem(f_cierre_str)
            item_fcierre.setData(f_cierre, Qt.UserRole)

            # Monto
            monto = getattr(data, 'monto_clp', 0)
            monto_val = float(monto) if monto is not None else 0
            monto_str = f"${int(monto_val):,}".replace(",", ".") if monto is not None else "N/A"
            item_monto = QStandardItem(monto_str)
            item_monto.setData(monto_val, Qt.UserRole)

            row_items = [
                item_score, 
                item_nombre, 
                item_org, 
                item_estado, 
                item_fpub, 
                item_fcierre, 
                item_monto
            ]
            
            model.appendRow(row_items)