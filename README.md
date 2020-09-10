# CertificateParser
### Asistente de descarga de certificados de bachillerato de la SEP

CertificateParser es una librería e interfaz gráfica para facilitar la descarga en paralelo de _datos de certificados del bachillerato mexicano_

```python
>>> from CURPValidator import CURPValidator
>>> CURPValidator.validate('POPC990709MGTSRL02', 'CLAUDIA LEONOR POSADA PEREZ')
{'nombre': 'CLAUDIA LEONOR', 'apellido': 'POSADA', 'apellido_m': 'PEREZ'}
	
# Funciona con prefijos como Del, De la, De los, etc
>>> CURPValidator.validate('MAGE981117MMNCRS05', 'ESTEFANIA DE LOS DOLORES MACIAS GARCIA')
{'nombre': 'ESTEFANIA DE LOS DOLORES', 'apellido': 'MACIAS', 'apellido_m': 'GARCIA'}

>>> CURPValidator.validate('MAPS991116MOCRZN07', 'SANDRA DEL CARMEN MARTINEZ DE LA PAZ')
{'nombre': 'SANDRA DEL CARMEN', 'apellido': 'MARTINEZ', 'apellido_m': 'DE LA PAZ'}
	
# Detecta ausencia de un segundo apellido
>>> CURPValidator.validate('TAXA990915MNEMXM06', 'AMBER NICOLE TAMAYO')
{'nombre': 'AMBER NICOLE', 'apellido': 'TAMAYO', 'apellido_m': ''}
	
# Detección de CURPs con palabras altisonantes
>>> CURPValidator.validate('MXME991209MGRRSS07', 'ESMERALDA MARTINEZ MASTACHE ')
{'nombre': 'ESMERALDA', 'apellido': 'MARTINEZ', 'apellido_m': 'MASTACHE'}

# Regresa False en caso de no coincidir el nombre y la curp
>>> CURPValidator.validate('MACD990727MMMCRRN0', 'DANIELA IVETTE MARTINEZ CRUZ')
False
```
	 

Este programa se distribuye bajo la licencia GNU 2.0, más información en el sitio de la [Free Software Foundation](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html) 

