# -*- coding: utf-8 -*-
"""
Constructor de URLs (URL Builder).
Actualizado: Elimina 'region=all' de la API listado para evitar conflictos con filtros de fecha.
"""
from typing import Dict, Optional
from config.config import URL_BASE_WEB, URL_BASE_API 

def construir_url_listado(numero_pagina: int = 1, filtros: Optional[Dict] = None):
    """Construye la URL WEB (para navegar). Aquí SI se usa region=all."""
    parametros = {
        'status': 2,
        'order_by': 'recent',
        'page_number': numero_pagina
    }
    if filtros: parametros.update(filtros)
    if 'region' not in parametros: parametros['region'] = 'all'
    string_parametros = '&'.join([f"{k}={v}" for k, v in parametros.items()])
    return f"{URL_BASE_WEB}/compra-agil?{string_parametros}"

def construir_url_api_listado(numero_pagina: int = 1, filtros: Optional[Dict] = None):
    """
    Construye la URL API DIRECTA.
    CORRECCIÓN: No forzar 'region=all' ya que rompe el filtro de fechas.
    """
    parametros = {
        'status': 2,
        'order_by': 'recent',
        'page_number': numero_pagina
    }
    if filtros: parametros.update(filtros)
    
    # NOTA: Se eliminó la inyección forzada de 'region=all'
    # La API real no la usa cuando se piden fechas.
    
    string_parametros = '&'.join([f"{k}={v}" for k, v in parametros.items()])
    return f"{URL_BASE_API}/compra-agil?{string_parametros}"

def construir_url_ficha(codigo_compra: str):
    return f"{URL_BASE_WEB}/ficha?code={codigo_compra}"

def construir_url_api_ficha(codigo_compra: str):
    return f"{URL_BASE_API}/compra-agil?action=ficha&code={codigo_compra}"