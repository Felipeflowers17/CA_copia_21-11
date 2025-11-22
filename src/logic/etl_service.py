# -*- coding: utf-8 -*-
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional, List

if TYPE_CHECKING:
    from src.db.db_service import DbService
    from src.scraper.scraper_service import ScraperService
    from src.logic.score_engine import ScoreEngine

from config.config import MODO_HEADLESS, HEADERS_API
from src.utils.logger import configurar_logger
from src.scraper.url_builder import construir_url_api_ficha
from src.utils.exceptions import (
    ScrapingFase1Error, DatabaseLoadError, DatabaseTransformError,
    ScrapingFase2Error, RecalculoError
)

logger = configurar_logger(__name__)

class EtlService:
    def __init__(self, db_service: "DbService", scraper_service: "ScraperService", score_engine: "ScoreEngine"):
        self.db_service = db_service
        self.scraper_service = scraper_service
        self.score_engine = score_engine
        logger.info("EtlService inicializado.")

    def _create_progress_emitters(self, progress_callback_text, progress_callback_percent):
        def emit_text(msg: str):
            if progress_callback_text: progress_callback_text(msg)
        def emit_percent(val: int):
            if progress_callback_percent: progress_callback_percent(val)
        return emit_text, emit_percent

    def _transform_puntajes_fase_1(self, progress_callback_text=None, progress_callback_percent=None):
        emit_text, emit_percent = self._create_progress_emitters(progress_callback_text, progress_callback_percent)
        try:
            licitaciones = self.db_service.obtener_todas_candidatas_fase_1_para_recalculo()
            if not licitaciones: return
            
            total = len(licitaciones)
            emit_text(f"Recalculando {total} CAs...")
            
            lista = []
            for i, lic in enumerate(licitaciones):
                item = { 
                    'codigo': lic.codigo_ca,
                    'nombre': lic.nombre, 
                    'estado_ca_texto': lic.estado_ca_texto, 
                    'organismo_comprador': lic.organismo.nombre if lic.organismo else "" 
                }
                p, det = self.score_engine.calcular_puntuacion_fase_1(item)
                lista.append((lic.ca_id, p, det))
                
                if i % 100 == 0:
                    emit_percent(int(((i+1)/total)*100))
                
            self.db_service.actualizar_puntajes_fase_1_en_lote(lista)
            
        except Exception as e:
            raise DatabaseTransformError(f"Error cálculo puntajes: {e}") from e

    def run_etl_live_to_db(self, progress_callback_text=None, progress_callback_percent=None, config=None):
        emit_text, emit_percent = self._create_progress_emitters(progress_callback_text, progress_callback_percent)
        date_from, date_to, max_paginas = config["date_from"], config["date_to"], config["max_paginas"]
        
        emit_text("Iniciando Fase 1 (Buscando token)...")
        emit_percent(5)
        
        try:
            filtros = {'date_from': date_from.strftime('%Y-%m-%d'), 'date_to': date_to.strftime('%Y-%m-%d')}
            datos = self.scraper_service.run_scraper_listado(emit_text, filtros, max_paginas)
        except Exception as e:
            raise ScrapingFase1Error(f"Fallo scraping listado: {e}") from e

        if not datos:
            emit_text("No se encontraron datos."); emit_percent(100); return

        emit_percent(20); emit_text(f"Guardando {len(datos)} registros...")
        try:
            self.db_service.insertar_o_actualizar_licitaciones_raw(datos)
        except Exception as e:
            raise DatabaseLoadError(f"Fallo guardado BD: {e}") from e
            
        emit_percent(30); self._transform_puntajes_fase_1(emit_text, emit_percent)
        
        try:
            candidatas = self.db_service.obtener_candidatas_para_fase_2(umbral_minimo=10)
            if candidatas:
                emit_text(f"Iniciando Fase 2 para {len(candidatas)} CAs Top...")
                self._procesar_lista_fase_2(candidatas, emit_text, emit_percent)
            else:
                 logger.info("No hay CAs nuevas con puntaje >= 10 para Fase 2 automática.")
        except Exception as e:
            logger.error(f"Error en Fase 2 automática: {e}") 
            
        emit_text("Proceso Completo."); emit_percent(100)

    def run_recalculo_total_fase_1(self, progress_callback_text=None, progress_callback_percent=None):
        emit_text, emit_percent = self._create_progress_emitters(progress_callback_text, progress_callback_percent)
        try:
            emit_text("Recargando reglas...")
            self.score_engine.recargar_reglas()
            self._transform_puntajes_fase_1(emit_text, emit_percent)
            emit_percent(100)
        except Exception as e:
            raise RecalculoError(f"Fallo recalculo: {e}") from e

    def run_fase2_update(self, progress_callback_text=None, progress_callback_percent=None, scopes: List[str] = None):
        """
        Actualiza las CAs buscando su ficha en la web.
        :param scopes: Lista de strings ['candidatas', 'seguimiento', 'ofertadas'] o None para todo.
        """
        emit_text, emit_percent = self._create_progress_emitters(progress_callback_text, progress_callback_percent)
        
        try:
            emit_text("Seleccionando CAs para actualizar...")
            
            lists_to_process = []
            
            # Si scopes es None o contiene 'all', traemos todo (comportamiento antiguo)
            if not scopes or 'all' in scopes:
                lists_to_process.append(self.db_service.obtener_datos_tab3_seguimiento())
                lists_to_process.append(self.db_service.obtener_datos_tab4_ofertadas())
                lists_to_process.append(self.db_service.obtener_candidatas_top_para_actualizar(umbral_minimo=10))
            else:
                # Comportamiento selectivo
                if 'seguimiento' in scopes:
                    lists_to_process.append(self.db_service.obtener_datos_tab3_seguimiento())
                if 'ofertadas' in scopes:
                    lists_to_process.append(self.db_service.obtener_datos_tab4_ofertadas())
                if 'candidatas' in scopes:
                    lists_to_process.append(self.db_service.obtener_candidatas_top_para_actualizar(umbral_minimo=10))
            
            # Deduplicación (por si una CA está en varias listas lógicas, aunque no debería)
            mapa = {}
            for lst in lists_to_process:
                for ca in lst: mapa[ca.ca_id] = ca
            
            procesar = list(mapa.values())
            
            if not procesar:
                emit_text("No hay licitaciones seleccionadas para actualizar."); emit_percent(100); return

            if not self.scraper_service.headers_sesion:
                 emit_text("Token no disponible. Intentando capturar...")

            emit_text(f"Actualizando {len(procesar)} CAs desde la web...")
            self._procesar_lista_fase_2(procesar, emit_text, emit_percent)
            
        except Exception as e:
             raise ScrapingFase2Error(f"Fallo actualización: {e}") from e
        
        emit_text("Actualización finalizada."); emit_percent(100)

    def _procesar_lista_fase_2(self, lista_cas, emit_text, emit_percent):
        total = len(lista_cas)
        for i, lic in enumerate(lista_cas):
            percent = int(((i+1)/total)*90)
            emit_percent(percent)
            emit_text(f"Actualizando: {lic.codigo_ca}")
            
            url = construir_url_api_ficha(lic.codigo_ca)
            datos = self.scraper_service._fetch_api_con_requests(url)
            
            if datos and datos.get('success') == 'OK' and 'payload' in datos:
                p = datos['payload']
                data_ficha = {
                    'descripcion': p.get('descripcion'),
                    'direccion_entrega': p.get('direccion_entrega'),
                    'fecha_cierre_p1': p.get('fecha_cierre_primer_llamado'),
                    'fecha_cierre_p2': p.get('fecha_cierre_segundo_llamado'),
                    'productos_solicitados': p.get('productos_solicitados', []),
                    'estado': p.get('estado'),
                    'cantidad_provedores_cotizando': p.get('cantidad_provedores_cotizando'),
                    'estado_convocatoria': p.get('estado_convocatoria'),
                    'plazo_entrega': p.get('plazo_entrega')
                }
                
                item_f1 = {'nombre': lic.nombre, 'estado_ca_texto': lic.estado_ca_texto, 'organismo_comprador': lic.organismo.nombre if lic.organismo else ""}
                pts1, _ = self.score_engine.calcular_puntuacion_fase_1(item_f1)
                pts2, det2 = self.score_engine.calcular_puntuacion_fase_2(data_ficha)
                
                self.db_service.actualizar_ca_con_fase_2(lic.codigo_ca, data_ficha, pts1+pts2, det2)
            
            time.sleep(0.5)

    def run_health_check(self, progress_callback_text=None, progress_callback_percent=None):
        return True

    def run_limpieza_automatica(self):
        try: self.db_service.limpiar_registros_antiguos()
        except: pass