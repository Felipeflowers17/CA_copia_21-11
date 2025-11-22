# -*- coding: utf-8 -*-
import time
import random
from playwright.sync_api import sync_playwright, Playwright, Page, Response
from typing import Optional, Dict, Callable, List

from src.utils.logger import configurar_logger
from . import api_handler
from .url_builder import (
    construir_url_listado,
    construir_url_api_ficha,
    construir_url_api_listado
)
from config.config import (
    MODO_HEADLESS, MAX_RETRIES, DELAY_RETRY, HEADERS_API
)

logger = configurar_logger('scraper_service')

class ScraperService:
    def __init__(self):
        logger.info("ScraperService inicializado.")
        self.headers_sesion = {} 

    def _obtener_credenciales(self, p: Playwright, progress_callback: Callable[[str], None]):
        logger.info("Iniciando navegador con camuflaje manual...")
        progress_callback("Abriendo Chrome (Modo Stealth Manual)...")
        
        args = [
            "--disable-blink-features=AutomationControlled", 
            "--start-maximized", 
            "--no-sandbox",
            "--disable-infobars"
        ]

        try:
            browser = p.chromium.launch(channel="chrome", headless=False, args=args)
        except:
            logger.warning("Chrome no encontrado, usando Chromium base.")
            browser = p.chromium.launch(headless=False, args=args)
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        page = context.new_page()
        headers_capturados = {}

        def interceptar_request(request):
            if "api.buscador" in request.url:
                headers = request.headers
                if "authorization" in headers:
                    headers_capturados['authorization'] = headers['authorization']
                if "x-api-key" in headers:
                    headers_capturados['x-api-key'] = headers['x-api-key']

        page.on("request", interceptar_request)

        try:
            logger.info("Navegando al sitio...")
            # Reducido timeout a 30s para no colgar la app
            page.goto("https://buscador.mercadopublico.cl/compra-agil", wait_until="commit", timeout=30000)
            
            time.sleep(5) 

            if "authorization" not in headers_capturados:
                try:
                    page.mouse.move(200, 200)
                    page.mouse.move(400, 400)
                    btn = page.get_by_role("button", name="Buscar")
                    if btn.is_visible():
                        btn.click()
                except: pass

            intentos = 0
            max_intentos = 15 # Reducido para mayor respuesta
            while "authorization" not in headers_capturados and intentos < max_intentos:
                time.sleep(1)
                intentos += 1
                progress_callback(f"Esperando token... {intentos}/{max_intentos}")

            if "authorization" not in headers_capturados:
                logger.warning("Recargando página para segundo intento...")
                try:
                    page.reload(wait_until="domcontentloaded", timeout=30000)
                except: pass
                time.sleep(5)

            if "authorization" not in headers_capturados:
                raise Exception("No se pudieron capturar las credenciales (Token Bearer) tras múltiples intentos.")

            logger.info("¡Credenciales capturadas exitosamente!")

            self.headers_sesion = {
                'authorization': headers_capturados['authorization'],
                'x-api-key': headers_capturados.get('x-api-key', 'e93089e4-437c-4723-b343-4fa20045e3bc'),
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'accept': 'application/json, text/plain, */*',
                'referer': 'https://buscador.mercadopublico.cl/'
            }
            
            return None 

        except Exception as e:
            logger.error(f"Error obteniendo credenciales: {e}")
            raise e
        finally:
            # Asegurar cierre del navegador
            try:
                browser.close()
            except: pass

    def run_scraper_listado(self, progress_callback: Callable[[str], None], filtros: Optional[Dict] = None, max_paginas: Optional[int] = None) -> List[Dict]:
        logger.info(f"INICIANDO FASE 1. Filtros: {filtros}")
        todas_las_compras = []

        with sync_playwright() as p:
            try:
                self._obtener_credenciales(p, progress_callback)
            except Exception as e:
                logger.error(f"Fallo crítico obteniendo token: {e}")
                # Si falla el token, no podemos seguir
                raise e
            
            # Fase de extracción con requests
            # Lanzamos un browser headless ligero solo para tener contexto si fuera necesario, 
            # aunque aquí usaremos principalmente requests con los headers capturados.
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(extra_http_headers=self.headers_sesion)
            api_request = context.request 

            try:
                current_page = 1
                total_paginas = 1
                
                # Límite de seguridad por si la API reporta páginas infinitas
                LIMIT_SAFETY_PAGES = 500 

                while True:
                    if max_paginas and max_paginas > 0 and current_page > max_paginas:
                        break
                    if current_page > total_paginas and total_paginas > 0:
                        break
                    if current_page > LIMIT_SAFETY_PAGES:
                        logger.warning("Se alcanzó el límite de seguridad de páginas.")
                        break

                    progress_callback(f"Procesando página {current_page}...")
                    
                    url = construir_url_api_listado(current_page, filtros)
                    
                    datos = self._ejecutar_peticion_api(api_request, url)
                    
                    if not datos:
                        logger.error(f"Fallo en página {current_page}, deteniendo.")
                        break

                    meta = api_handler.extraer_metadata_paginacion(datos)
                    items = api_handler.extraer_resultados(datos)
                    
                    if current_page == 1:
                        total_paginas = meta.get('pageCount', 0)
                        logger.info(f"Total páginas encontradas: {total_paginas}")
                        
                        if total_paginas == 0:
                            logger.warning("La API retornó 0 páginas. Verificar filtros o token.")
                            break
                    
                    todas_las_compras.extend(items)
                    current_page += 1
                    
                    # Pequeña pausa para ser amables con el servidor
                    time.sleep(random.uniform(0.5, 1.0))

            except Exception as e:
                logger.critical(f"Error Fase 1: {e}")
                raise e
            finally:
                try:
                    browser.close()
                except: pass

        unicas = {c.get('codigo', c.get('id')): c for c in todas_las_compras if c.get('codigo', c.get('id'))}
        return list(unicas.values())

    def _fetch_api_con_requests(self, url: str) -> Optional[Dict]:
        import requests
        try:
            headers = self.headers_sesion if self.headers_sesion else HEADERS_API
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Error request directo: {e}")
            return None

    def scrape_ficha_detalle_api(self, page: Page, codigo_ca: str, progress_callback: Callable[[str], None]) -> Optional[Dict]:
        url_api = construir_url_api_ficha(codigo_ca)
        datos = self._fetch_api_con_requests(url_api)
        
        if datos and datos.get('success') == 'OK' and 'payload' in datos:
            payload = datos['payload']
            return {
                'descripcion': payload.get('descripcion'),
                'direccion_entrega': payload.get('direccion_entrega'),
                'fecha_cierre_p1': payload.get('fecha_cierre_primer_llamado'),
                'fecha_cierre_p2': payload.get('fecha_cierre_segundo_llamado'),
                'productos_solicitados': payload.get('productos_solicitados', []),
                'estado': payload.get('estado'),
                'cantidad_provedores_cotizando': payload.get('cantidad_provedores_cotizando'),
                'estado_convocatoria': payload.get('estado_convocatoria')
            }
        return None

    def _ejecutar_peticion_api(self, api_request, url):
        for intento in range(1, MAX_RETRIES + 1):
            try:
                response = api_request.get(url)
                if response.ok:
                    return response.json()
                elif response.status == 429:
                    # Rate Limit: Esperar más
                    time.sleep(DELAY_RETRY * 2)
                else:
                    logger.warning(f"API Status {response.status}: {url}")
            except Exception as e:
                logger.debug(f"Error intento {intento}: {e}")
            time.sleep(DELAY_RETRY)
        return None