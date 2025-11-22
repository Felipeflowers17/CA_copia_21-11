# -*- coding: utf-8 -*-
"""
Configuración General de la Aplicación.
Actualizado: Timeouts consistentes y seguridad de API Key.
"""

import os
import sys  
from dotenv import load_dotenv
from pathlib import Path

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

env_path = BASE_DIR / ".env"
load_dotenv(env_path, encoding="cp1252")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Valor por defecto o error explicativo
    raise ValueError(f"DATABASE_URL no está definida. Se buscó en: {env_path}")

# Umbrales
UMBRAL_FASE_1 = 5
UMBRAL_FINAL_RELEVANTE = 9

# Configuración de Scraping
URL_BASE_WEB = "https://buscador.mercadopublico.cl"
URL_BASE_API = "https://api.buscador.mercadopublico.cl"

# --- AJUSTES DE RENDIMIENTO ---
# Se han sincronizado los valores con la documentación
TIMEOUT_REQUESTS = 90      # Segundos antes de cancelar una petición
DELAY_ENTRE_PAGINAS = 3    # Segundos de espera entre páginas de listado
MAX_RETRIES = 3            # Número de intentos si falla una ficha
DELAY_RETRY = 5            # Segundos de espera antes de reintentar
# ------------------------------

MODO_HEADLESS = os.getenv('HEADLESS', 'True').lower() == 'true'

# Intenta leer la Key del sistema, si no, usa la por defecto (pero se recomienda .env)
_API_KEY = os.getenv('MERCADOPUBLICO_API_KEY', 'e93089e4-437c-4723-b343-4fa20045e3bc')

HEADERS_API = {
    'X-Api-Key': _API_KEY
}

# Constantes de Puntaje (por defecto 0, se cargan de BD)
PUNTOS_ORGANISMO = 0
PUNTOS_SEGUNDO_LLAMADO = 0
PUNTOS_KEYWORD_TITULO = 0
PUNTOS_ALERTA_URGENCIA = 0
PUNTOS_KEYWORD_PRODUCTO = 0