#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kangaroo, una interfaz gráfica para facilitar
el análisis y descarga de datos de
certificados de bachillerato mexicanos
disponibles al público en general

Copyright (C) 2020
Jacob Sánchez Pérez
"""

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor,
# Boston, MA  02110-1301, USA.
# Also available at https://www.gnu.org/licenses/old-licenses/gpl-2.0.html

import os
import sys
import time
import json
import logging
import datetime
import concurrent.futures as futures
from main import CertificateParser
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *


class AboutWindow(QWidget):
    _window_title = "Acerca De Kangaroo"
    _about_icon = os.path.join("assets", "kangaroo.png")
    _app_name = "Kangaroo"
    _app_version = "Versión 0.1a"
    _app_desc = "Un asistente de descarga de certificados de bachillerato"
    _copyright = "Copyright (C) 2020"
    _copyright_holder = "Jacob Sánchez Pérez"

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        app_info = [self._app_name, self._app_version, self._app_desc,
                    self._copyright, self._copyright_holder]

        label_styles = [QFont('sans-serif', 12, QFont.Bold),
                        QFont('sans-serif', 10),
                        QFont('sans-serif', 10),
                        QFont('sans-serif', 8),
                        QFont('sans-serif', 8)]

        self.setWindowTitle(self._window_title)
        self.setWindowIcon(QIcon(self._about_icon))

        self.setFixedSize(320, 320)

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignHCenter)

        self.layout.addSpacing(12)
        self.addMainIcon()
        self.layout.addStretch()

        for i in range(0, len(app_info)):
            new_label = QLabel(app_info[i])
            new_label.setAlignment(Qt.AlignHCenter)
            new_label.setFont(label_styles[i])
            new_label.setWordWrap(True)
            new_label.setFixedWidth(280)

            self.layout.addWidget(new_label)

        self.layout.addSpacing(12)

    def addMainIcon(self):
        self.center_icon = QLabel(self)
        pixmap = QPixmap(self._about_icon)
        pixmap = pixmap.scaledToHeight(140)
        self.center_icon.setPixmap(pixmap)
        self.center_icon.setAlignment(Qt.AlignHCenter)
        self.layout.addWidget(self.center_icon)


class NewDownloadDialog(QDialog):
    _window_title = "Comenzar Nueva Descarga"
    _about_icon = os.path.join("assets", "kangaroo.png")
    _threaded_text = "Habilitar Multithreading"
    _filename = "certificate_data_{}.json"
    _start_text = "Iniciar"
    _cancel_text = "Cancelar"

    def __init__(self, batch_size):
        super().__init__(None, Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        self._batch_size = batch_size
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self._window_title)
        self.setWindowIcon(QIcon(self._about_icon))
        self.setFixedSize(420, 200)

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)

        self.layout.addSpacing(10)

        self.cert_spin = QSpinBox()
        self.cert_spin.setRange(1, 999)
        self.cert_spin.valueChanged.connect(self.updateRange)
        self.layout.addWidget(self.cert_spin)

        self.layout.addSpacing(20)

        self.range_label = QLabel('Selecciona el número de lote')
        self.layout.addWidget(self.range_label)

        self.filename_label = QLabel('...')
        self.layout.addWidget(self.filename_label)

        self.layout.addStretch()

        options_line = QFrame()
        options_line.setFrameShape(QFrame.HLine)
        self.layout.addWidget(options_line)

        self.thread_check = QCheckBox(self._threaded_text)
        self.thread_check.toggle()
        self.layout.addWidget(self.thread_check)

        button_layout = QHBoxLayout()
        start_button = QPushButton(self._start_text)
        start_button.clicked.connect(self.accept)
        cancel_button = QPushButton(self._cancel_text)
        cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(start_button)

        self.layout.addLayout(button_layout)

    def updateRange(self):
        current_value = self.cert_spin.value()

        r_end = current_value * self._batch_size - 1
        r_start = (current_value - 1) * self._batch_size

        range_text = f"Download certificates {r_start} - {r_end}"

        full_filename = self._filename.format(f"{current_value:03}")
        filename_text = f"Save as: {full_filename}"

        self.range_label.setText(range_text)
        self.filename_label.setText(filename_text)


class DownloadThread(QThread):
    storage_folder = "Certificates_GUI"
    _filename = "certificate_data_{}.json"

    _max_wks = 8

    download_change = pyqtSignal(int)
    download_update = pyqtSignal(int, int)

    def __init__(self, folder, filename, batch_size, file_no, threaded=True):
        super().__init__()
        self.cert_parser = CertificateParser()
        self.storage_folder = folder
        self._filename = filename

        self._batch_size = batch_size
        self.file_no = file_no
        self.threaded = threaded
        self._range_end = self.file_no * self._batch_size
        self._range_start = (self.file_no - 1) * self._batch_size

    def run(self):
        self.download_change.emit(0)

        cert_list = []
        cert_range = range(self._range_start, self._range_end)

        with futures.ThreadPoolExecutor(max_workers=self._max_wks) as executor:
            map_mode = map

            if self.threaded:
                map_mode = executor.map

            cert_list = map_mode(self.parseWrapper, cert_range)

        cert_list = list(cert_list)

        # Finalise operation
        self.download_change.emit(1)

        # self.state.setText(f"Completed batch number {self.file_no}")

        failed_certs = cert_list.count(False)

        if failed_certs >= 1:
            print(f"{failed_certs} certificados no pudieron ser descargados")
            failure_rate = (failed_certs / self._batch_size) * 100

            print(f"{failure_rate}% tasa de error")

        file_name = self._filename.format(f"{self.file_no:03}")
        file_path = os.path.join(self.storage_folder, file_name)

        with open(file_path, 'w') as outfile:
            json.dump(cert_list, outfile, indent=4, ensure_ascii=False)
            # self.state.setText(f"Saved batch number {self.file_no}")
            self.download_change.emit(2)

    def parseWrapper(self, cert_number):
        if (cert_number % 5 == 0) or not self.threaded:
            self.sendDownloadUpdate(cert_number)
        return self.cert_parser.parse(cert_number)

    def sendDownloadUpdate(self, cert_number):
        relative_no = cert_number - self._range_start
        self.download_update.emit(relative_no, self._batch_size)


class DownloadDetails(QWidget):
    _title_format = "Propiedades del lote {}"
    _window_icon = os.path.join("assets", "kangaroo.png")

    def __init__(self, d_item):
        super().__init__()

        self.d_item = d_item

        self._window_title = self._title_format.format(self.d_item.file_no)
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self._window_title)
        self.setWindowIcon(QIcon(self._window_icon))

        self.setFixedSize(420, 420)

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignCenter)
        self.createTable()

        self.layout.addWidget(self.tab_widget)

    def createTable(self):
        self.tab_widget = QTabWidget()
        self.tab_information = self.createInformation()

        # Add tabs
        self.tab_widget.addTab(self.tab_information, "Información")
        # self.tab_widget.addTab(self.tab_operations, "Operaciones")

    def createInformation(self):
        tab_information = QWidget()
        tab_information.layout = QVBoxLayout()
        tab_information.layout.setAlignment(Qt.AlignTop)
        tab_information.layout.addSpacing(6)

        op_title_label = QLabel("Descarga")
        op_title_label.setFont(QFont('sans-serif', 10, QFont.Bold))
        tab_information.layout.addWidget(op_title_label)
        tab_information.layout.addSpacing(6)

        operations_line = QFrame()
        operations_line.setFrameShape(QFrame.HLine)
        tab_information.layout.addWidget(operations_line)

        tab_information.layout.addSpacing(10)

        tab_information.layout.addLayout(self.getDownloadGrid())
        tab_information.setLayout(tab_information.layout)

        return tab_information

    def getDownloadGrid(self):
        local_start = time.localtime(self.d_item.start_time)
        start_time = time.strftime("%Y-%m-%d %H:%M:%S", local_start)

        finish_time = "N/A"
        elapsed_end = time.time()

        if self.d_item.finish_time is not None:
            local_finish = time.localtime(self.d_item.finish_time)
            finish_time = time.strftime("%Y-%m-%d %H:%M:%S", local_finish)
            elapsed_end = self.d_item.finish_time

        elapsed_s = round(elapsed_end - self.d_item.start_time)
        time_elapsed = str(datetime.timedelta(seconds=elapsed_s))

        operation_list = ["Comienzo:",
                          "Tiempo Transcurrido:",
                          "Tiempo Restante:",
                          "Completado:",
                          "Estado:"]

        state_list = ["Comenzando", "Trabajando",
                      "Pausado", "Guardando", "Guardado", "Cancelado"]

        value_list = [start_time,
                      time_elapsed,
                      self.d_item.eta,
                      finish_time,
                      state_list[self.d_item.status_code]]

        operation_grid = self.constructGrid(operation_list, value_list)

        return operation_grid

    def constructGrid(self, attr, values):
        new_grid = QGridLayout()
        new_grid.setContentsMargins(20, 0, 0, 0)
        new_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        new_grid.setVerticalSpacing(18)
        new_grid.setHorizontalSpacing(8)

        for i in range(len(attr)):
            attr_label = QLabel(attr[i])
            value_label = QLabel(values[i])

            new_grid.addWidget(attr_label, i + 1, 1)
            new_grid.addWidget(value_label, i + 1, 2)
        return new_grid

    def createOperations(self):
        tab_operations = QWidget()

        return tab_operations

    def closeEvent(self, event):
        self.d_item.details_open = False


class DownloadItem(QWidget):
    _speed_icon = os.path.join("assets", "flame.png")
    _title_format = "Datos de Certificado {}"
    _storage_folder = "Certificates_GUI"
    _filename_format = "certificate_data_{}.json"

    threaded = True
    name = ""

    has_errors = False
    errors = []
    time_history = []
    details_open = False
    status_code = 0
    selected = False
    disabled = False

    selected_item = pyqtSignal()

    def __init__(self, batch_size, file_no, threaded=True):
        super().__init__()

        self._batch_size = batch_size
        self.file_no = file_no

        self.threaded = threaded
        self.name = self._title_format.format(file_no)

        self.start_time = time.time()
        self.finish_time = None

        self.initUI()
        self.setObjectName("DownloadItem")
        self.thread_op = DownloadThread(self._storage_folder,
                                        self._filename_format,
                                        self._batch_size,
                                        self.file_no, self.threaded)
        self.thread_op.download_update.connect(self.updateProgress)
        self.thread_op.download_change.connect(self.downloadChange)

        self.started_last = time.time()

        file_name = self._filename_format.format(f"{self.file_no:03}")
        file_path = os.path.join(self._storage_folder, file_name)

        if os.path.exists(file_path):
            proceed = QMessageBox()
            proceed.setIcon(QMessageBox.Question)

            proceed.setText("¿Sobreescribir archivo existente homónimo?")

            proceed.setWindowTitle("Confirmar sobreescritura")
            proceed.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            proceed_result = proceed.exec()

            if proceed_result == 65536:
                self.cancelled()
                return

        # self.thread_op.start()

    def initUI(self):
        self.setFixedHeight(100)
        self.initInfoLayout()

        self.title = QLabel(self.name)
        self.title.setFont(QFont('sans-serif', 11, QFont.Bold))
        self.threading_icon = QLabel()

        self.state = QLabel("Comenzando descarga")
        self.eta = "?"
        self.eta_label = QLabel("ETA: ?")

        self.title_hbox.addWidget(self.title)

        if self.threaded:
            self.addMainIcon()

        self.info_vbox.addWidget(self.state)
        self.info_hbox.addWidget(self.eta_label)

        self.progress = QProgressBar()
        self.progress.setFixedHeight(16)
        self.progress.setStyleSheet("background-color: unset;")

        self.layout.addWidget(self.progress)
        self.layout.addSpacing(5)
        self.setAttribute(Qt.WA_StyledBackground, True)

    def initInfoLayout(self):
        self.layout = QVBoxLayout(self)
        self.info_hbox = QHBoxLayout()
        self.info_hbox.setAlignment(Qt.AlignTop)
        self.info_vbox = QVBoxLayout()
        self.title_hbox = QHBoxLayout()
        self.info_vbox.addLayout(self.title_hbox)

        self.layout.addLayout(self.info_hbox)
        self.info_hbox.addLayout(self.info_vbox)
        self.info_hbox.addStretch()

    def addMainIcon(self):
        pixmap = QPixmap(self._speed_icon)

        self.threading_icon.setPixmap(pixmap)
        self.threading_icon.setAlignment(Qt.AlignVCenter)
        self.title_hbox.addWidget(self.threading_icon)

    def updateProgress(self, relative_no, batch_size):
        # Calculate progress, update status and progress bar
        progress = round(relative_no / batch_size * 100)
        text_progress = f"{relative_no}/{batch_size}"

        if progress == 100:
            progress = 99

        remaining = batch_size - relative_no
        self.registerETA(remaining)

        self.state.setText(f"Downloading certificate {text_progress}")
        self.progress.setValue(progress)

    def downloadChange(self, change_type):
        # Calculate progress, update status and progress bar
        if (change_type == 0):
            self.state.setText(f"Comenzando lote número {self.file_no}")
            self.status_code = 1
        elif (change_type == 1):
            self.finish_time = time.time()
            self.eta = f"Completado"
            self.state.setText(f"Lote número {self.file_no} completado")
            self.progress.setValue(99)
            self.status_code = 3
        elif (change_type == 2):
            self.state.setText(f"Certificado número {self.file_no} guardado")
            self.progress.setValue(100)
            self.status_code = 4

        self.eta_label.setText(self.eta)

    def registerETA(self, remaining):
        unit_time = time.time() - self.started_last
        self.started_last = time.time()

        if self.threaded:
            unit_time /= 4

        self.time_history.append(unit_time)

        average_no = min(4, len(self.time_history))
        average = sum(self.time_history[-average_no:]) / average_no

        eta = round(average * remaining)
        self.eta = str(datetime.timedelta(seconds=eta))
        self.eta_label.setText(f"ETA: {self.eta}")

    def mousePressEvent(self, event):
        self.selected_item.emit()
        self.updateSelect(True)

    def updateSelect(self, selected=False):
        self.selected = selected

        if selected:
            self.setStyleSheet("""
                QWidget#DownloadItem {
                    border-radius: 4px;
                    background-color: #03A9F4
                }""")
        else:
            self.setStyleSheet("")

    def mouseDoubleClickEvent(self, event):
        if not self.details_open:
            self.details = DownloadDetails(self)
            self.details.show()
            self.details_open = True

    def cancelled(self):
        self.eta = "Cancelado"
        self.eta_label.setText(self.eta)

        self.state.setText("Trabajo cancelado")
        self.status_code = 5

    def stopThread(self):
        pass


class MainWindow(QMainWindow):
    _window_title = "Kangaroo: Consulta de Certificados"
    _main_icon = os.path.join("assets", "kangaroo.png")
    _max_downloads = 10
    _batch_size = 100
    _current_downloads = 0
    _download_items = []
    deselect_all = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.initUI()

        parser_handler = logging.StreamHandler()
        parser_handler.setLevel(logging.WARNING)
        CertificateParser.logger.addHandler(parser_handler)

    def initUI(self):
        self.setWindowTitle(self._window_title)
        self.setWindowIcon(QIcon(self._main_icon))

        # self.setGeometry(200, 200, 800, 420)
        self.resize(800, 420)
        self.setMinimumSize(600, 250)
        self.statusBar().showMessage('Listo')

        self.initMenu()
        self.initToolbar()

        self.scroll = QScrollArea()
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)

        self.dlds_widget = QWidget()
        self.downloads_vbox = QVBoxLayout()
        self.dlds_widget.setLayout(self.downloads_vbox)

        self.scroll.setWidget(self.dlds_widget)

        self.downloads_vbox.setAlignment(Qt.AlignTop)
        self.setCentralWidget(self.scroll)

    def initMenu(self):
        menubar = self.menuBar()
        editMenu = menubar.addMenu('&Editar')
        helpMenu = menubar.addMenu('&Ayuda')

        settings_act = QAction('&Configuración', self)
        settings_act.setShortcut('Ctrl+T')
        settings_act.setStatusTip('Cambiar ajustes')
        settings_act.triggered.connect(self.settings)

        about_act = QAction('&Acerca De', self)
        about_act.setStatusTip('Información del programa')
        about_act.triggered.connect(self.about)
        self.about = AboutWindow()

        editMenu.addAction(settings_act)
        helpMenu.addAction(about_act)

    def initToolbar(self):
        new_icon = QIcon().fromTheme('document-new')
        new_down_act = QAction(new_icon, '&Nueva Descarga', self)
        new_down_act.setShortcut('Ctrl+Alt+N')
        new_down_act.triggered.connect(self.newDownload)

        delete_icon = QIcon().fromTheme('edit-delete')
        delete_act = QAction(delete_icon, '&Eliminar', self)
        delete_act.setShortcut('Del')
        delete_act.triggered.connect(self.removeDownload)

        self.main_toolbar = self.addToolBar('Principal')
        self.main_toolbar.setIconSize(QSize(32, 32))
        self.main_toolbar.addAction(new_down_act)
        self.main_toolbar.addAction(delete_act)

    def newDownload(self):
        if self._current_downloads < self._max_downloads:
            dld_dialog = NewDownloadDialog(self._batch_size)

            if dld_dialog.exec() == 1:
                chosen_file = dld_dialog.cert_spin.value()
                preexistent_item = None

                for item in self._download_items:
                    if item.file_no == chosen_file and not item.disabled:
                        preexistent_item = item

                if preexistent_item is not None:
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Warning)

                    msg.setText("Ya existe una descarga igual")
                    msg.setWindowTitle("No se pudo añadir descarga")
                    msg.setStandardButtons(QMessageBox.Ok)
                    msg.exec()
                    return

                self._current_downloads += 1
                new_item = DownloadItem(self._batch_size,
                                        chosen_file,
                                        dld_dialog.thread_check.isChecked())

                new_item.selected_item.connect(self.unselectAll)
                self.deselect_all.connect(new_item.updateSelect)

                self._download_items.append(new_item)
                self.downloads_vbox.addWidget(self._download_items[-1])
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)

            msg.setText("Se alcanzó el máximo de descargas simultáneas")
            msg.setWindowTitle("No se pudo añadir descarga")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()

    def removeDownload(self):
        if len(self._download_items) == 0:
            return

        selected_item = None

        for item in self._download_items:
            if item.selected:
                selected_item = item

        if selected_item is None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)

            msg.setText("No hay descarga seleccionada")
            msg.setWindowTitle("No se pudo eliminar descarga")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            return

        print(f"Removing {selected_item.file_no}")
        self.downloads_vbox.removeWidget(selected_item)
        selected_item.deleteLater()
        selected_item.disabled = True

    def settings(self):
        print("Opened settings")

    def about(self):
        self.about.show()

    def unselectAll(self):
        self.deselect_all.emit()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Kangaroo")
    app.setApplicationVersion("0.1a")

    base_w = MainWindow()
    base_w.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
