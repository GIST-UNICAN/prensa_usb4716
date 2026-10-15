"""UNE-EN 12697-34:2022: definiciones 3.1–3.5, 7.1–7.4 y anexo A.

Resultados individuales calculados, no certificación del ensayo completo.
La norma no prescribe el algoritmo numérico de ajuste automático de tangente.
"""
import math
from decimal import Decimal,ROUND_HALF_UP

STANDARD='UNE-EN 12697-34:2022'
STANDARD_TITLE='Mezclas bituminosas. Métodos de ensayo. Parte 34: Ensayo Marshall.'
STANDARD_URL='https://tienda.aenor.com/p/norma-une-en-12697-34-2022-n0068669'
LABELS=[('peak_kp','Carga máxima (kp)'),('raw_stability_kn','Carga máxima sin corregir (kN)'),
 ('stability_kn','Estabilidad S corregida (kN)'),('flow_mm','Deformación F corregida (mm)'),
 ('tangential_flow_mm','Deformación tangencial Ft (mm)'),('total_flow_mm','Deformación total FT (mm)'),
 ('quotient_kn_mm','Cociente Marshall S/F (kN/mm)'),('zero_mm','Cero de la tangente A (mm)'),
 ('correction_factor','Factor de corrección c')]


def tenth(value):
    return float(Decimal(str(value)).quantize(Decimal('.1'),rounding=ROUND_HALF_UP))


def normative(result,height=None,volume=None):
    for key,_ in LABELS:
        if key not in ('peak_kp','zero_mm'):result[key]=None
    result['standard']=STANDARD
    result['standard_sections']='3.1–3.5; 7.1–7.4; anexo A, figura A.1'
    result['normative_note']='Resultados individuales. Falta altura h o volumen v para corregir S y calcular S/F.'
    peak=result.get('peak_kp')
    if peak is None:return result
    load=peak*.00980665
    result['raw_stability_kn']=tenth(load);result['raw_stability_exact_kn']=load
    x=result.get('peak_mm');zero=result.get('zero_mm');slope=result.get('slope_kp_mm')
    result['flow_exact_mm']=x-zero if x is not None and zero is not None and x>zero else None
    if result['flow_exact_mm'] is not None:result['flow_mm']=tenth(result['flow_exact_mm'])
    if slope is not None and slope>0:result['tangential_flow_mm']=tenth(peak/slope)
    if x is not None and x>=0:result['total_flow_mm']=tenth(x)
    h=height if isinstance(height,(int,float)) and math.isfinite(height) and height>0 else None
    v=volume if isinstance(volume,(int,float)) and math.isfinite(volume) and volume>0 else None
    factor=5.2*math.exp(-.0259*h) if h is not None else 5.2*math.exp(-3.2e-6*v) if v is not None else None
    if factor is not None:
        result['correction_factor']=factor;result['stability_kn']=tenth(load*factor)
        if result['flow_exact_mm'] is not None:result['quotient_kn_mm']=tenth(load*factor/result['flow_exact_mm'])
        result['normative_note']='Corrección por altura h.' if h is not None else 'Corrección por volumen v.'
        if h is not None and not 60.5<=h<=66.5:result['normative_note']+=' Altura fuera de 60,5–66,5 mm: la norma advierte de menor precisión.'
    return result
