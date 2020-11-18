#!/usr/bin/env python3

"""
Controlador de QtKangaroo, una interfaz gráfica
para Kangaroo, basada en PyQt

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

import sys
from pathlib import Path
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox
from qt.qt_elements import (KangarooWindow, DownloadDialog, DownloadItem,
                            KangarooSettings, DownloadDetails)

from kangaroo import (KangarooModel, KangarooWarning as KW, DownloadState)


class DownloadController:
    """Controller for DownloadTask"""

    def __init__(self, project_root, task):
        self.model = task

        self.project_root = project_root
        self.initUI()

        # Create new timer for elapsed time
        self.timer = QTimer()
        self.timer.timeout.connect(self.updateElapsed)

    def initUI(self):
        self.ui_item = DownloadItem(self.project_root,
                                    f"Descarga de lote {self.model.batch}",
                                    self.model.threaded)

        # To update UI when major changes happen (cancel, saved, etc)
        self.model.state_change.connect(self.ui_item.setDownloadEvent)
        self.model.state_change.connect(self.updateDetailsEvent)

        # To update UI when download makes progress
        self.model.download_progress.connect(self.updateProgress)
        self.model.download_progress.connect(self.updateDetailsProgress)

        # To handle saving exceptions
        self.model.saving_error.connect(self.saveError)

        self.ui_item.setDownloadEvent(self.model.state)
        self.ui_item.double_clicked.connect(self.openDetails)

        self.details = DownloadDetails(self.project_root)
        self.reloadOperationTab()
        self.reloadFileTab()
        self.reloadBatchTab()
        self.details.closed_window.connect(self.detailsClosed)

        self.model.asyncStart()

    def openDetails(self):
        self.updateElapsed()
        self.details.show()
        self.timer.start(1000)

    def stopTask(self):
        self.model.stop()

    def delete(self):
        self.ui_item.deleteLater()

    def updateDetailsEvent(self, event):
        if event is DownloadState.COMPLETED:
            self.reloadBatchTab()
            self.reloadOperationTab()
        if event is DownloadState.SAVED:
            self.reloadFileTab()

    def updateDetailsProgress(self):
        self.reloadOperationTab()
        self.reloadBatchTab()

    def updateProgress(self):
        if not self.model.cancelled:
            text_progress = f"{self.model.relative_cert}/{self.model.batch_size}"
            self.ui_item.setProgressText(f"Fetched certificate {text_progress}")
            self.ui_item.setProgress(self.model.progress)
            self.ui_item.setETA(self.model.eta)

    def updateElapsed(self):
        self.details.updateElapsed(self.model.elapsed_time)

    def reloadOperationTab(self):
        self.details.initOpTab(start_time=self.model.creation_iso_time,
                               remaining_time=self.model.eta,
                               completion_time=self.model.completion_iso_time,
                               avg_speed=self.model.avg_speed)

    def reloadBatchTab(self):
        self.details.initBatchTab(log=self.model.download_log,
                                  downloaded=self.model.successful_certs,
                                  failed=self.model.failed_certs,
                                  not_found=self.model.not_found_certs,
                                  batch_size=self.model.batch_size)

    def reloadFileTab(self):
        self.details.initFileTab(file_name=self.model.file_name,
                                 file_location=self.model.file_location,
                                 file_size=self.model.file_size,
                                 sha_one=self.model.sha1,
                                 md5=self.model.md5)

    def detailsClosed(self):
        self.timer.stop()
        self.ui_item.closeDetails()

    def saveError(self, error_type):
        if error_type is KW.FILE_EXISTS:
            if self.ui_item.askOverwrite() == QMessageBox.Yes:
                self.model.saveFile(True)

    def deselectUI(self):
        self.ui_item.selected = False

    @property
    def selected(self):
        return self.ui_item.selected


class KangarooController:
    """Controller for QtKangaroo and KangarooModel"""
    downloads = []

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("QtKangaroo")
        self.app.setApplicationVersion("0.4a")
        self.project_root = Path(__file__).parent.parent

        self.model = KangarooModel()
        self.initUI()

    def initUI(self):
        self.main_window = KangarooWindow(self.project_root)
        self.main_window.show()
        self.main_window.open_settings.triggered.connect(self.openSettings)

        self.main_window.new_download.triggered.connect(self.newDownload)
        self.main_window.cancel_download.triggered.connect(self.cancelDownload)
        self.main_window.delete_download.triggered.connect(self.deleteDownload)

        self.main_window.close_app.connect(self.app.closeAllWindows)

    def newDownload(self):
        self.d_dialog = DownloadDialog(self.project_root,
                                       self.model.batch_size,
                                       self.model.filename_format)
        dialog_exec = self.d_dialog.exec()

        if dialog_exec == QDialog.Accepted:
            batch_no = self.d_dialog.batch_no_spin.value()
            threading = self.d_dialog.threading_check.isChecked()

            create = self.model.createDownload(batch_no, threading)

            if create is KW.MAX_REACHED:
                self.main_window.displayWarning(KW.MAX_REACHED)
            elif create is KW.DOWNLOAD_EXISTS:
                self.main_window.displayWarning(KW.DOWNLOAD_EXISTS)
            else:
                new_controller = DownloadController(self.project_root, create)
                new_controller.ui_item.selected_event.connect(self.deselectAll)
                new_controller.model.saving_error.connect(self.saveError)
                self.downloads.append(new_controller)
                self.main_window.appendDownload(new_controller.ui_item)

    def cancelDownload(self):
        for controller in self.downloads:
            if controller.selected:
                controller.stopTask()

    def deleteDownload(self):
        for controller in self.downloads:
            if controller.selected:
                controller.stopTask()
                self.main_window.removeDownload(controller.ui_item)
                self.model.deleteTask(controller.model)
                controller.delete()
                self.downloads.remove(controller)

    def deselectAll(self):
        for controller in self.downloads:
            controller.deselectUI()

    def openSettings(self):
        self.settings = KangarooSettings(self.project_root,
                                         self.model.download_folder,
                                         self.model.filename_format,
                                         self.model.batch_size)
        self.settings.saved_settings.connect(self.saveSettings)
        self.settings.show()

    def saveSettings(self, new_path, new_filename, new_batch_size):
        try:
            self.model.download_folder = new_path
            self.model.filename_format = new_filename
            self.model.batch_size = new_batch_size
        except FileNotFoundError:
            self.main_window.displayWarning(KW.FOLDER_NOT_EXISTS)
        except NotADirectoryError:
            self.main_window.displayWarning(KW.NOT_A_FOLDER)

        self.model.saveConfig()

    def saveError(self, error_type):
        if error_type is KW.INVALID_NAME:
            self.main_window.displayWarning(KW.INVALID_NAME)
        elif error_type is KW.FOLDER_NOT_EXISTS:
            self.main_window.displayWarning(KW.FOLDER_NOT_EXISTS)


def main():
    controller = KangarooController()
    controller.app.exec()


if __name__ == '__main__':
    main()
