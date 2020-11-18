#!/usr/bin/env python3

"""
Kangaroo, una interfaz para facilitar
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

import time
import json
import bitmath
import logging
import hashlib
import datetime
import threading
from PyQt5 import QtCore
from pathlib import Path
from appdirs import user_config_dir
from enum import Enum, auto
from concurrent.futures import ThreadPoolExecutor
from lib.parser import CertificateParser


class DownloadState(Enum):
    DEFAULT = auto()
    CREATED = auto()
    STARTED = auto()
    COMPLETED = auto()
    SAVED = auto()
    STOPPED = auto()


class KangarooWarning(Enum):
    MAX_REACHED = 0
    DOWNLOAD_EXISTS = 1
    NOT_SELECTED = 2
    FOLDER_NOT_EXISTS = 3
    NOT_A_FOLDER = 4
    FILE_EXISTS = 5
    INVALID_NAME = 6


class CertState(Enum):
    DOWNLOADED = auto()
    NOT_FOUND = auto()
    FAILED = auto()


class DownloadTask(QtCore.QObject):
    """Represents a single download job"""

    # Fallback file cofiguration
    _filename_format = "certificate_data_{batch_number:03}.json"

    # Thread configuration
    _max_workers = 8
    _batch_size = 1000

    _state = DownloadState.DEFAULT

    state_change = QtCore.pyqtSignal(DownloadState)
    download_progress = QtCore.pyqtSignal()
    saving_error = QtCore.pyqtSignal(KangarooWarning)

    def __init__(self, batch_number, threaded=True, folder=None,
                 filename_format=None, batch_size=None, max_workers=None):
        """DownloadTask constructor

        Keyword arguments:

        :param int batch_number: Number of batch to download
        :param bool threaded: If download should use multithreading
        :param int batch_size: Size of batch to download
        :param int max_workers: Workers to use for multithreading
        :param str folder: Folder name of location to save file
        :param str filename_format: Custom file naming format
        """

        super().__init__()
        self._creation_time = time.time()

        self._download_log = []
        self._download_statuses = []
        self._download_times = []
        self._download_items = {}

        self.state = DownloadState.CREATED

        self.cert_parser = CertificateParser()

        self._batch = batch_number
        self.threaded = threaded

        self._folder = folder or ''

        if filename_format is not None:
            self._filename_format = filename_format

        if batch_size is not None:
            self._batch_size = batch_size

        if max_workers is not None:
            self._max_workers = max_workers

        self.cancel_event = threading.Event()

    def formatName(self):
        """
        Will only be called when about to save the download as a file

        Available parameters for file naming:

        {batch_number}      Batch Number
        {batch_size}        Batch Size (Number of requested certificates)
        {now}               Datetime object, created when saving file
                            By default outputs ISO Format
                            Format precisely using syntax {now:parameters}
                            See https://strftime.org/ for all parameters
                            Example: {now:%d} will output the day of the month
        {created}           Timestamp of item's creation
        {completed}         Timestamp of download completion

        """

        format_options = {
            'batch_number': self.batch,
            'batch_size': self.batch_size,
            'now': datetime.datetime.now(),
            'created': self.creation_time,
            'completed': self.completion_time
        }

        try:
            filename = f"{self._filename_format.format(**format_options)}"
        except KeyError as e:
            raise ValueError(f"Invalid filename format: {e}")

        return filename

    def asyncStart(self):
        self.main_thread = threading.Thread(target=self.start)
        self.main_thread.start()

    def start(self):
        """Starts the download thread"""
        self.state = DownloadState.STARTED
        cert_data = {}

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            self.started_last = time.time()

            for cert in range(self.range_start, self.range_end):
                if self.threaded:
                    new_parse = executor.submit(self.parseWrapper, cert)
                else:
                    if self.cancel_event.is_set():
                        return
                    new_parse = self.parseWrapper(cert)

                self._download_items[cert] = new_parse

            for cert_no, new_cert in self._download_items.items():
                if self.threaded:
                    if new_cert.cancelled():
                        return
                    new_cert = new_cert.result()

                if new_cert:
                    new_cert.pop('number')

                cert_data[cert_no] = new_cert

        self.cert_data = cert_data
        self._completion_time = time.time()
        self.state = DownloadState.COMPLETED

        self.saveFile()

    def parseWrapper(self, cert_number):
        cert_parse = self.cert_parser.parse(cert_number)
        self.logDownloadState(cert_parse, cert_number)

        if (cert_number % self._max_workers == 0) or not self.threaded:
            self.current_cert = cert_number
            self.registerLastWait()
            self.download_progress.emit()

        return cert_parse

    def saveFile(self, overwrite=False):
        try:
            self._output_file = Path(self._folder) / self.formatName()
        except ValueError:
            self.saving_error.emit(KangarooWarning.INVALID_NAME)
            return

        if not Path(self._folder).exists():
            self.saving_error.emit(KangarooWarning.FOLDER_NOT_EXISTS)
            return

        if self._output_file.exists() and not overwrite:
            self.saving_error.emit(KangarooWarning.FILE_EXISTS)
            return

        with open(self._output_file, 'w') as outfile:
            json.dump(self.cert_data, outfile, indent=4, ensure_ascii=False)

        self._file_size = self.calculateSize()
        self._md5 = self.calculateHash(hashlib.md5)
        self._sha1 = self.calculateHash(hashlib.sha1)

        self.state = DownloadState.SAVED

    def stop(self):
        if self.running and not self.cancelled:
            """Stops the download thread"""
            self.state = DownloadState.STOPPED

            if self.threaded:
                for i in self._download_items.values():
                    i.cancel()
            else:
                self.cancel_event.set()

    def logDownloadState(self, cert_item, cert_number):
        cert_state = CertState.DOWNLOADED

        if cert_item is None:
            cert_state = CertState.NOT_FOUND
        elif cert_item is False:
            cert_state = CertState.FAILED

        self._download_log.append((cert_number, cert_state))
        self._download_statuses.append(cert_state)

    def registerLastWait(self):
        unit_time = time.time() - self.started_last
        self.started_last = time.time()
        self._download_times.append(unit_time)

    @property
    def eta(self):
        if (self.state is not DownloadState.STOPPED
                and (len(self._download_times) >= 1)):
            # Average a max of 4 or as many waiting times have been recorded
            to_average = min(4, len(self._download_times))
            average = sum(self._download_times[-to_average:]) / to_average

            remaining_packets = self.batch_size - self.relative_cert

            if self.threaded:
                remaining_packets = remaining_packets / self._max_workers

            eta = round(average * remaining_packets)

            return str(datetime.timedelta(seconds=eta))

    @property
    def avg_speed(self):
        if (self.state is not DownloadState.STOPPED
                and (len(self._download_times) >= 1)):
            average_wait = sum(self._download_times) / len(self._download_times)

            if self.threaded:
                average_wait = average_wait / self._max_workers

            return f"{round(average_wait ** -1, 2)} /s"

    @property
    def download_log(self):
        return self._download_log

    def calculateHash(self, algorithm=hashlib.md5):
        hasher = algorithm()

        with open(self._output_file, 'rb') as batch_file:
            hasher.update(batch_file.read())

        return hasher.hexdigest()

    def calculateSize(self):
        return bitmath.getsize(self._output_file).format("{value:.2f} {unit}")

    @property
    def relative_cert(self):
        return (self.current_cert - self.range_start)

    @property
    def progress(self):
        progress = round(self.relative_cert / self.batch_size * 100)

        if progress == 100:
            progress = 99

        return progress

    @property
    def range_start(self):
        return self.batch_size * (self.batch - 1)

    @property
    def range_end(self):
        return self.batch_size * self.batch

    @property
    def batch(self):
        return self._batch

    @property
    def batch_size(self):
        return self._batch_size

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, new_state):
        self.state_change.emit(new_state)
        self._state = new_state

    @property
    def running(self):
        return self.state not in (DownloadState.STOPPED,
                                  DownloadState.COMPLETED,
                                  DownloadState.SAVED)

    @property
    def cancelled(self):
        return self.state is DownloadState.STOPPED

    @property
    def creation_time(self):
        return self._creation_time

    def timestampToISO(self, timestamp):
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))

    @property
    def creation_iso_time(self):
        return self.timestampToISO(self.creation_time)

    @property
    def elapsed_time(self):
        elapsed_end = self.completion_time or time.time()
        elapsed_s = round(elapsed_end - self.creation_time)
        return str(datetime.timedelta(seconds=elapsed_s))

    @property
    def remaining_time(self):
        return self._foo

    @property
    def completion_iso_time(self):
        if not self.running and not self.cancelled:
            return self.timestampToISO(self.completion_time)

    @property
    def completion_time(self):
        if not self.running and not self.cancelled:
            return self._completion_time

    @property
    def fetched_certs(self):
        return len(self._download_statuses)

    @property
    def successful_certs(self):
        return self._download_statuses.count(CertState.DOWNLOADED)

    @property
    def failed_certs(self):
        return self._download_statuses.count(CertState.FAILED)

    @property
    def not_found_certs(self):
        return self._download_statuses.count(CertState.NOT_FOUND)

    @property
    def file_location(self):
        return str(Path(self._folder).resolve())

    @property
    def file_name(self):
        if self.state is DownloadState.SAVED:
            return self._output_file.name

    @property
    def file_size(self):
        if self.state is DownloadState.SAVED:
            return self._file_size

    @property
    def md5(self):
        if self.state is DownloadState.SAVED:
            return self._md5

    @property
    def sha1(self):
        if self.state is DownloadState.SAVED:
            return self._sha1


class KangarooModel:
    # Default filename format, configurable
    _folder = "Certificates_GUI"
    _filename_format = "certificate_data_{batch_number:03}.json"
    _config_filename = "kangaroo_config.json"

    _max_downloads = 0
    _batch_size = 100
    _download_items = []

    def __init__(self):
        # Load default configuration
        self.config_folder = Path(Path.home() / '.config')

        appdirs_folder = Path(user_config_dir(appauthor="WeAreMagic",
                                              roaming=True))
        if appdirs_folder.exists():
            self.config_folder = appdirs_folder

        self.config_file = self.config_folder / self._config_filename

        if self.config_file.exists():
            self.loadConfig(self.config_file)

        # Set logging parameters
        parser_handler = logging.StreamHandler()
        parser_handler.setLevel(logging.WARNING)
        CertificateParser.logger.addHandler(parser_handler)

    def createDownload(self, batch_number, threaded):
        if self.download_count < self._max_downloads:
            return KangarooWarning.MAX_REACHED

        preexistent_task = None

        for task in self._download_items:
            if task.batch == batch_number and task.running:
                preexistent_task = task

        if preexistent_task is not None:
            return KangarooWarning.DOWNLOAD_EXISTS

        new_download = DownloadTask(batch_number=batch_number,
                                    threaded=threaded,
                                    folder=self._folder,
                                    filename_format=self._filename_format,
                                    batch_size=self.batch_size)
        self._download_items.append(new_download)
        return new_download

    def loadConfig(self, config):
        with open(config) as config_file:
            config_json = json.load(config_file)

            self.batch_size = config_json['batch_size']
            self.filename_format = config_json['filename_format']

            try:
                self.download_folder = config_json['download_folder']
            except (FileNotFoundError, NotADirectoryError):
                print("Erroneous value in config file")

    def saveConfig(self):
        with open(self.config_file, 'w') as config_out:
            config_dict = {'batch_size': self.batch_size,
                           'filename_format': self.filename_format,
                           'download_folder': self.download_folder}

            json.dump(config_dict, config_out, indent=4, ensure_ascii=False)

    def deleteTask(self, task):
        self._download_items.remove(task)

    @property
    def download_count(self):
        return len(self._download_items)

    def stopAll(self):
        for item in self._download_items:
            item.stop()

    @property
    def filename_format(self):
        return self._filename_format

    @filename_format.setter
    def filename_format(self, format):
        self._filename_format = format

    @property
    def download_folder(self):
        return self._folder

    @download_folder.setter
    def download_folder(self, folder):
        new_location = Path(folder)
        if not new_location.exists():
            raise FileNotFoundError("Download folder does not exist")
        if not new_location.is_dir():
            raise NotADirectoryError("Download location must be a folder")

        self._folder = folder

    @property
    def batch_size(self):
        return self._batch_size

    @batch_size.setter
    def batch_size(self, size):
        self._batch_size = size
