# -*- coding: utf-8 -*-
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List

import pandas as pd

from src.db.session import SessionLocal
from src.db.db_models import (
    CaLicitacion, CaSector, CaOrganismo, 
    CaSeguimiento, CaKeyword, CaOrganismoRegla
)

if TYPE_CHECKING:
    from src.db.db_service import DbService

from src.utils.logger import configurar_logger

logger = configurar_logger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]


class ExcelService:
    def __init__(self, db_service: "DbService"):
        self.db_service = db_service
        logger.info("ExcelService inicializado.")

    def ejecutar_exportacion_lote(self, lista_tareas: List[Dict], base_path: str) -> List[str]:
        """
        Ejecuta múltiples exportaciones dentro de una carpeta organizada por fecha.
        Estructura: base_path/export/YYYYMMDD_HHMMSS/archivos...
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Crear estructura de carpetas
        try:
            export_root = Path(base_path) / "export"
            session_folder = export_root / timestamp
            os.makedirs(session_folder, exist_ok=True)
        except Exception as e:
            return [f"ERROR CRÍTICO: No se pudo crear carpeta en {base_path}: {e}"]

        resultados = []
        for tarea in lista_tareas:
            tipo = tarea["tipo"]
            formato = tarea["format"]
            
            try:
                ruta = ""
                if tipo == "tabs":
                    ruta = self.generar_reporte_pestañas(tarea, session_folder)
                elif tipo == "config":
                    ruta = self.generar_reporte_configuracion(formato, session_folder)
                elif tipo == "bd_full":
                    ruta = self.generar_reporte_bd_completa(formato, session_folder)
                
                if ruta:
                    resultados.append(f"[{tipo.upper()} - {formato.upper()}] -> {ruta}")
                else:
                    resultados.append(f"ERROR [{tipo.upper()}] -> Ruta vacía.")

            except Exception as e:
                logger.error(f"Error en lote ({tipo}): {e}", exc_info=True)
                resultados.append(f"ERROR [{tipo.upper()}] -> {str(e)}")
        
        return resultados

    def _convertir_a_dataframe(self, datos_dict: List[Dict]) -> pd.DataFrame:
        datos = []
        for item in datos_dict:
            # Manejo seguro de fechas y zonas horarias
            f_cierre = item.get("fecha_cierre")
            f_cierre_2 = item.get("fecha_cierre_segundo_llamado")
            
            fecha_cierre_ingenua = f_cierre.replace(tzinfo=None) if f_cierre else None
            fecha_cierre_2_ingenua = f_cierre_2.replace(tzinfo=None) if f_cierre_2 else None

            datos.append({
                "Score": item.get("puntuacion_final"),
                "Código CA": item.get("codigo_ca"),
                "Nombre": item.get("nombre"),
                "Descripcion": item.get("descripcion"),
                "Organismo": item.get("organismo_nombre"),
                "Dirección Entrega": item.get("direccion_entrega"),
                "Estado": item.get("estado_ca_texto"),
                "Fecha Publicación": item.get("fecha_publicacion"),
                "Fecha Cierre": fecha_cierre_ingenua,
                "Fecha Cierre 2do Llamado": fecha_cierre_2_ingenua,
                "Proveedores": item.get("proveedores_cotizando"),
                "Productos": str(item.get("productos_solicitados")) if item.get("productos_solicitados") else None,
                "Favorito": item.get("es_favorito"),
                "Ofertada": item.get("es_ofertada"),
            })
        
        columnas = [
            "Score", "Código CA", "Nombre", "Descripcion", "Organismo",
            "Dirección Entrega", "Estado", "Fecha Publicación", "Fecha Cierre",
            "Fecha Cierre 2do Llamado", "Productos", "Proveedores",
            "Favorito", "Ofertada"
        ]
        if not datos:
            return pd.DataFrame(columns=columnas)
        return pd.DataFrame(datos).reindex(columns=columnas)

    def generar_reporte_pestañas(self, options: dict, target_dir: Path) -> str:
        formato = options.get("format", "excel")
        dfs_to_export: Dict[str, pd.DataFrame] = {}

        try:
            # Usamos los métodos seguros de DbService que devuelven diccionarios
            datos_tab1 = self.db_service.obtener_datos_exportacion_tab1()
            datos_tab3 = self.db_service.obtener_datos_exportacion_tab3()
            datos_tab4 = self.db_service.obtener_datos_exportacion_tab4()
            
            dfs_to_export["Candidatas"] = self._convertir_a_dataframe(datos_tab1)
            dfs_to_export["Seguimiento"] = self._convertir_a_dataframe(datos_tab3)
            dfs_to_export["Ofertadas"] = self._convertir_a_dataframe(datos_tab4)
        except Exception as e:
            logger.error(f"Error obteniendo datos para reporte: {e}")
            raise e

        return self._guardar_archivos(dfs_to_export, formato, "Reporte_Pestañas", target_dir)

    def generar_reporte_configuracion(self, formato: str, target_dir: Path) -> str:
        logger.info("Exportando Configuración...")
        dfs_to_export = {}
        with SessionLocal() as session:
            # 1. Exportar Keywords (Corregido: Adaptado a la nueva estructura sin 'tipo')
            keywords = session.query(CaKeyword).all()
            data_kw = []
            for k in keywords:
                data_kw.append({
                    "Keyword": k.keyword,
                    "Puntos Nombre": k.puntos_nombre,
                    "Puntos Descripcion": k.puntos_descripcion,
                    "Puntos Productos": k.puntos_productos
                })
            dfs_to_export["Keywords"] = pd.DataFrame(data_kw)
            
            # 2. Exportar Reglas de Organismos
            reglas = session.query(CaOrganismoRegla).all()
            data_org = []
            for r in reglas:
                # Manejo seguro del Enum 'tipo'
                tipo_val = r.tipo.value if hasattr(r.tipo, 'value') else r.tipo
                data_org.append({
                    "Organismo": r.organismo.nombre if r.organismo else "Desconocido",
                    "Tipo Regla": tipo_val,
                    "Puntos": r.puntos
                })
            dfs_to_export["Reglas_Organismos"] = pd.DataFrame(data_org)

        return self._guardar_archivos(dfs_to_export, formato, "Configuracion_Reglas", target_dir)

    def generar_reporte_bd_completa(self, formato: str, target_dir: Path) -> str:
        dfs_to_export = {}
        # Lista de modelos a exportar
        tablas = [CaLicitacion, CaSeguimiento, CaOrganismo, CaSector, CaKeyword, CaOrganismoRegla]
        
        try:
            with SessionLocal() as session:
                connection = session.connection()
                for model in tablas:
                    # Pandas lee SQL directamente
                    df = pd.read_sql_table(model.__tablename__, con=connection)
                    
                    # Limpieza de Zonas Horarias para Excel
                    for col in df.columns:
                        if pd.api.types.is_datetime64_any_dtype(df[col]):
                            try:
                                df[col] = df[col].dt.tz_localize(None)
                            except: pass
                    
                    dfs_to_export[model.__tablename__] = df
        except Exception as e:
            logger.error(f"Error leyendo BD completa: {e}", exc_info=True)
            raise e
            
        return self._guardar_archivos(dfs_to_export, formato, "BD_Completa", target_dir)

    def _guardar_archivos(self, dfs: Dict[str, pd.DataFrame], formato: str, prefijo: str, target_dir: Path) -> str:
        """Guarda los DataFrames en la carpeta indicada (target_dir)."""
        
        if formato == "excel":
            nombre = f"{prefijo}.xlsx"
            ruta = target_dir / nombre
            try:
                with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
                    for sheet, df in dfs.items():
                        # Excel limita nombres de hoja a 31 caracteres
                        safe_sheet = sheet[:30]
                        df.to_excel(writer, sheet_name=safe_sheet, index=False)
                return str(ruta)
            except Exception as e:
                logger.error(f"Error escribiendo Excel {prefijo}: {e}")
                raise e
        else:
            # CSV: Guardamos múltiples archivos
            try:
                for sheet, df in dfs.items():
                    nombre_csv = f"{prefijo}_{sheet}.csv"
                    ruta_csv = target_dir / nombre_csv
                    df.to_csv(ruta_csv, index=False, encoding='utf-8-sig')
                return str(target_dir) 
            except Exception as e:
                logger.error(f"Error escribiendo CSVs {prefijo}: {e}")
                raise e