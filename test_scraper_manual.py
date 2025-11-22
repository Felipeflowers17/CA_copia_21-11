# -*- coding: utf-8 -*-
"""
Script de prueba independiente para validar el Scraper (Fase 1 y Fase 2).
Ejecutar con: poetry run python test_scraper_manual.py
"""

import sys
import datetime
from pathlib import Path

# Aseguramos que el sistema encuentre los módulos del proyecto
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from src.scraper.scraper_service import ScraperService
from src.utils.logger import configurar_logger
from config.config import HEADERS_API, MODO_HEADLESS

# Configurar logger para ver output en consola
logger = configurar_logger("TEST_SCRAPER")

def callback_dummy(mensaje):
    """Función simple para imprimir el progreso en consola."""
    print(f"[PROGRESO] {mensaje}")

def run_test():
    print("="*60)
    print(" INICIANDO TEST DE SCRAPING (Modo Híbrido)")
    print("="*60)
    
    # Validar que el API Key esté configurado
    api_key = HEADERS_API.get('X-Api-Key')
    if not api_key:
        print("⚠️ ERROR: X-Api-Key no está definido en config.py")
        return
    print(f"✓ API Key detectado: {api_key[:20]}...")
    print("✓ Estrategia: requests (Fase 1) + Playwright (Fase 2 si necesario)")

    scraper = ScraperService()

    # --- TEST FASE 1: Listado con requests ---
    print("\n--- 1. Probando FASE 1 (Listado con requests) ---")
    
    # Configurar fechas: Últimos 2 días
    hoy = datetime.date.today()
    hace_dos_dias = hoy - datetime.timedelta(days=2)
    
    filtros = {
        'date_from': hace_dos_dias.strftime('%Y-%m-%d'),
        'date_to': hoy.strftime('%Y-%m-%d')
    }
    
    print(f"Buscando licitaciones entre {filtros['date_from']} y {filtros['date_to']}...")
    print("Max páginas: 1 (Para prueba rápida)")

    try:
        # Ejecutamos scraper limitando a 1 página
        resultados_fase1 = scraper.run_scraper_listado(
            progress_callback=callback_dummy,
            filtros=filtros,
            max_paginas=1
        )
        
        if resultados_fase1:
            print(f"✅ ÉXITO FASE 1: Se encontraron {len(resultados_fase1)} licitaciones.")
            primer_resultado = resultados_fase1[0]
            codigo_prueba = primer_resultado.get('codigo')
            print(f"Ejemplo capturado: {codigo_prueba} - {primer_resultado.get('nombre')[:50]}...")
        else:
            print("⚠️ ADVERTENCIA: Fase 1 terminó sin errores pero no trajo datos.")
            print("   Esto puede ser normal si no hay CAs publicadas en esas fechas.")
            print("   Intenta ampliar el rango de fechas o verifica el sitio web.")
            return

    except Exception as e:
        print(f"❌ ERROR FATAL EN FASE 1: {e}")
        import traceback
        traceback.print_exc()
        return

    # --- TEST FASE 2: Ficha Detalle (con requests, no necesita navegador) ---
    print("\n--- 2. Probando FASE 2 (Detalle con requests) ---")
    print(f"Usaremos el código capturado: {codigo_prueba}")

    try:
        # FASE 2 ahora también usa requests por defecto
        print("Obteniendo ficha con requests...")
        detalle = scraper._fetch_api_con_requests(
            f"https://api.buscador.mercadopublico.cl/compra-agil?action=ficha&code={codigo_prueba}"
        )
        
        if detalle and detalle.get('success') == 'OK' and 'payload' in detalle:
            payload = detalle['payload']
            print("✅ ÉXITO FASE 2: Datos de ficha obtenidos con requests.")
            print("Datos extraídos:")
            desc = payload.get('descripcion', '')
            if desc:
                print(f" - Descripción: {desc[:100]}...")
            else:
                print(" - Descripción: (vacía)")
            print(f" - Productos: {len(payload.get('productos_solicitados', []))} items encontrados.")
            print(f" - Estado: {payload.get('estado')}")
            print(f" - Estado Convocatoria: {payload.get('estado_convocatoria')}")
        else:
            print("❌ ERROR EN FASE 2: No se pudo obtener el detalle.")

    except Exception as e:
        print(f"❌ ERROR FATAL EN FASE 2: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)
    print(" FIN DEL TEST")
    print("="*60)

if __name__ == "__main__":
    run_test()