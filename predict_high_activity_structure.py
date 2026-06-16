import csv
import math
import re
from pathlib import Path

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, LeaveOneOut, cross_val_predict
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "aunc_data.csv"
CANDIDATE_FILE = ROOT / "candidate_data.csv"
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

NUMBER = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")

def num(value):
    if value is None:
        return math.nan
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("−", "-").replace("–", "-")
    if text.upper() in {"", "NA", "N/A", "NONE", "NULL"}:
        return math.nan
    found = NUMBER.search(text)
    if not found:
        return math.nan
    try:
        return float(found.group(0))
    except ValueError:
        return math.nan

def read_csv(path):
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path, rows, fields=None):
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def percentile(values, p):
    values = sorted([v for v in values if not math.isnan(v)])
    if not values:
        return math.nan
    if len(values) == 1:
        return values[0]
    pos = (len(values) - 1) * p
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return values[lo]
    return values[lo] * (hi - pos) + values[hi] * (pos - lo)

def row_id(row):
    return row.get("candidate_id") or row.get("sample_id") or row.get("reference_id") or ""

NUMERIC_ALL = [
    "gold_atom_count", "diameter_TEM_nm", "diameter_DLS_nm", "diameter_nm",
    "diameter_sd_nm", "pdi_or_cv", "zeta_mV", "emission_peak_nm",
    "excitation_wavelength_nm", "quantum_yield_percent", "homo_lumo_gap_eV",
    "electronegativity_avg_pauling", "surface_area_volume_nm_inv",
    "ligand_binding_energy_kJ_mol", "ligand_grafting_density_nm2",
    "synthesis_temperature_C", "synthesis_time_h", "pH",
    "HAuCl4_concentration_mM", "NaOH_concentration_M"
]

CAT_ALL = [
    "core", "ligand", "ligand_family", "ligand_ratio", "AuNC_type",
    "is_pure_AuNC_or_composite", "composite_type", "carrier_or_matrix",
    "source_batch"
]

def usable_columns(rows):
    numeric = []
    for col in NUMERIC_ALL:
        if any(not math.isnan(num(r.get(col))) for r in rows):
            numeric.append(col)
    cats = []
    for col in CAT_ALL:
        if any((r.get(col) or "").strip() for r in rows):
            cats.append(col)
    return numeric, cats

def make_x(rows, numeric, cats):
    out = []
    for row in rows:
        out.append([num(row.get(c)) for c in numeric] + [(row.get(c) or "") for c in cats])
    return out

