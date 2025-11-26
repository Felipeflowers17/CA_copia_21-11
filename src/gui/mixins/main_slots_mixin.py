# -*- coding: utf-8 -*-
"""
Mixin para los Slots (acciones) de los botones principales.
"""

# --- CORRECCIÓN: Se eliminó 'Quser' que causaba el error ---
from PySide6.QtWidgets import QMessageBox, QSystemTrayIcon, QDialog
from PySide6.QtCore import Slot, Qt
import datetime 

from src.gui.gui_scraping_dialog import ScrapingDialog
from src.gui.gui_settings_dialog import GuiSettingsDialog
from src.gui.gui_export_dialog import GuiExportDialog 
from src.utils.logger import configurar_logger

logger = configurar_logger(__name__)


class MainSlotsMixin:
    """
    Este Mixin maneja las acciones disparadas por los
    botones principales de la barra de herramientas.
    """
    @Slot(object)
    def on_table_double_clicked(self, index):
        """
        Se dispara al hacer doble clic en cualquier tabla.
        Busca el ID oculto de forma robusta y abre el Drawer.
        """
        if not index.isValid():
            return
            
        proxy_model = index.model()

        if index.column() == 7: # Columna de Notas
            nota_texto = index.data(Qt.UserRole)
            if nota_texto and str(nota_texto).strip():
                QMessageBox.information(self, "Nota Personal", str(nota_texto))
            return # Detenemos aquí para no abrir el drawer

        row = index.row()
        ca_id = None

        # --- BÚSQUEDA ROBUSTA DEL ID ---
        # A veces el ID está en la Columna 0 (Score) o Columna 1 (Nombre)
        # Y puede estar en el UserRole (32) o UserRole+1 (33)
        
        columnas_a_revisar = [0, 1] 
        roles_a_revisar = [Qt.UserRole, Qt.UserRole + 1]

        for col in columnas_a_revisar:
            idx = proxy_model.index(row, col)
            for role in roles_a_revisar:
                data = proxy_model.data(idx, role)
                
                # Caso 1: El dato es directamente el ID (int)
                if isinstance(data, int) and data > 0:
                    ca_id = data
                    break
                
                # Caso 2: El dato es un diccionario completo (común en algunos diseños)
                if isinstance(data, dict) and 'ca_id' in data:
                    ca_id = data['ca_id']
                    break
            if ca_id: break

        if not ca_id:
            # Intento de último recurso: Buscar en columnas ocultas (ej. col 2)
            idx_oculto = proxy_model.index(row, 2)
            val = proxy_model.data(idx_oculto, Qt.UserRole)
            if isinstance(val, int): ca_id = val

        if not ca_id:
             logger.warning(f"ERROR: No se encontró CA_ID en la fila {row}. Revisa table_manager_mixin.py")
             return

        logger.info(f"Abriendo detalle para CA ID: {ca_id}")
        
        # Ejecutar consulta en hilo secundario
        self.start_task(
            task=self.db_service.get_licitacion_by_id,
            on_result=self.on_detail_data_loaded,
            on_error=self.on_task_error,
            task_args=(ca_id,)
        )

    def on_detail_data_loaded(self, licitacion_obj):
        """Callback cuando la BD devuelve el objeto completo."""
        if licitacion_obj and hasattr(self, 'detail_drawer'):
            self.detail_drawer.set_data(licitacion_obj)
            self.detail_drawer.open_drawer()
        else:
            logger.error("No se pudo cargar el detalle de la licitación.")

    def _show_task_completion_notification(self, title: str, message: str, is_auto: bool = False, is_error: bool = False):
        if self.tray_icon:
            icon = QSystemTrayIcon.MessageIcon.Warning if is_error else QSystemTrayIcon.MessageIcon.Information
            self.tray_icon.showMessage(title, message, icon, 4000)
        if not is_auto:
            if not is_error:
                QMessageBox.information(self, title, message)
    
    @Slot()
    def on_scraping_completed(self):
        self.set_ui_busy(False)
        if self.last_error:
            logger.warning("Proceso de Scraping finalizado con errores.")
            self._show_task_completion_notification( "Error de Scraping", f"La tarea falló: {self.last_error}", is_auto=False, is_error=True )
        else:
            msg = "La tarea de scraping ha finalizado exitosamente."
            self._show_task_completion_notification( "Proceso Completado", msg, is_auto=False, is_error=False )
        self.on_load_data_thread()

    @Slot()
    def on_export_report_completed(self): 
        self.set_ui_busy(False)
        if self.last_error:
            logger.error(f"La exportación falló: {self.last_error}")
            self._show_task_completion_notification( "Error de Exportación", f"La exportación falló: {self.last_error}", is_auto=False, is_error=True )
        elif self.last_export_path:
            logger.info("Exportación finalizada.")
            msg = f"Reporte guardado en:\n{self.last_export_path}"
            self._show_task_completion_notification( "Exportación Exitosa", msg, is_auto=False, is_error=False )

    @Slot()
    def on_recalculate_finished(self):
        self.set_ui_busy(False)
        if self.last_error:
            logger.warning(f"Proceso de Recálculo finalizado con errores: {self.last_error}")
            self._show_task_completion_notification( "Error de Recálculo", f"El recálculo falló: {self.last_error}", is_auto=False, is_error=True )
        else:
            msg = "Se han recalculado todos los puntajes exitosamente."
            self._show_task_completion_notification( "Recálculo Completado", msg, is_auto=False, is_error=False )
        self.on_load_data_thread()

    @Slot()
    def on_fase2_update_finished(self):
        self.set_ui_busy(False)
        is_auto = getattr(self, 'is_task_running_auto', False) 
        if self.last_error:
            logger.warning(f"Proceso de Actualización de Fichas finalizado con errores: {self.last_error}")
            self._show_task_completion_notification( "Error de Actualización", f"La actualización falló: {self.last_error}", is_auto=is_auto, is_error=True )
        else:
            msg = "Se han actualizado las fichas seleccionadas."
            self._show_task_completion_notification( "Actualización Completada", msg, is_auto=is_auto, is_error=False )
        self.on_load_data_thread()
        
    @Slot()
    def on_auto_task_finished(self):
        self.set_ui_busy(False)
        if self.last_error:
            logger.warning(f"PILOTO AUTOMÁTICO: Tarea finalizada con errores: {self.last_error}")
            self._show_task_completion_notification( "Error de Piloto Automático", f"La tarea automática falló: {self.last_error}", is_auto=True, is_error=True )
        else:
            logger.info("PILOTO AUTOMÁTICO: Tarea finalizada exitosamente.")
        self.on_load_data_thread()

    @Slot()
    def on_health_check_finished(self):
        self.set_ui_busy(False)
        if self.last_error:
            logger.warning(f"Chequeo de salud finalizado con errores: {self.last_error}")
            msg = ( "Falló el chequeo de salud.\n\n" f"Error: {self.last_error}\n\n" "Es posible que el sitio de Mercado Público haya cambiado, " "que no haya CAs hoy, o que no haya conexión a internet." )
            self._show_task_completion_notification("Chequeo Fallido", str(self.last_error), is_auto=False, is_error=True)
            QMessageBox.critical(self, "Chequeo Fallido", msg)
        elif self.last_health_check_ok:
            logger.info("Chequeo de salud finalizado con ÉXITO.")
            msg = ( "¡Chequeo de salud completado!\n\n" "La conexión a Mercado Público y el formato de datos " "(Fase 1 y Fase 2) parecen estar correctos." )
            self._show_task_completion_notification("Chequeo Exitoso", "Conexión y formato de datos OK.", is_auto=False, is_error=False)
            QMessageBox.information(self, "Chequeo Exitoso", msg)
        else:
            logger.error("Chequeo de salud finalizó en un estado desconocido (sin error, pero sin éxito).")
            
    @Slot()
    def on_open_scraping_dialog(self):
        if self.is_task_running:
            return
        dialog = ScrapingDialog(self)
        dialog.start_scraping.connect(self.on_start_full_scraping)
        dialog.exec()

    @Slot(dict)
    def on_start_full_scraping(self, config: dict):
        logger.info(f"Recibida configuración de scraping: {config}")
        task_to_run = None
        if config["mode"] == "to_db":
            task_to_run = self.etl_service.run_etl_live_to_db
        elif config["mode"] == "to_json":
            task_to_run = self.etl_service.run_etl_live_to_db 
            
        if task_to_run is None:
            return
        
        self.start_task(
            task=task_to_run,
            on_result=lambda: logger.info("Proceso ETL completo OK"),
            on_error=self.on_task_error,
            on_finished=self.on_scraping_completed,
            on_progress=self.on_progress_update,
            on_progress_percent=self.on_progress_percent_update,
            task_kwargs={"config": config}, 
        )

    @Slot()
    def on_open_export_pestañas_dialog(self):
        if self.is_task_running:
            return
        try:
            current_tab_index = self.tabs.currentIndex()
            current_tab_name = self.tabs.tabText(current_tab_index)
        except Exception:
            current_tab_name = "Actual"

        dialog = GuiExportDialog(current_tab_name, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            options = dialog.get_options()
            self.on_run_export_report_task(options)

    @Slot(dict)
    def on_run_export_report_task(self, options: dict):
        if self.is_task_running:
            return
        logger.info(f"Solicitud de exportar reporte de pestañas (con hilos) y opciones: {options}")
        self.last_export_path = None
        
        self.start_task(
            task=self.excel_service.generar_reporte_pestañas,
            on_result=lambda path: setattr(self, 'last_export_path', path),
            on_error=self.on_task_error,
            on_finished=self.on_export_report_completed, 
            task_args=(options,),
        )

    @Slot()
    def on_export_full_db_thread(self):
        if self.is_task_running:
            return
        confirm = QMessageBox.question(
            self, "Confirmar Exportación Completa",
            "Esto exportará TODAS las tablas de la base de datos a Excel.\n\n¿Desea continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.No:
            return
            
        logger.info("Solicitud de exportar BD completa (con hilos)...")
        self.last_export_path = None
        
        self.start_task(
            task=self.excel_service.generar_reporte_bd_completa,
            on_result=lambda path: setattr(self, 'last_export_path', path),
            on_error=self.on_task_error,
            on_finished=self.on_export_report_completed, 
        )

    @Slot()
    def on_open_settings_dialog(self):
        if self.is_task_running:
            return
        logger.debug("Abriendo diálogo de configuración...")
        dialog = GuiSettingsDialog(self.db_service, self.settings_manager, self)
        dialog.settings_changed.connect(self.on_settings_changed)
        dialog.exec()

    @Slot()
    def on_settings_changed(self):
        logger.info("Configuración actualizada por el usuario.")
        try:
            self.score_engine.recargar_reglas()
            logger.info("Reglas de ScoreEngine recargadas.")
            QMessageBox.information(
                self, "Configuración Actualizada",
                "La configuración se ha guardado. Recuerda recalcular puntajes si cambiaste reglas."
            )
        except Exception as e:
            logger.error(f"Error al aplicar nueva configuración: {e}")
            QMessageBox.critical(self, "Error", f"No se pudieron aplicar los cambios:\n{e}")

    @Slot()
    def on_run_recalculate_thread(self):
        if self.is_task_running:
            return
        confirm = QMessageBox.question( self, "Confirmar Recálculo", "Esto recalculará los puntajes de Fase 1...", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No, )
        if confirm == QMessageBox.StandardButton.No:
            return
        logger.info("Iniciando recálculo total de puntajes (con hilo)...")
        
        self.start_task(
            task=self.etl_service.run_recalculo_total_fase_1,
            on_result=lambda: logger.info("Recálculo completado OK"),
            on_error=self.on_task_error,
            on_finished=self.on_recalculate_finished,
            on_progress=self.on_progress_update,
            on_progress_percent=self.on_progress_percent_update,
        )

    @Slot()
    def on_run_fase2_update_thread(self, skip_confirm=False):
        if self.is_task_running:
            return
        if not skip_confirm:
            confirm = QMessageBox.question( self, "Confirmar Actualización", "Esto buscará en la web las fichas...", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No, )
            if confirm == QMessageBox.StandardButton.No:
                return
        logger.info("Iniciando actualización de Fichas Fase 2 (con hilo)...")
        
        self.start_task(
            task=self.etl_service.run_fase2_update,
            on_result=lambda: logger.info("Actualización de Fichas completada OK"),
            on_error=self.on_task_error,
            on_finished=self.on_fase2_update_finished,
            on_progress=self.on_progress_update,
            on_progress_percent=self.on_progress_percent_update,
        )
    
    @Slot()
    def on_start_full_scraping_auto(self):
        logger.info("PILOTO AUTOMÁTICO: Disparado Timer (Fase 1)")
        if self.is_task_running:
            logger.warning("PILOTO AUTOMÁTICO (Fase 1): Omitido. Otra tarea ya está en ejecución.")
            return
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        config = { "mode": "to_db", "date_from": yesterday, "date_to": today, "max_paginas": 100 }
        logger.info("PILOTO AUTOMÁTICO (Fase 1): Iniciando tarea...")
        
        self.start_task(
            task=self.etl_service.run_etl_live_to_db,
            on_result=lambda: logger.info("PILOTO AUTOMÁTICO (Fase 1): Proceso ETL completo OK"),
            on_error=self.on_task_error,
            on_finished=self.on_auto_task_finished, 
            on_progress=self.on_progress_update,
            on_progress_percent=self.on_progress_percent_update,
            task_kwargs={"config": config}, 
        )

    @Slot()
    def on_run_fase2_update_thread_auto(self):
        logger.info("PILOTO AUTOMÁTICO: (Fase 2)")
        if self.is_task_running:
            logger.warning("PILOTO AUTOMÁTICO (Fase 2): Omitido. Otra tarea ya está en ejecución.")
            return
        logger.info("PILOTO AUTOMÁTICO (Fase 2): Iniciando tarea...")
        
        self.start_task(
            task=self.etl_service.run_fase2_update,
            on_result=lambda: logger.info("PILOTO AUTOMÁTICO (Fase 2): Actualización de Fichas OK"),
            on_error=self.on_task_error,
            on_finished=self.on_auto_task_finished,
            on_progress=self.on_progress_update,
            on_progress_percent=self.on_progress_percent_update,
        )
        
    @Slot()
    def on_run_health_check_thread(self):
        if self.is_task_running:
            QMessageBox.warning(self, "Tarea en Curso", "Ya hay otra tarea ejecutándose.")
            return
        logger.info("Iniciando chequeo de salud (con hilo)...")
        self.last_health_check_ok = False 
        
        self.start_task(
            task=self.etl_service.run_health_check,
            on_result=lambda result: setattr(self, 'last_health_check_ok', result),
            on_error=self.on_task_error,
            on_finished=self.on_health_check_finished,
            on_progress=self.on_progress_update,
            on_progress_percent=self.on_progress_percent_update,
        )