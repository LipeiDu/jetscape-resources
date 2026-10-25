"""Readers for explicitly pinned SIMS inputs; no upstream Python code or pickle execution."""
from pathlib import Path
import csv
import io
import json
import zipfile
import numpy as np


def read_design_archive(path):
    prefix = 'design_pts_Pb_Pb_2760_production/'
    with zipfile.ZipFile(path) as archive:
        text = archive.read(prefix+'design_points_main_PbPb-2760.dat').decode()
        ranges = list(csv.DictReader(io.StringIO(archive.read(prefix+'design_ranges_main_PbPb-2760.dat').decode())))
    rows = list(csv.DictReader(io.StringIO(text)))
    names = [key for key in rows[0] if key != 'idx']
    ids = np.array([int(row['idx']) for row in rows])
    values = np.array([[float(row[key]) for key in names] for row in rows])
    if not np.array_equal(ids, np.arange(len(ids))) or not np.isfinite(values).all():
        raise ValueError('Expected ordered, unique design IDs starting at zero and finite design values')
    if [row['param'] for row in ranges] != names:
        raise ValueError('Design and prior coordinate order disagree')
    return ids, names, values, {r['param']: (float(r['min']), float(r['max'])) for r in ranges}


def observable_dtype(schema, systems):
    return np.dtype([(system, [(name, [('mean','<f8',len(bins)),('err','<f8',len(bins))])
                              for name, bins in schema['systems'][system].items()], schema['number_of_models'])
                     for system in systems])


def read_model(path, schema, system, *, map_record=False):
    """Exact byte-length checks, including the pinned Pb MAP file's zero-filled Au block."""
    payload = Path(path).read_bytes()
    if map_record and system == 'Pb-Pb-2760':
        dtype = observable_dtype(schema, ['Pb-Pb-2760','Au-Au-200'])
        if len(payload) != dtype.itemsize:
            raise ValueError('Pinned Pb MAP compound-record size mismatch')
        records = np.frombuffer(payload, dtype=dtype)
        tail_offset = dtype.fields['Au-Au-200'][1]
        if any(payload[tail_offset:]):
            raise ValueError('Expected documented zero-filled Au padding block in the Pb MAP file')
    else:
        dtype = observable_dtype(schema, [system])
        if not payload or len(payload) % dtype.itemsize:
            raise ValueError('Model bytes do not match the declared dtype; no trailing bytes may be ignored')
        records = np.frombuffer(payload, dtype=dtype)
        if map_record and len(records) != 1:
            raise ValueError('Expected one MAP record')
    return records[system]


def viscosity_curves(temperature, point):
    temperature = np.asarray(temperature, dtype=float)
    delta = temperature - point['eta_over_s_T_kink_in_GeV']
    slope = np.where(delta < 0, point['eta_over_s_low_T_slope_in_GeV'], point['eta_over_s_high_T_slope_in_GeV'])
    shear = np.maximum(0, point['eta_over_s_at_kink'] + slope*delta)
    offset = temperature - point['zeta_over_s_T_peak_in_GeV']
    width = point['zeta_over_s_width_in_GeV']*(1+point['zeta_over_s_lambda_asymm']*np.sign(offset))
    bulk = point['zeta_over_s_max']/(1+(offset/width)**2)
    return shear, bulk
