#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-
import os
import time
import json
import requests
import concurrent.futures
from main import CertificateParser

# 1. Assign different threads to download certificates in a range
# 2. When all done, save to file

cert_base_path = os.path.join("Certificates_EXP", "certificate_data_")


def downloadFile(file_no):
    cert_parser = CertificateParser()

    data = {}
    data['cert_data'] = []

    start = file_no * 1000
    end = start + 1000

    for cert in range(start, end):
        new_cert = False
        query_status = False
        attempts = 0

        while not query_status and attempts < 8:
            try:
                new_cert = cert_parser.parse(cert)
                query_status = True
            except requests.exceptions.ConnectionError:
                print(f"Attempting again {cert} ({attempts})")
                attempts += 1
        data['cert_data'].append(new_cert)

    with open(f"{cert_base_path}{file_no+1:03}.json", 'w') as outfile:
        print(f"Retrieved batch number {file_no}")
        json.dump(data, outfile, indent=4, ensure_ascii=False)

    return f"Batch {file_no} completed"


file_timer_start = time.perf_counter()

with concurrent.futures.ThreadPoolExecutor() as executor:
    results = [executor.submit(downloadFile, i) for i in range(250, 260)]

    for f in concurrent.futures.as_completed(results):
        try:
            print(f.result())
        except Exception as exc:
            print(f"Some file download generated an exception: {exc}")

file_timer_end = time.perf_counter()
op_duration = round(file_timer_end - file_timer_start, 2)
print(f"Operation took {op_duration} s")