def model_pipeline(n_num, n_cat):
    num_idx = list(range(n_num))
    cat_idx = list(range(n_num, n_num + n_cat))
    prep = ColumnTransformer([
        ("num", Pipeline([("fill", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), num_idx),
        ("cat", Pipeline([("fill", SimpleImputer(strategy="most_frequent")), ("code", OneHotEncoder(handle_unknown="ignore"))]), cat_idx)
    ])
    return Pipeline([("prep", prep), ("model", Ridge(alpha=1.0))])

def fit_model(rows, target):
    labeled = [(r, num(r.get(target))) for r in rows if not math.isnan(num(r.get(target)))]
    if len(labeled) < 3:
        return None, {"target": target, "status": "not_enough_data", "label_count": len(labeled)}
    train_rows = [r for r, v in labeled]
    y = np.array([v for r, v in labeled], dtype=float)
    numeric, cats = usable_columns(train_rows)
    x = make_x(train_rows, numeric, cats)
    model = model_pipeline(len(numeric), len(cats))
    if len(y) < 6:
        cv = LeaveOneOut()
        cv_name = "LeaveOneOut"
    else:
        cv = KFold(n_splits=min(5, len(y)), shuffle=True, random_state=12)
        cv_name = f"{min(5, len(y))}-fold"
    pred = cross_val_predict(model, x, y, cv=cv)
    report = {
        "target": target,
        "status": "trained",
        "label_count": len(y),
        "cv": cv_name,
        "mae": float(mean_absolute_error(y, pred)),
        "r2": float(r2_score(y, pred)) if len(set(np.round(y, 10))) > 1 else ""
    }
    model.fit(x, y)
    return (model, numeric, cats, train_rows, y), report

def predict_with(model_pack, rows):
    model, numeric, cats, train_rows, y = model_pack
    return model.predict(make_x(rows, numeric, cats))

def normalized(values, direction):
    vals = [v for v in values if not math.isnan(v)]
    if not vals:
        return [math.nan for _ in values]
    lo, hi = min(vals), max(vals)
    if lo == hi:
        return [1.0 if not math.isnan(v) else math.nan for v in values]
    scores = []
    for v in values:
        if math.isnan(v):
            scores.append(math.nan)
        elif direction == "lower":
            scores.append((hi - v) / (hi - lo))
        else:
            scores.append((v - lo) / (hi - lo))
    return scores

def top_range(rows, fields):
    result = []
    for field in fields:
        vals = [num(r.get(field)) for r in rows]
        vals = [v for v in vals if not math.isnan(v)]
        if not vals:
            continue
        result.append({
            "parameter": field,
            "n": len(vals),
            "min": min(vals),
            "q25": percentile(vals, 0.25),
            "median": percentile(vals, 0.5),
            "q75": percentile(vals, 0.75),
            "max": max(vals)
        })
    return result

TARGETS = [
    ("Km_TMB_mM", "lower"),
    ("Km_H2O2_mM", "lower"),
    ("Vmax_TMB_M_s", "higher"),
    ("Vmax_H2O2_M_s", "higher"),
    ("absorbance_TMB_652nm", "higher"),
    ("specific_activity_U_mg", "higher")
]

STRUCTURE_FIELDS = [
    "core", "ligand", "ligand_family", "ligand_ratio",
    "diameter_TEM_nm", "diameter_DLS_nm", "diameter_sd_nm",
    "emission_peak_nm", "synthesis_temperature_C", "synthesis_time_h",
    "pH", "AuNC_type", "is_pure_AuNC_or_composite", "composite_type",
    "carrier_or_matrix", "reference_id", "DOI", "paper_title"
]

RANGE_FIELDS = [
    "diameter_TEM_nm", "diameter_DLS_nm", "diameter_sd_nm",
    "emission_peak_nm", "synthesis_temperature_C", "synthesis_time_h", "pH"
]

def literature_recommendations(rows, target, direction):
    labeled = []
    for row in rows:
        value = num(row.get(target))
        if not math.isnan(value):
            item = {k: row.get(k, "") for k in STRUCTURE_FIELDS}
            item["target"] = target
            item["actual_value"] = value
            labeled.append(item)
    labeled.sort(key=lambda r: r["actual_value"], reverse=(direction == "higher"))
    for i, row in enumerate(labeled, 1):
        row["rank"] = i
    return labeled

def main():
    rows = [r for r in read_csv(DATA_FILE) if r.get("analysis_group") == "activity"]
    candidates = read_csv(CANDIDATE_FILE)
    reports = []
    literature_rows = []
    candidate_rows = [dict(r) for r in candidates]

    for target, direction in TARGETS:
        pack, report = fit_model(rows, target)
        report["direction"] = direction
        reports.append(report)

        lit = literature_recommendations(rows, target, direction)
        literature_rows.extend(lit[:5])

        if pack and candidate_rows:
            pred = [float(x) for x in predict_with(pack, candidate_rows)]
            scores = normalized(pred, direction)
            for row, p, s in zip(candidate_rows, pred, scores):
                row[f"predicted_{target}"] = p
                row[f"{target}_score"] = s if not math.isnan(s) else ""

    for row in candidate_rows:
        scores = [num(v) for k, v in row.items() if k.endswith("_score") and not math.isnan(num(v))]
        row["activity_score"] = sum(scores) / len(scores) if scores else ""

    candidate_rows.sort(key=lambda r: num(r.get("activity_score")), reverse=True)
    for i, row in enumerate(candidate_rows, 1):
        row["activity_rank"] = i

    top_lit_for_range = []
    for target, direction in TARGETS:
        one = literature_recommendations(rows, target, direction)
        top_lit_for_range.extend(one[:3])

    write_csv(RESULTS / "high_activity_model_summary.csv", reports)
    write_csv(RESULTS / "high_activity_structure_recommendations.csv", literature_rows)
    write_csv(RESULTS / "high_activity_parameter_ranges.csv", top_range(top_lit_for_range, RANGE_FIELDS))

    if candidate_rows:
        write_csv(RESULTS / "high_activity_candidate_predictions.csv", candidate_rows)
        write_csv(RESULTS / "top_high_activity_candidates.csv", candidate_rows[:10])
    else:
        write_csv(RESULTS / "high_activity_candidate_predictions.csv", [], ["candidate_id", "message"])
        write_csv(RESULTS / "top_high_activity_candidates.csv", [], ["candidate_id", "message"])

    print("high activity structure prediction finished")

if __name__ == "__main__":
    main()
