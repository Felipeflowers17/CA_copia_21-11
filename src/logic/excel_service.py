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

# BASE_DIR se mantiene para referencia interna, pero EXPORTS_DIR ya no se usa para exportaciones de usuario
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

    def _convertir_a_dataframe(self, licitaciones: list[CaLicitacion]) -> pd.DataFrame:
        datos = []
        for ca in licitaciones:
            fecha_cierre_ingenua = ca.fecha_cierre.replace(tzinfo=None) if ca.fecha_cierre else None
            fecha_cierre_2_ingenua = ca.fecha_cierre_segundo_llamado.replace(tzinfo=None) if ca.fecha_cierre_segundo_llamado else None

            datos.append({
                "Score": ca.puntuacion_final,
                "Código CA": ca.codigo_ca,
                "Nombre": ca.nombre,
                "Descripcion": ca.descripcion,
                "Organismo": ca.organismo.nombre if ca.organismo else "N/A",
                "Dirección Entrega": ca.direccion_entrega,
                "Estado": ca.estado_ca_texto,
                "Fecha Publicación": ca.fecha_publicacion,
                "Fecha Cierre": fecha_cierre_ingenua,
                "Fecha Cierre 2do Llamado": fecha_cierre_2_ingenua,
                "Proveedores": ca.proveedores_cotizando,
                "Productos": str(ca.productos_solicitados) if ca.productos_solicitados else None,
                "Favorito": ca.seguimiento.es_favorito if ca.seguimiento else False,
                "Ofertada": ca.seguimiento.es_ofertada if ca.seguimiento else False,
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
            datos_tab1 = self.db_service.obtener_candidatas_unificadas()
            datos_tab3 = self.db_service.obtener_datos_tab3_seguimiento()
            datos_tab4 = self.db_service.obtener_datos_tab4_ofertadas()
            
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
            keywords = session.query(CaKeyword).all()
            data_kw = [{"Keyword": k.keyword, "Tipo": k.tipo, "Puntos": k.puntos} for k in keywords]
            dfs_to_export["Keywords"] = pd.DataFrame(data_kw)
            
            reglas = session.query(CaOrganismoRegla).all()
            data_org = []
            for r in reglas:
                data_org.append({
                    "Organismo": r.organismo.nombre,
                    "Tipo Regla": r.tipo.value,
                    "Puntos": r.puntos
                })
            dfs_to_export["Reglas_Organismos"] = pd.DataFrame(data_org)

        return self._guardar_archivos(dfs_to_export, formato, "Configuracion_Reglas", target_dir)

    def generar_reporte_bd_completa(self, formato: str, target_dir: Path) -> str:
        dfs_to_export = {}
        tablas = [CaLicitacion, CaSeguimiento, CaOrganismo, CaSector, CaKeyword, CaOrganismoRegla]
        
        try:
            with SessionLocal() as session:
                connection = session.connection()
                for model in tablas:
                    df = pd.read_sql_table(model.__tablename__, con=connection)
                    
                    # Limpieza Zonas Horarias
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
                        safe_sheet = sheet[:30]
                        df.to_excel(writer, sheet_name=safe_sheet, index=False)
                return str(ruta)
            except Exception as e:
                logger.error(f"Error escribiendo Excel {prefijo}: {e}")
                raise e
        else:
            # CSV: Los guardamos directamente en la carpeta target_dir con el prefijo
            try:
                for sheet, df in dfs.items():
                    nombre_csv = f"{prefijo}_{sheet}.csv"
                    ruta_csv = target_dir / nombre_csv
                    df.to_csv(ruta_csv, index=False, encoding='utf-8-sig')
                return str(target_dir) # Retornamos la carpeta
            except Exception as e:
                logger.error(f"Error escribiendo CSVs {prefijo}: {e}")
                raise e