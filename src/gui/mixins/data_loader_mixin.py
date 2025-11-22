# -*- coding: utf-8 -*-
from PySide6.QtCore import Slot
from src.utils.logger import configurar_logger

logger = configurar_logger(__name__)

class DataLoaderMixin:
    """
    Maneja la carga secuencial de las pestañas para no congelar la UI.
    """

    @Slot()
    def on_load_data_thread(self):
        self.on_load_tab1_candidatas()

    def on_load_tab1_candidatas(self):
        # Leer umbral dinámico desde configuración (Default: 5)
        try:
            self.settings_manager.load_settings()
            umbral = int(self.settings_manager.get_setting("umbral_puntaje_minimo") or 5)
        except:
            umbral = 5
        
        def task():
            return self.db_service.obtener_datos_tab1_candidatas(umbral_minimo=umbral)
        
        self.start_task(
            task=task,
            on_result=self.poblar_tab_unificada,
            on_error=self.on_task_error
        )

    def poblar_tab_unificada(self, data):
        logger.info(f"DATA LOADER: Cargando {len(data)} licitaciones en Candidatas.")
        self.poblar_tabla(self.model_tab1, data)
        self.on_load_tab3_seguimiento()

    def on_load_tab3_seguimiento(self):
        self.start_task(task=self.db_service.obtener_datos_tab3_seguimiento, on_result=self.poblar_tab_seguimiento, on_error=self.on_task_error)

    def poblar_tab_seguimiento(self, data):
        self.poblar_tabla(self.model_tab3, data)
        self.on_load_tab4_ofertadas()

    def on_load_tab4_ofertadas(self):
        self.start_task(task=self.db_service.obtener_datos_tab4_ofertadas, on_result=self.poblar_tab_ofertadas, on_error=self.on_task_error)

    def poblar_tab_ofertadas(self, data):
        self.poblar_tabla(self.model_tab4, data)
        
    @Slot()
    def on_auto_task_finished(self):
        logger.info("Tarea automática finalizada. Recargando datos...")
        self.on_load_data_thread()