# -*- coding: utf-8 -*-
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
    # Fallback para desarrollo local si no hay .env, 
    # pero idealmente debería lanzar error o avisar en GUI
    print(f"ADVERTENCIA: DATABASE_URL no encontrada en {env_path}")

UMBRAL_FASE_1 = 5
UMBRAL_FINAL_RELEVANTE = 9

URL_BASE_WEB = "https://buscador.mercadopublico.cl"
URL_BASE_API = "https://api.buscador.mercadopublico.cl"

# Timeouts y Reintentos
TIMEOUT_REQUESTS = 30      
DELAY_ENTRE_PAGINAS = 1    
MAX_RETRIES = 3            
DELAY_RETRY = 5            

MODO_HEADLESS = os.getenv('HEADLESS', 'False').lower() == 'false'

# Seguridad: No hardcodear keys reales en código fuente.
# Se debe proveer por variable de entorno.
_API_KEY = os.getenv('MERCADOPUBLICO_API_KEY', '')

HEADERS_API = {
    'X-Api-Key': _API_KEY
}

PUNTOS_ORGANISMO = 0
PUNTOS_SEGUNDO_LLAMADO = 0
PUNTOS_KEYWORD_TITULO = 0
PUNTOS_ALERTA_URGENCIA = 0
PUNTOS_KEYWORD_PRODUCTO = 0