"""Evalúa el filtro sobre la captura estable guardada y un escalón sintético."""
import csv
import json
import statistics
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from denoising import voltage_filters, VoltageKalman, NOISE_VARIANCES


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    args=parser.parse_args()
    with args.csv.open(encoding='utf-8-sig') as file:
        rows=[tuple(map(float,row)) for row in list(csv.reader(file))[1:]]
    filters=voltage_filters()
    clean=[(t,filters[0].update(t,vf),filters[1].update(t,vd)) for t,vf,vd in rows]
    result={'note':'R estimado en t < 5 s; evaluación descriptiva en t >= 5 s. Sin referencia limpia: variación, no exactitud.', 'channels':{}}
    for index,name in ((1,'force'),(2,'deformation')):
        original=[row[index] for row in rows if row[0]>=5]
        filtered=[row[index] for row in clean if row[0]>=5]
        raw_std,clean_std=statistics.stdev(original),statistics.stdev(filtered)
        result['channels'][name]={'raw_std_mv':raw_std*1000,'kalman_std_mv':clean_std*1000,
                                 'std_reduction_percent':100*(1-clean_std/raw_std)}
    f=VoltageKalman(NOISE_VARIANCES[0])
    for i in range(200): f.update(i*.01,0)
    step=[f.update(2+i*.01,1) for i in range(100)]
    result['synthetic_step_t90_seconds']=next(i*.01 for i,v in enumerate(step) if v>=.9)
    args.csv.with_name(args.csv.stem+'_kalman.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    with args.csv.with_name(args.csv.stem+'_kalman.csv').open('w',newline='',encoding='utf-8-sig') as file:
        writer=csv.writer(file)
        writer.writerow(('tiempo_s','fuerza_bruta_V','deformacion_bruta_V','fuerza_kalman_V','deformacion_kalman_V'))
        writer.writerows((*raw,flt[1],flt[2]) for raw,flt in zip(rows,clean))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,1,figsize=(11,6),sharex=True,layout='constrained')
    for ax,index,title in zip(axes,(1,2),('Fuerza','Deformación')):
        ax.plot([r[0] for r in rows],[r[index]*1000 for r in rows],color='#a1b6c5',lw=.6,label='Original')
        ax.plot([r[0] for r in clean],[r[index]*1000 for r in clean],color='#ba4c28',lw=1.5,label='Kalman causal')
        ax.axvline(5,color='#333333',ls='--',lw=.8,label='Inicio de evaluación')
        ax.set_ylabel(title+' (mV)'); ax.grid(alpha=.2); ax.legend(loc='upper right')
    axes[-1].set_xlabel('Tiempo (s)')
    fig.suptitle('Limpieza de ruido · Captura real USB-4716\nAjuste de ruido: primeros 5 s · Evaluación: últimos 5 s')
    fig.savefig(args.csv.with_name(args.csv.stem+'_kalman.png'),dpi=160)
    print(json.dumps(result,indent=2,ensure_ascii=False))


if __name__=='__main__': main()
