# -*- coding: utf-8 -*-
"""
Motor de Puntuación (Score Engine).
Versión Blindada: Normalización agresiva y manejo seguro de listas vacías.
"""
import unicodedata
from typing import Dict, List, Set, Tuple
from src.utils.logger import configurar_logger
from src.db.db_models import CaKeyword
from config.config import PUNTOS_SEGUNDO_LLAMADO

logger = configurar_logger(__name__)

class ScoreEngine:
    def __init__(self, db_service):
        self.db_service = db_service
        self.keywords_cache: List[CaKeyword] = [] 
        self.reglas_prioritarias: Dict[int, int] = {}
        self.reglas_no_deseadas: Set[int] = set()
        self.organismo_name_to_id_map: Dict[str, int] = {}
        self.recargar_reglas()

    def recargar_reglas(self):
        """Carga todas las reglas desde la BD a memoria RAM."""
        logger.info("ScoreEngine: Recargando reglas y keywords...")
        try:
            self.keywords_cache = self.db_service.get_all_keywords()
        except Exception as e: 
            logger.error(f"Error cargando keywords: {e}")
            self.keywords_cache = []
        
        self.reglas_prioritarias = {}
        self.reglas_no_deseadas = set()
        try:
            reglas = self.db_service.get_all_organismo_reglas()
            for r in reglas:
                tipo_val = r.tipo.value if hasattr(r.tipo, 'value') else r.tipo
                
                if tipo_val == 'prioritario': 
                    self.reglas_prioritarias[r.organismo_id] = r.puntos
                elif tipo_val == 'no_deseado': 
                    self.reglas_no_deseadas.add(r.organismo_id)
        except Exception as e:
            logger.error(f"Error cargando reglas organismos: {e}")

        self.organismo_name_to_id_map = {}
        try:
            orgs = self.db_service.get_all_organisms()
            for o in orgs:
                if o.nombre: 
                    self.organismo_name_to_id_map[self._norm(o.nombre)] = o.organismo_id
        except: pass

    def _norm(self, txt): 
        """
        Normalización Agresiva:
        1. None -> ""
        2. Elimina tildes (á -> a).
        3. Todo a minúsculas.
        4. Elimina saltos de línea, tabulaciones y espacios dobles.
        """
        if not txt: return ""
        # Paso 1: Descomponer caracteres unicode (NFD) y eliminar marcas (Mn)
        s = ''.join(c for c in unicodedata.normalize('NFD', str(txt).lower()) if unicodedata.category(c) != 'Mn')
        # Paso 2: Reemplazar cualquier espacio en blanco (tabs, newlines) por espacio simple
        return " ".join(s.split())

    def calcular_puntuacion_fase_1(self, licitacion_raw: dict) -> Tuple[int, List[str]]:
        """Cálculo base: Organismo + Título + Estado"""
        org_norm = self._norm(licitacion_raw.get("organismo_comprador"))
        nom_norm = self._norm(licitacion_raw.get("nombre"))
        
        puntaje = 0
        detalle = []

        if not nom_norm: 
            return 0, ["Sin nombre"]

        # 1. Organismo
        org_id = self.organismo_name_to_id_map.get(org_norm)
        
        # Búsqueda flexible por si el nombre varía ligeramente
        if not org_id:
            for name_key, oid in self.organismo_name_to_id_map.items():
                if name_key == org_norm:
                    org_id = oid
                    break

        if org_id:
            if org_id in self.reglas_no_deseadas: 
                return -9999, ["Organismo No Deseado"]
            
            if org_id in self.reglas_prioritarias: 
                pts = self.reglas_prioritarias[org_id]
                puntaje += pts
                detalle.append(f"Org. Prioritario (+{pts})")

        # 2. Estado
        est_norm = self._norm(licitacion_raw.get("estado_ca_texto"))
        if "segundo llamado" in est_norm: 
            puntaje += PUNTOS_SEGUNDO_LLAMADO
            if PUNTOS_SEGUNDO_LLAMADO != 0:
                detalle.append(f"2° Llamado (+{PUNTOS_SEGUNDO_LLAMADO})")
        
        # 3. Keywords en NOMBRE
        for kw in self.keywords_cache:
            if kw.puntos_nombre == 0: continue
            
            kw_norm = self._norm(kw.keyword)
            if kw_norm in nom_norm:
                puntaje += kw.puntos_nombre
                signo = "+" if kw.puntos_nombre > 0 else ""
                detalle.append(f"KW Título: '{kw.keyword}' ({signo}{kw.puntos_nombre})")
                
        return max(0, puntaje), detalle

    def calcular_puntuacion_fase_2(self, datos_ficha: dict) -> Tuple[int, List[str]]:
        """Cálculo profundo: Descripción + Productos"""
        puntaje = 0
        detalle = []
        
        # Normalizar Descripción
        desc_norm = self._norm(datos_ficha.get("descripcion"))
        
        # Normalizar Productos (Corrección de Bug: Manejo de None)
        prods_raw = datos_ficha.get("productos_solicitados")
        if prods_raw is None: 
            prods_raw = [] # Asegurar que sea lista vacía y no None
            
        txt_prods = ""
        if isinstance(prods_raw, list):
            parts = []
            for p in prods_raw:
                # Extraer texto de cada producto con seguridad
                n = p.get("nombre") or ""
                d = p.get("descripcion") or ""
                parts.append(self._norm(f"{n} {d}"))
            txt_prods = " ".join(parts)

        for kw in self.keywords_cache:
            kw_norm = self._norm(kw.keyword)
            if not kw_norm: continue
            
            # Check Descripción
            if kw.puntos_descripcion != 0 and desc_norm:
                if kw_norm in desc_norm:
                    puntaje += kw.puntos_descripcion
                    signo = "+" if kw.puntos_descripcion > 0 else ""
                    detalle.append(f"KW Desc: '{kw.keyword}' ({signo}{kw.puntos_descripcion})")
            
            # Check Productos
            if kw.puntos_productos != 0 and txt_prods:
                if kw_norm in txt_prods:
                    puntaje += kw.puntos_productos
                    signo = "+" if kw.puntos_productos > 0 else ""
                    detalle.append(f"KW Prod: '{kw.keyword}' ({signo}{kw.puntos_productos})")
                
        return puntaje, detalle