# -*- coding: utf-8 -*-
from typing import List, Dict, Tuple, Optional, Union
from datetime import datetime, timedelta 
from sqlalchemy.orm import sessionmaker, Session, joinedload
from sqlalchemy import select, delete, or_, update, and_

from .db_models import (
    CaLicitacion,
    CaSeguimiento,
    CaOrganismo,
    CaSector,
    CaKeyword,
    CaOrganismoRegla,      
)

from config.config import UMBRAL_FASE_1, UMBRAL_FINAL_RELEVANTE
from src.utils.logger import configurar_logger

logger = configurar_logger(__name__)

class DbService:
    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory
        logger.info("DbService inicializado.")

    def _get_or_create_organismo_sector(
        self, session: Session, nombre_organismo: str, nombre_sector: str
    ) -> CaOrganismo:
        if not nombre_sector: nombre_sector = "No Especificado"
        nombre_sector_norm = nombre_sector.strip()
        nombre_organismo_norm = nombre_organismo.strip()
        
        stmt_sector = select(CaSector).where(CaSector.nombre == nombre_sector_norm)
        sector = session.scalars(stmt_sector).first()
        if not sector:
            sector = CaSector(nombre=nombre_sector_norm)
            session.add(sector)
            session.flush()
            
        if not nombre_organismo_norm: nombre_organismo_norm = "Organismo No Especificado"
            
        stmt_org = select(CaOrganismo).where(CaOrganismo.nombre == nombre_organismo_norm)
        organismo = session.scalars(stmt_org).first()
        if not organismo:
            organismo = CaOrganismo(nombre=nombre_organismo_norm, sector_id=sector.sector_id)
            session.add(organismo)
            session.flush()
        return organismo

    def insertar_o_actualizar_licitaciones_raw(self, compras: List[Dict]):
        logger.info(f"Iniciando (ELT) Carga de {len(compras)} CAs crudas...")
        codigos_procesados = set()
        nuevos_inserts = 0
        actualizaciones = 0
        
        with self.session_factory() as session:
            try:
                for item in compras:
                    codigo = item.get("codigo", item.get("id"))
                    if not codigo: continue
                    if codigo in codigos_procesados: continue
                    codigos_procesados.add(codigo)
                    
                    nombre_org_raw = item.get("organismo", "No Especificado")
                    nombre_sec_raw = item.get("unidad", "No Especificado")
                    organismo_db = self._get_or_create_organismo_sector(session, nombre_org_raw, nombre_sec_raw)
                    
                    stmt = select(CaLicitacion).where(CaLicitacion.codigo_ca == codigo)
                    licitacion_existente = session.scalars(stmt).first()
                    
                    estado_convocatoria_val = item.get("estado_convocatoria")
                    
                    if licitacion_existente:
                        licitacion_existente.proveedores_cotizando = item.get("cantidad_provedores_cotizando")
                        licitacion_existente.estado_ca_texto = item.get("estado")
                        licitacion_existente.fecha_cierre = item.get("fecha_cierre")
                        if estado_convocatoria_val is not None:
                            licitacion_existente.estado_convocatoria = estado_convocatoria_val
                        actualizaciones += 1
                    else:
                        nueva_licitacion = CaLicitacion(
                            codigo_ca=codigo,
                            nombre=item.get("nombre"),
                            monto_clp=item.get("monto_disponible_CLP"),
                            fecha_publicacion=item.get("fecha_publicacion"),
                            fecha_cierre=item.get("fecha_cierre"),
                            proveedores_cotizando=item.get("cantidad_provedores_cotizando"),
                            estado_ca_texto=item.get("estado"),
                            estado_convocatoria=estado_convocatoria_val,
                            organismo_id=organismo_db.organismo_id,
                            puntuacion_final=0,
                            puntaje_detalle=[] 
                        )
                        session.add(nueva_licitacion)
                        nuevos_inserts += 1
                session.commit()
                logger.info(f"Carga (L) exitosa: {nuevos_inserts} nuevos, {actualizaciones} actualizados.")
            except Exception as e:
                logger.error(f"Error al hacer commit en lote (Carga): {e}", exc_info=True)
                session.rollback()
                raise e
    
    def obtener_candidatas_para_recalculo_fase_1(self) -> List[CaLicitacion]:
        with self.session_factory() as session:
            stmt = select(CaLicitacion).where(
                CaLicitacion.puntuacion_final == 0,
                CaLicitacion.descripcion.is_(None)
            ).options(
                joinedload(CaLicitacion.organismo),
                joinedload(CaLicitacion.seguimiento)
            )
            return session.scalars(stmt).all()

    def obtener_todas_candidatas_fase_1_para_recalculo(self) -> List[CaLicitacion]:
        with self.session_factory() as session:
            stmt = select(CaLicitacion).options(
                joinedload(CaLicitacion.organismo),
                joinedload(CaLicitacion.seguimiento)
            )
            return session.scalars(stmt).all()
    
    def actualizar_puntajes_fase_1_en_lote(self, actualizaciones: List[Union[Tuple[int, int], Tuple[int, int, List[str]]]]):
        if not actualizaciones: return
        
        datos_mapeados = []
        for item in actualizaciones:
            if len(item) == 3:
                ca_id, puntaje, detalle = item
            elif len(item) == 2:
                ca_id, puntaje = item
                detalle = ["Sin detalle (Recálculo antiguo)"]
            else: continue
                
            datos_mapeados.append({ "ca_id": ca_id, "puntuacion_final": puntaje, "puntaje_detalle": detalle })

        with self.session_factory() as session:
            try:
                session.bulk_update_mappings(CaLicitacion, datos_mapeados)
                session.commit()
            except Exception as e:
                logger.error(f"Error en la actualización de puntajes en lote: {e}")
                session.rollback()
                raise

    def obtener_candidatas_para_fase_2(self, umbral_minimo: int = 10) -> List[CaLicitacion]:
        with self.session_factory() as session:
            stmt = (
                select(CaLicitacion)
                .filter(
                    CaLicitacion.puntuacion_final >= umbral_minimo,
                    CaLicitacion.descripcion.is_(None)
                )
                .order_by(CaLicitacion.fecha_cierre.asc())
            )
            candidatas = session.scalars(stmt).all()
            logger.info(f"Se encontraron {len(candidatas)} CAs 'Top' (>{umbral_minimo}pts) para Fase 2 automática.")
            return candidatas

    def obtener_candidatas_top_para_actualizar(self, umbral_minimo: int = 10) -> List[CaLicitacion]:
        with self.session_factory() as session:
            subq_seguimiento = select(CaSeguimiento.ca_id).where(
                or_(CaSeguimiento.es_favorito == True, CaSeguimiento.es_ofertada == True)
            )
            stmt = (
                select(CaLicitacion)
                .filter(
                    CaLicitacion.puntuacion_final >= umbral_minimo,
                    CaLicitacion.ca_id.notin_(subq_seguimiento)
                )
                .order_by(CaLicitacion.fecha_cierre.asc())
            )
            return session.scalars(stmt).all()

    def actualizar_ca_con_fase_2(
        self, codigo_ca: str, datos_fase_2: Dict, puntuacion_total: int, detalle_extra: List[str]
    ):
        with self.session_factory() as session:
            try:
                stmt = select(CaLicitacion).where(CaLicitacion.codigo_ca == codigo_ca)
                licitacion = session.scalars(stmt).first()
                
                if not licitacion: return

                licitacion.descripcion = datos_fase_2.get("descripcion")
                licitacion.productos_solicitados = datos_fase_2.get("productos_solicitados")
                licitacion.direccion_entrega = datos_fase_2.get("direccion_entrega")
                licitacion.puntuacion_final = puntuacion_total
                licitacion.plazo_entrega = datos_fase_2.get("plazo_entrega")
                
                detalle_actual = licitacion.puntaje_detalle or []
                if not isinstance(detalle_actual, list): detalle_actual = []
                licitacion.puntaje_detalle = detalle_actual + detalle_extra
                
                licitacion.fecha_cierre_segundo_llamado = datos_fase_2.get("fecha_cierre_p2")
                
                estado_conv_f2 = datos_fase_2.get("estado_convocatoria")
                if estado_conv_f2 is not None:
                     licitacion.estado_convocatoria = estado_conv_f2

                session.commit()
            except Exception as e:
                logger.error(f"[Fase 2] Error al actualizar CA {codigo_ca}: {e}")
                session.rollback()
                raise

    def get_licitacion_by_id(self, ca_id: int) -> Optional[CaLicitacion]:
        with self.session_factory() as session:
            stmt = select(CaLicitacion).options(
                joinedload(CaLicitacion.organismo),
                joinedload(CaLicitacion.seguimiento)
            ).where(CaLicitacion.ca_id == ca_id)
            return session.scalars(stmt).first()

    def limpiar_registros_antiguos(self, dias_retencion: int = 30) -> int:
        fecha_limite = datetime.now() - timedelta(days=dias_retencion)
        registros_eliminados = 0
        with self.session_factory() as session:
            try:
                subquery_favoritos = select(CaSeguimiento.ca_id).where(CaSeguimiento.es_favorito == True)
                stmt_delete = delete(CaLicitacion).where(
                    CaLicitacion.fecha_cierre < fecha_limite,
                    CaLicitacion.estado_ca_texto.notin_(['Publicada', 'Publicada - Segundo llamado']),
                    or_(CaLicitacion.estado_convocatoria.is_(None), CaLicitacion.estado_convocatoria != 2),
                    CaLicitacion.ca_id.notin_(subquery_favoritos)
                )
                result = session.execute(stmt_delete)
                registros_eliminados = result.rowcount
                session.commit()
                if registros_eliminados > 0:
                    logger.info(f"Limpieza automática: Se eliminaron {registros_eliminados} CAs antiguas.")
            except Exception as e:
                logger.error(f"Error durante la limpieza automática de BD: {e}")
                session.rollback()
        return registros_eliminados

    def obtener_datos_tab1_candidatas(self, umbral_minimo: int = 5) -> List[CaLicitacion]:
        with self.session_factory() as session:
            subquery_seguimiento = select(CaSeguimiento.ca_id).where(
                or_(CaSeguimiento.es_favorito == True, CaSeguimiento.es_ofertada == True)
            )
            stmt = (
                select(CaLicitacion)
                .options(
                    joinedload(CaLicitacion.seguimiento), 
                    joinedload(CaLicitacion.organismo).joinedload(CaOrganismo.sector)
                ) 
                .filter(
                    CaLicitacion.puntuacion_final >= umbral_minimo,
                    CaLicitacion.ca_id.notin_(subquery_seguimiento) 
                )
                .order_by(CaLicitacion.puntuacion_final.desc())
            )
            return session.scalars(stmt).all()

    def obtener_datos_tab3_seguimiento(self) -> List[CaLicitacion]:
        with self.session_factory() as session:
            stmt = select(CaLicitacion).options(joinedload(CaLicitacion.seguimiento), joinedload(CaLicitacion.organismo).joinedload(CaOrganismo.sector)).join(CaSeguimiento, CaLicitacion.ca_id == CaSeguimiento.ca_id).filter(CaSeguimiento.es_favorito == True).order_by(CaLicitacion.fecha_cierre.asc())
            return session.scalars(stmt).all()

    def obtener_datos_tab4_ofertadas(self) -> List[CaLicitacion]:
        with self.session_factory() as session:
            stmt = select(CaLicitacion).options(joinedload(CaLicitacion.seguimiento), joinedload(CaLicitacion.organismo).joinedload(CaOrganismo.sector)).join(CaSeguimiento, CaLicitacion.ca_id == CaSeguimiento.ca_id).filter(CaSeguimiento.es_ofertada == True).order_by(CaLicitacion.fecha_cierre.asc())
            return session.scalars(stmt).all()

    def _gestionar_seguimiento(self, ca_id: int, es_favorito: bool | None, es_ofertada: bool | None):
        with self.session_factory() as session:
            try:
                seguimiento = session.get(CaSeguimiento, ca_id)
                if seguimiento:
                    if es_favorito is not None: seguimiento.es_favorito = es_favorito
                    if es_ofertada is not None: 
                        seguimiento.es_ofertada = es_ofertada
                        if es_ofertada: seguimiento.es_favorito = True
                elif es_favorito or es_ofertada:
                    nuevo = CaSeguimiento(ca_id=ca_id, es_favorito=es_favorito or es_ofertada, es_ofertada=es_ofertada if es_ofertada is not None else False)
                    session.add(nuevo)
                session.commit()
            except Exception as e:
                logger.error(f"Error seguimiento {ca_id}: {e}")
                session.rollback()

    def gestionar_favorito(self, ca_id: int, es_favorito: bool):
        self._gestionar_seguimiento(ca_id, es_favorito=es_favorito, es_ofertada=None)

    def gestionar_ofertada(self, ca_id: int, es_ofertada: bool):
        self._gestionar_seguimiento(ca_id, es_favorito=None, es_ofertada=es_ofertada)

    def actualizar_nota_seguimiento(self, ca_id: int, nueva_nota: str):
        with self.session_factory() as session:
            try:
                seguimiento = session.get(CaSeguimiento, ca_id)
                if seguimiento:
                    seguimiento.notas = nueva_nota
                else:
                    nuevo = CaSeguimiento(ca_id=ca_id, es_favorito=False, es_ofertada=False, notas=nueva_nota)
                    session.add(nuevo)
                session.commit()
            except Exception as e:
                logger.error(f"Error nota {ca_id}: {e}")
                session.rollback()

    def eliminar_ca_definitivamente(self, ca_id: int):
        with self.session_factory() as session:
            try:
                licitacion = session.get(CaLicitacion, ca_id)
                if licitacion:
                    session.delete(licitacion)
                    session.commit()
            except Exception as e:
                logger.error(f"Error en eliminación definitiva de CA {ca_id}: {e}")
                session.rollback()

    def ocultar_licitacion(self, ca_id: int):
        return self.eliminar_ca_definitivamente(ca_id)

    def get_all_keywords(self) -> List[CaKeyword]:
        with self.session_factory() as session:
            return session.scalars(select(CaKeyword).order_by(CaKeyword.keyword)).all()

    def add_keyword(self, keyword: str, tipo: str, puntos: int) -> CaKeyword:
        with self.session_factory() as session:
            nuevo = CaKeyword(keyword=keyword.lower().strip(), tipo=tipo, puntos=puntos)
            session.add(nuevo)
            session.commit()
            session.refresh(nuevo)
            return nuevo

    def delete_keyword(self, keyword_id: int):
        with self.session_factory() as session:
            session.query(CaKeyword).filter_by(keyword_id=keyword_id).delete()
            session.commit()

    def get_all_organismo_reglas(self) -> List[CaOrganismoRegla]:
        with self.session_factory() as session:
            return session.scalars(select(CaOrganismoRegla).options(joinedload(CaOrganismoRegla.organismo))).all()

    def set_organismo_regla(self, organismo_id: int, tipo_str: str, puntos: Optional[int] = None) -> CaOrganismoRegla:
        with self.session_factory() as session:
            stmt = select(CaOrganismoRegla).where(CaOrganismoRegla.organismo_id == organismo_id)
            regla = session.scalars(stmt).first()
            if regla:
                regla.tipo = tipo_str
                regla.puntos = puntos
            else:
                regla = CaOrganismoRegla(organismo_id=organismo_id, tipo=tipo_str, puntos=puntos)
                session.add(regla)
            session.commit()
            session.refresh(regla)
            return regla

    def delete_organismo_regla(self, organismo_id: int):
        with self.session_factory() as session:
            stmt = select(CaOrganismoRegla).where(CaOrganismoRegla.organismo_id == organismo_id)
            regla = session.scalars(stmt).first()
            if regla:
                session.delete(regla)
                session.commit()

    def get_all_organisms(self) -> List[CaOrganismo]:
        with self.session_factory() as session:
            return session.scalars(select(CaOrganismo).order_by(CaOrganismo.nombre)).all()