# Data Dictionary and Quality Rules

## Source

UCI Diabetes 130-US Hospitals for Years 1999-2008. The project uses the de-identified `diabetic_data.csv` and `IDS_mapping.csv` files. Source access and limitations are documented in the README. No names, addresses, or direct identifiers are added.

## Curated encounter fields

| Field | Type | Meaning |
|---|---|---|
| `encounter_id` | integer | Dataset encounter identifier; primary key for encounter-level tables |
| `patient_key` | string | Truncated SHA-256 of the source patient number for within-dataset grouping; pseudonymous, not anonymous |
| `race` | category | Source race group, with `?` normalized to missing |
| `gender` | category | Source gender; `Unknown/Invalid` standardized to `Unknown` |
| `age` | category | Source age band |
| `admission_type_id` | integer | Source admission type lookup code |
| `discharge_disposition_id` | integer | Source discharge disposition lookup code |
| `admission_source_id` | integer | Source admission source lookup code |
| `length_of_stay` | integer | Days in hospital from `time_in_hospital` |
| `prior_admissions` | integer | Sum of source inpatient, outpatient, and emergency visit counts |
| `diagnosis_count` | integer | Source number of diagnoses recorded for encounter |
| `medication_count` | integer | Source number of medications for encounter |
| `readmitted` | category | Dataset class: `<30`, `>30`, or no readmission; standardized labels in analytics output |
| `readmission_flag` | integer | 1 for either readmission class, else 0 |
| `diag_1` | category | Primary diagnosis code from source; terminology descriptions are not inferred |

## Analytical tables

| Table/file | Grain | Purpose |
|---|---|---|
| `readmission_analytics` | One row per encounter | Dashboard and model feature source |
| `admissions` | One row per encounter | Admission, source, discharge, stay, and readmission attributes |
| `diagnoses` | One row per encounter and diagnosis position | Long-form `diag_1`, `diag_2`, and `diag_3` codes |
| `patient_summary` | One row per `patient_key` | Encounter and aggregate utilization summary |

## Validation and transformation rules

- Replace the dataset's `?` missing-value marker with a proper null; trim text and normalize column names.
- Coerce identifier, code, count, and length fields to numeric values; unparseable values become null and are validated downstream.
- Reject rows with missing encounter IDs, duplicate encounter IDs, or length of stay outside 1-365 days; write reasons to `logs/rejected_records.csv`.
- Keep the original source files in `data/raw/`; write derived files to staging, cleaned, and analytical directories. Do not manually edit analytical outputs.
- Use the hashed patient key only for analysis/grouping. It is deterministic and could be linkable; protect project files and do not treat hashing as a guarantee of anonymization.
- Model features exclude encounter IDs and patient keys. The target is the dataset-defined binary readmission class, not a guaranteed 30-day outcome.
