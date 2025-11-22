# -*- coding: utf-8 -*-
import sys
import os
from pathlib import Path

# Configuración del Path para PyInstaller
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
    ROOT_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    ROOT_DIR = Path(__file__).resolve().parent

if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtGui import QPixmap, QFont

from src.utils.logger import configurar_logger
from config.config import DATABASE_URL

from alembic.config import Config
from alembic.command import upgrade

logger = configurar_logger("run_app")

def run_migrations():
    logger.info("Verificando estado de la base de datos...")
    try:
        if getattr(sys, 'frozen', False):
            alembic_cfg_path = ROOT_DIR / "alembic.ini"
            script_location = ROOT_DIR / "alembic"
        else:
            alembic_cfg_path = ROOT_DIR / "alembic.ini"
            script_location = ROOT_DIR / "alembic"

        if not alembic_cfg_path.exists():
            logger.error(f"No se encontró alembic.ini en: {alembic_cfg_path}")
            return

        alembic_cfg = Config(str(alembic_cfg_path))
        alembic_cfg.set_main_option("script_location", str(script_location))
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)

        upgrade(alembic_cfg, "head")
        logger.info("BD actualizada correctamente.")

    except Exception as e:
        logger.critical(f"Error al ejecutar migraciones: {e}", exc_info=True)

def main():
    # Crear la app primero para poder mostrar Splash
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    app.setQuitOnLastWindowClosed(False)

    # Splash Screen Simple (Solo texto si no hay imagen)
    splash = QSplashScreen()
    splash.showMessage("Iniciando Monitor CA...\nVerificando Base de Datos...", Qt.AlignBottom | Qt.AlignCenter, Qt.black)
    splash.show()
    
    # Procesar eventos para que se pinte el splash antes de bloquear con migraciones
    QCoreApplication.processEvents()

    # 1. Ejecutar Migraciones
    run_migrations()
    
    splash.showMessage("Cargando Interfaz...", Qt.AlignBottom | Qt.AlignCenter, Qt.black)
    QCoreApplication.processEvents()

    # 2. Iniciar GUI
    try:
        from src.gui.gui_main import MainWindow
        window = MainWindow()
        window.show()
        splash.finish(window)
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"Error fatal no manejado en la GUI: {e}", exc_info=True)
        print(f"Error Fatal: {e}")

if __name__ == "__main__":
    main()