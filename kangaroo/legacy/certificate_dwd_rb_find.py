#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-
import json
from robobrowser import RoboBrowser

browser = RoboBrowser(parser="lxml", history=False)
b_url = "http://www.pace.sep.gob.mx/certificadosdgb/certificadoremesadetalles/"
b_field = "_s_com_dgb_sep_domain_CertificadoRemesaDetalle_"
main_counter = 0

for j in range(120, 150):
    main_counter = j * 1000

    data = {}
    data['people_list'] = []

    for i in range(main_counter, main_counter + 1000):
        browser.open(f"{b_url}{str(i)}")

        plantel = browser.find(id=f"{b_field}tmpNombrePlantel_tmpNombrePlantel_id")

        if plantel:
            clave = browser.find(id=f"{b_field}tmpClaveCct_tmpClaveCct_id")
            rvoe = browser.find(id=f"{b_field}tmpRvoe_tmpRvoe_id")
            tipo_cert = browser.find(id=f"{b_field}tmpTipoCertificado_tmpTipoCertificado_id")
            cert = browser.find(id=f"{b_field}tmpFolioDigital_tmpFolioDigital_id")
            curp = browser.find(id=f"{b_field}idAlumno_idAlumno_id")
            nombre = browser.find(id=f"{b_field}tmpNombreCompleto_tmpNombreCompleto_id")
            matricula = browser.find(id=f"{b_field}matricula_matricula_id")
            promedio = browser.find(id=f"{b_field}promedio_promedio_id")
            periodo = browser.find(id=f"{b_field}tmpPeriodo_tmpPeriodo_id")

            student_dict = {"nombre": nombre.string,
                            "plantel": plantel.string,
                            "clave_trabajo": clave.string,
                            "rvoe": rvoe.string,
                            "curp": curp.string,
                            "matricula": matricula.string,
                            "promedio": promedio.string,
                            "periodo": periodo.string,
                            "tipo_certificado": tipo_cert.string,
                            "certificado": cert.string}

            data['people_list'].append(student_dict)
            print(cert.string)

        else:
            print("Skipped User")

    with open(f"certificate_data_{j+1:03}.json", 'w') as outfile:
        json.dump(data, outfile, indent=4, ensure_ascii=False)
