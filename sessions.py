"""Archivo transaccional de ensayos y formato portátil versionado."""
from __future__ import annotations
import json
import math
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

FORMAT = 'marshall-session'
FIELDS = ('t', 'vf', 'vd', 'force_kp', 'deformation_mm')


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def make_session(samples, metadata, configuration=None, session_id=None, acquired_at=None):
    rows = []
    for sample in samples:
        row = asdict(sample)
        for key in ('vf', 'vd'):
            if not math.isfinite(row[key]): row[key] = None
        rows.append(row)
    session = dict(format=FORMAT, version=1, id=session_id or str(uuid4()),
                   acquired_at=acquired_at, saved_at=timestamp(), metadata=dict(metadata),
                   configuration=configuration, samples=rows)
    validate_session(session)
    return session


def validate_session(session):
    if not isinstance(session, dict) or session.get('format') != FORMAT or session.get('version') != 1:
        raise ValueError('Formato de ensayo o versión no compatible.')
    for key in ('id', 'saved_at'):
        if not isinstance(session.get(key), str) or not session[key]: raise ValueError(f'Falta {key}.')
    if session.get('acquired_at') is not None and not isinstance(session['acquired_at'], str):
        raise ValueError('Fecha de adquisición inválida.')
    meta = session.get('metadata')
    if not isinstance(meta, dict): raise ValueError('Metadatos inválidos.')
    for key in ('reference', 'operator', 'sample_id', 'notes', 'source'):
        if not isinstance(meta.get(key, ''), str): raise ValueError(f'Metadato inválido: {key}.')
    if meta.get('demo') not in (True, False, None): raise ValueError('Modo de adquisición inválido.')
    if session.get('configuration') is not None and not isinstance(session['configuration'], dict):
        raise ValueError('Configuración inválida.')
    rows = session.get('samples')
    if not isinstance(rows, list) or not rows: raise ValueError('El ensayo no contiene muestras.')
    previous = -math.inf
    for i, row in enumerate(rows, 1):
        if not isinstance(row, dict) or not all(key in row for key in FIELDS): raise ValueError(f'Muestra {i} incompleta.')
        for key in FIELDS:
            value = row.get(key)
            if value is None and key in ('vf', 'vd'): continue
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
                raise ValueError(f'Muestra {i}: {key} debe ser finito.')
        if row['t'] < 0 or row['t'] < previous: raise ValueError('Los tiempos deben estar ordenados y ser positivos.')
        previous = row['t']
    # También impide NaN/Infinity dentro de la configuración.
    json.dumps(session, allow_nan=False)
    return session


def session_summary(session):
    rows = session['samples']; peak = max(rows, key=lambda row: row['force_kp'])
    duration = rows[-1]['t']-rows[0]['t']
    return dict(points=len(rows), duration_s=duration, peak_kp=peak['force_kp'],
                peak_kn=peak['force_kp']*.00980665, deformation_at_peak_mm=peak['deformation_mm'],
                max_deformation_mm=max(row['deformation_mm'] for row in rows),
                speed_mm_min=(rows[-1]['deformation_mm']-rows[0]['deformation_mm'])*60/duration if duration else None)


def dumps_session(session):
    validate_session(session)
    return json.dumps(session, ensure_ascii=False, allow_nan=False, indent=2)


def load_session(path):
    return validate_session(json.loads(Path(path).read_text(encoding='utf-8-sig')))


class SessionStore:
    def __init__(self, path): self.path = Path(path)

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.path)
        con.execute('''CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY, saved_at TEXT NOT NULL, header TEXT NOT NULL, payload TEXT NOT NULL)''')
        return con

    def save(self, session):
        payload = dumps_session(session)
        header = {key:value for key,value in session.items() if key != 'samples'}
        header['summary'] = session_summary(session)
        con = self._connect()
        try:
            with con:
                con.execute('INSERT OR REPLACE INTO sessions VALUES (?, ?, ?, ?)',
                            (session['id'], session['saved_at'], json.dumps(header, ensure_ascii=False), payload))
        finally: con.close()

    def list(self, query='', mode='Todos'):
        con = self._connect()
        try: rows = con.execute('SELECT header FROM sessions ORDER BY saved_at DESC, rowid DESC').fetchall()
        finally: con.close()
        result=[]
        for (raw,) in rows:
            item=json.loads(raw); meta=item['metadata']
            if query.casefold() not in ' '.join(str(meta.get(k,'')) for k in ('reference','operator','sample_id','notes')).casefold(): continue
            if mode == 'Simulación' and meta.get('demo') is not True: continue
            if mode == 'Real' and meta.get('demo') is not False: continue
            if mode == 'Importado / desconocido' and meta.get('demo') is not None: continue
            result.append(item)
        return result

    def get(self, session_id):
        con = self._connect()
        try: row = con.execute('SELECT payload FROM sessions WHERE id=?', (session_id,)).fetchone()
        finally: con.close()
        if not row: raise ValueError('El ensayo ya no está disponible.')
        return validate_session(json.loads(row[0]))

    def delete(self, session_id):
        """Elimina únicamente el registro confirmado, en una transacción."""
        con=self._connect()
        try:
            with con:
                cursor=con.execute('DELETE FROM sessions WHERE id=?',(session_id,))
                if cursor.rowcount!=1:raise ValueError('El ensayo ya no está disponible.')
        finally:con.close()
