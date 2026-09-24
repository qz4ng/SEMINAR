# Dữ liệu mẫu cho `ra_causal` Run Viewer

> **Nguồn:** hai lần chạy **thật** của pipeline (không phải số bịa), cộng nội dung tiếng Việt viết tay.
> - **Kịch bản A** — `data/raw/dirty.csv`: 306 dòng có cài lỗi đã biết; chạy hết 9 bước, trạng thái `warning`.
> - **Kịch bản B** — cùng dữ liệu nhưng **bỏ cột `yield_unit`**: P02 không quy đổi được kg/ha → P04 gắn cờ 6.3% dòng > ngưỡng 5% → pipeline `blocked` tại P04.
>
> Trường `details` quá lớn được thay bằng `{"_trimmed": true}` để file gọn.

## Cách dùng (dành cho agent dựng UI)

Chép **nguyên văn** từng khối JSON dưới đây ra file tương ứng. Không sửa số, không thêm trường.

| Khối | Lưu thành |
|---|---|
| §1 | `src/mock/runs.json` |
| §2 | `src/mock/params.json` |
| §3 | `src/mock/variable_roles.json` |
| §4 | `src/mock/artifacts_preview.json` |
| §5 | `src/content/modules.json` |
| §6 | `src/content/error_codes.json` |
| §7 | `src/content/param_docs.json` |

### Những điều về dữ liệu mà UI phải xử lý đúng

1. **Không có tham số nào khác mặc định** trong cả hai kịch bản (`params_effective` trùng `params.<MÃ>.defaults`). Tầng 2 hiển thị "Mặc định · n tham số" cho mọi node — nhưng **vẫn phải cài** logic so sánh, vì dữ liệu thật sẽ có.
2. **Trạng thái node lấy từ `step.status`, không lấy từ severity lớn nhất của findings.** P03 có finding mức `error` (`P03.CONFLICTING_DUPLICATES`) nhưng `status` là `warning` — node màu cam, riêng chip finding đó màu đỏ.
3. **Bước bị chặn/hỏng có `n_rows_out = 0`** (kịch bản B, P04). Đây **không** phải mất 301 dòng: hiển thị `301 → —`, và phễu dòng dừng ở P03.
4. Các bước sau bước hỏng **không có trong `steps[]`** — UI tự sinh node "Chưa chạy" cho chúng từ danh sách module ở §5.
5. `rows_flagged` là số **cộng dồn** từ mọi bước trước (P09 hiện 64 dù không gắn cờ gì). **Không hiển thị** trường này như thành tích của bước; dùng "Cột cờ mới" = số tên cột bắt đầu bằng `flag__` trong `columns_added`.
6. Finding có mã kết thúc bằng `.SUMMARY` là thống kê tổng hợp, **không** phải phát hiện: không đếm, không hiện trong danh sách findings, chỉ hiện trong JSON gốc.
7. `message` do backend sinh, **có câu tiếng Anh, có câu tiếng Việt** — hiển thị nguyên văn; nghĩa tiếng Việt chuẩn lấy từ §6 (tooltip).
8. P07 kịch bản A có **7 cảnh báo `UNKNOWN_TIMING`** cho các cột dẫn xuất (`cover_crop__thr1`, `yield_t_ha__winsorized`…). Đây là nhiễu đã biết của backend — hiển thị đúng như dữ liệu, không che.

## §1. `runs.json` — báo cáo hai lần chạy

```json
{
 "A": {
  "run_id": "20260924-112145-95668ddd",
  "started_at": "2026-09-24T11:21:45.519939+00:00",
  "finished_at": "2026-09-24T11:21:45.965608+00:00",
  "duration_s": 0.441,
  "status": "warning",
  "failed_step": null,
  "config_digest": "46ec1c5a6f01",
  "schema_version": "1.0",
  "input": {
   "path": "/tmp/claude-1000/-home-doan-Seminar/cadad364-d6f6-47e3-8482-a89e748efc7d/scratchpad/ui/A.csv",
   "n_rows": 306,
   "n_cols": 31,
   "adapter": "canonical"
  },
  "steps": [
   {
    "module_id": "P01",
    "module_name": "schema_check",
    "spec_version": "1.0",
    "status": "warning",
    "started_at": "2026-09-24T11:21:45.541207790",
    "duration_s": 0.02,
    "n_rows_in": 306,
    "n_rows_out": 304,
    "n_cols_in": 31,
    "n_cols_out": 34,
    "rows_dropped": 2,
    "rows_flagged": 34,
    "columns_added": [
     "flag__p01__not_allowed__contract",
     "flag__p01__not_allowed__country",
     "flag__p01__out_of_range__yield_t_ha"
    ],
    "columns_modified": [
     "record_id",
     "grower_id",
     "field_id",
     "country",
     "year",
     "rain_longterm_mm",
     "temp_longterm_c",
     "soil_om_baseline_pct",
     "field_size_ha",
     "extension_access",
     "contract",
     "experience_yr",
     "irrigation",
     "no_till",
     "organic_fert",
     "rotation_len_yr",
     "cover_crop",
     "cover_crop_months",
     "cover_crop_type",
     "soil_om_post_pct",
     "weed_pressure",
     "season_rain_mm",
     "buyer_incentive",
     "noise_1",
     "noise_2",
     "noise_3",
     "noise_4",
     "noise_5",
     "yield_t_ha",
     "in_program",
     "yield_unit"
    ],
    "params_effective": {
     "on_error": "quarantine",
     "dtype_coercion": "permissive",
     "out_of_range": "flag",
     "unknown_columns": "warn_keep",
     "duplicate_key_action": "defer_to_p03",
     "required_id_columns": [
      "record_id"
     ]
    },
    "findings": [
     {
      "code": "P01.UNKNOWN_COLUMN",
      "severity": "warning",
      "message": "Kept unknown columns: ['yield_unit']",
      "count": 1,
      "column": null,
      "sample_ids": [],
      "details": {
       "columns": [
        "yield_unit"
       ]
      }
     },
     {
      "code": "P01.NOT_ALLOWED_CATEGORY",
      "severity": "warning",
      "message": "Not allowed categories in country",
      "count": 16,
      "column": "country",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P01.COERCE_FAILED",
      "severity": "warning",
      "message": "Coercion failed in temp_longterm_c",
      "count": 1,
      "column": "temp_longterm_c",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P01.NOT_ALLOWED_CATEGORY",
      "severity": "warning",
      "message": "Not allowed categories in contract",
      "count": 1,
      "column": "contract",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P01.OUT_OF_RANGE",
      "severity": "warning",
      "message": "Out of range in yield_t_ha",
      "count": 21,
      "column": "yield_t_ha",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P01.BAD_RECORD_ID",
      "severity": "error",
      "message": "Bad ID in record_id",
      "count": 1,
      "column": "record_id",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P01.DUPLICATE_KEY_SEEN",
      "severity": "info",
      "message": "Duplicate record_ids deferred to P03",
      "count": 6,
      "column": "record_id",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P01.SUMMARY",
      "severity": "info",
      "message": "Module summary",
      "count": 0,
      "column": null,
      "sample_ids": [],
      "details": {
       "errors_by_column": {
        "country": {
         "coerce_failed": 0,
         "out_of_range": 0,
         "not_allowed": 16
        },
        "temp_longterm_c": {
         "coerce_failed": 1,
         "out_of_range": 0,
         "not_allowed": 0
        },
        "contract": {
         "coerce_failed": 0,
         "out_of_range": 0,
         "not_allowed": 1
        },
        "yield_t_ha": {
         "coerce_failed": 0,
         "out_of_range": 21,
         "not_allowed": 0
        }
       },
       "n_quarantined": 1,
       "schema_version": "1.0"
      }
     }
    ],
    "artifacts": {
     "quarantine": "quarantine.parquet"
    },
    "context_updates": [
     "quarantined_ids"
    ]
   },
   {
    "module_id": "P02",
    "module_name": "harmonize",
    "spec_version": "1.0",
    "status": "warning",
    "started_at": "2026-09-24T11:21:45.578306675",
    "duration_s": 0.02,
    "n_rows_in": 304,
    "n_rows_out": 304,
    "n_cols_in": 34,
    "n_cols_out": 35,
    "rows_dropped": 0,
    "rows_flagged": 34,
    "columns_added": [
     "flag__p02__unmapped__contract"
    ],
    "columns_modified": [
     "record_id",
     "grower_id",
     "field_id",
     "country",
     "contract",
     "yield_t_ha",
     "yield_unit"
    ],
    "params_effective": {
     "string_normalize": {
      "trim": true,
      "lower": true,
      "strip_accents": true,
      "collapse_spaces": true
     },
     "category_mapping_mode": "explicit",
     "fuzzy_threshold": 0.9,
     "unmapped_action": {
      "default": "to_na",
      "overrides": {
       "country": "raise",
       "cover_crop": "raise"
      }
     },
     "unit_policy": "unit_column",
     "unit_column_name": "yield_unit",
     "unit_fallback": "source_declaration",
     "unit_threshold": 1000.0,
     "decimal_comma": "auto",
     "category_levels_source": "schema"
    },
    "findings": [
     {
      "code": "P02.UNMAPPED_CATEGORY",
      "severity": "warning",
      "message": "Không ánh xạ được 'invalid_cat' trong contract",
      "count": 1,
      "column": "contract",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P02.UNIT_CONVERTED",
      "severity": "info",
      "message": "Yield converted by unit_column",
      "count": 17,
      "column": null,
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P02.MIXED_UNIT_SUSPECTED",
      "severity": "warning",
      "message": "Bimodal yield distribution suggests mixed units",
      "count": 304,
      "column": null,
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P02.SUMMARY",
      "severity": "info",
      "message": "Module summary",
      "count": 0,
      "column": null,
      "sample_ids": [],
      "details": {
       "mapping_applied": [
        {
         "column": "country",
         "raw_value": "c-1",
         "mapped_value": "C1",
         "n_rows": 4
        },
        {
         "column": "country",
         "raw_value": "c1",
         "mapped_value": "C1",
         "n_rows": 123
        },
        {
         "column": "country",
         "raw_value": "c2",
         "mapped_value": "C2",
         "n_rows": 99
        },
        {
         "column": "country",
         "raw_value": "c3",
         "mapped_value": "C3",
         "n_rows": 44
        },
        {
         "column": "country",
         "raw_value": "c4",
         "mapped_value": "C4",
         "n_rows": 26
        },
        {
         "column": "country",
         "raw_value": "country 1",
         "mapped_value": "C1",
         "n_rows": 8
        }
       ],
       "unit_conversion": {
        "n_rows_converted": 17,
        "factor": 1000.0,
        "policy_used": "unit_column"
       },
       "fuzzy_suggestions": []
      }
     }
    ],
    "artifacts": {},
    "context_updates": [
     "unit_conversions"
    ]
   },
   {
    "module_id": "P03",
    "module_name": "deduplicate",
    "spec_version": "1.0",
    "status": "warning",
    "started_at": "2026-09-24T11:21:45.604355812",
    "duration_s": 0.051,
    "n_rows_in": 304,
    "n_rows_out": 301,
    "n_cols_in": 35,
    "n_cols_out": 38,
    "rows_dropped": 3,
    "rows_flagged": 39,
    "columns_added": [
     "dup_group_id",
     "flag__p03__conflict",
     "flag__p03__duplicate"
    ],
    "columns_modified": [
     "record_id",
     "grower_id",
     "field_id",
     "country",
     "year",
     "rain_longterm_mm",
     "temp_longterm_c",
     "soil_om_baseline_pct",
     "field_size_ha",
     "extension_access",
     "contract",
     "experience_yr",
     "irrigation",
     "no_till",
     "organic_fert",
     "rotation_len_yr",
     "cover_crop",
     "cover_crop_months",
     "cover_crop_type",
     "soil_om_post_pct",
     "weed_pressure",
     "season_rain_mm",
     "buyer_incentive",
     "noise_1",
     "noise_2",
     "noise_3",
     "noise_4",
     "noise_5",
     "yield_t_ha",
     "in_program",
     "yield_unit",
     "flag__p01__not_allowed__country",
     "flag__p01__not_allowed__contract",
     "flag__p01__out_of_range__yield_t_ha",
     "flag__p02__unmapped__contract"
    ],
    "params_effective": {
     "key": [
      "grower_id",
      "field_id",
      "year"
     ],
     "resolve": "keep_most_complete",
     "timestamp_column": null,
     "conflict_action": "review_list",
     "critical_columns": [
      "cover_crop",
      "yield_t_ha",
      "country",
      "year"
     ],
     "numeric_tolerance": 1e-08,
     "aggregate_rules": {
      "numeric": "mean",
      "categorical": "mode",
      "boolean": "max"
     }
    },
    "findings": [
     {
      "code": "P03.EXACT_DUPLICATES",
      "severity": "info",
      "message": "Exact duplicates found",
      "count": 1,
      "column": null,
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P03.PARTIAL_DUPLICATES",
      "severity": "warning",
      "message": "Partial duplicates found",
      "count": 2,
      "column": null,
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P03.CONFLICTING_DUPLICATES",
      "severity": "error",
      "message": "Conflicting duplicates found",
      "count": 3,
      "column": null,
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P03.SUMMARY",
      "severity": "info",
      "message": "Module summary",
      "count": 0,
      "column": null,
      "sample_ids": [],
      "details": {
       "groups_by_type": {
        "exact": 1,
        "partial": 2,
        "conflict": 3
       },
       "rows_removed": 3,
       "conflict_columns_frequency": {
        "cover_crop": 2,
        "yield_t_ha": 1
       }
      }
     }
    ],
    "artifacts": {
     "review_list": "review_list.parquet"
    },
    "context_updates": [
     "duplicate_groups"
    ]
   },
   {
    "module_id": "P04",
    "module_name": "outliers",
    "spec_version": "1.0",
    "status": "warning",
    "started_at": "2026-09-24T11:21:45.666170359",
    "duration_s": 0.033,
    "n_rows_in": 301,
    "n_rows_out": 301,
    "n_cols_in": 38,
    "n_cols_out": 45,
    "rows_dropped": 0,
    "rows_flagged": 39,
    "columns_added": [
     "flag__p04__any",
     "flag__p04__outlier__experience_yr",
     "flag__p04__outlier__field_size_ha",
     "flag__p04__outlier__soil_om_baseline_pct",
     "flag__p04__outlier__yield_t_ha",
     "flag__p04__suspected_unit_error__yield_t_ha",
     "yield_t_ha__winsorized"
    ],
    "columns_modified": [],
    "params_effective": {
     "columns": [
      "yield_t_ha",
      "field_size_ha",
      "soil_om_baseline_pct",
      "experience_yr"
     ],
     "method": "robust_z",
     "method_by_column": {
      "yield_t_ha": "domain_range",
      "field_size_ha": "domain_range"
     },
     "iqr_k": 3.0,
     "robust_z_threshold": 3.5,
     "percentile_bounds": [
      0.005,
      0.995
     ],
     "group_by": [
      "country"
     ],
     "min_group_size": 30,
     "action": "flag_only",
     "parallel_actions": [
      "winsorize"
     ],
     "winsorize_at": "bound",
     "max_flag_rate": 0.05,
     "unit_error_detection": true,
     "unit_error_factors": [
      1000.0,
      100.0,
      10.0,
      0.1,
      0.01,
      0.001
     ]
    },
    "findings": [
     {
      "code": "P04.OUTLIERS_FLAGGED",
      "severity": "info",
      "message": "Outliers in yield_t_ha",
      "count": 3,
      "column": "yield_t_ha",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P04.SUSPECTED_UNIT_ERROR",
      "severity": "warning",
      "message": "Unit error suspected in yield_t_ha",
      "count": 6,
      "column": "yield_t_ha",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P04.SMALL_GROUP",
      "severity": "info",
      "message": "Group C4 size 25 < 30, using global bounds",
      "count": 25,
      "column": "soil_om_baseline_pct",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P04.SMALL_GROUP",
      "severity": "info",
      "message": "Group C4 size 22 < 30, using global bounds",
      "count": 22,
      "column": "experience_yr",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P04.SUMMARY",
      "severity": "info",
      "message": "Module summary",
      "count": 0,
      "column": null,
      "sample_ids": [],
      "details": {
       "_trimmed": true,
       "_note": "details lớn, rút gọn trong mock"
      }
     }
    ],
    "artifacts": {},
    "context_updates": []
   },
   {
    "module_id": "P05",
    "module_name": "treatment_define",
    "spec_version": "1.0",
    "status": "ok",
    "started_at": "2026-09-24T11:21:45.707859755",
    "duration_s": 0.01,
    "n_rows_in": 301,
    "n_rows_out": 301,
    "n_cols_in": 45,
    "n_cols_out": 50,
    "rows_dropped": 0,
    "rows_flagged": 39,
    "columns_added": [
     "cover_crop__raw",
     "cover_crop__thr1",
     "cover_crop__thr2",
     "cover_crop__thr3",
     "cover_crop_type__grouped"
    ],
    "columns_modified": [
     "cover_crop"
    ],
    "params_effective": {
     "mode": "binary_threshold",
     "source_column": "cover_crop_months",
     "threshold_months": 2.0,
     "threshold_sensitivity": [
      1.0,
      2.0,
      3.0
     ],
     "partial_action": "to_na",
     "type_grouping": "group",
     "min_cell": 30,
     "write_treatment_column": true
    },
    "findings": [
     {
      "code": "P05.THRESHOLD_SENSITIVITY",
      "severity": "info",
      "message": "Max 28 samples change status under sensitivity thresholds",
      "count": 28,
      "column": null,
      "sample_ids": [],
      "details": {}
     }
    ],
    "artifacts": {},
    "context_updates": [
     "treatment_definition",
     "treatment_column"
    ]
   },
   {
    "module_id": "P07",
    "module_name": "time_order",
    "spec_version": "1.0",
    "status": "warning",
    "started_at": "2026-09-24T11:21:45.727387190",
    "duration_s": 0.0,
    "n_rows_in": 301,
    "n_rows_out": 301,
    "n_cols_in": 50,
    "n_cols_out": 50,
    "rows_dropped": 0,
    "rows_flagged": 0,
    "columns_added": [],
    "columns_modified": [],
    "params_effective": {
     "time_source": "schema",
     "unknown_action": "exclude",
     "strict": true,
     "allow_post_precision_vars": false,
     "allow_post_as_secondary_outcome": true,
     "diagnostics_on_post_vars": true
    },
    "findings": [
     {
      "code": "P07.BLOCKED_POST_TREATMENT",
      "severity": "info",
      "message": "Blocked post var soil_om_post_pct",
      "count": 1,
      "column": "soil_om_post_pct",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P07.BLOCKED_POST_TREATMENT",
      "severity": "info",
      "message": "Blocked post var weed_pressure",
      "count": 1,
      "column": "weed_pressure",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P07.BLOCKED_POST_TREATMENT",
      "severity": "info",
      "message": "Blocked post var season_rain_mm",
      "count": 1,
      "column": "season_rain_mm",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P07.SECONDARY_OUTCOME_ALLOWED",
      "severity": "info",
      "message": "Allowed post-treatment outcome: yield_t_ha",
      "count": 1,
      "column": "yield_t_ha",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P07.BLOCKED_POST_TREATMENT",
      "severity": "info",
      "message": "Blocked post var in_program",
      "count": 1,
      "column": "in_program",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P07.UNKNOWN_TIMING",
      "severity": "warning",
      "message": "Cột 'yield_unit' không khai trong schema, coi như không rõ thời điểm đo",
      "count": 1,
      "column": "yield_unit",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P07.UNKNOWN_TIMING",
      "severity": "warning",
      "message": "Cột 'yield_t_ha__winsorized' không khai trong schema, coi như không rõ thời điểm đo",
      "count": 1,
      "column": "yield_t_ha__winsorized",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P07.UNKNOWN_TIMING",
      "severity": "warning",
      "message": "Cột 'cover_crop__raw' không khai trong schema, coi như không rõ thời điểm đo",
      "count": 1,
      "column": "cover_crop__raw",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P07.UNKNOWN_TIMING",
      "severity": "warning",
      "message": "Cột 'cover_crop__thr1' không khai trong schema, coi như không rõ thời điểm đo",
      "count": 1,
      "column": "cover_crop__thr1",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P07.UNKNOWN_TIMING",
      "severity": "warning",
      "message": "Cột 'cover_crop__thr2' không khai trong schema, coi như không rõ thời điểm đo",
      "count": 1,
      "column": "cover_crop__thr2",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P07.UNKNOWN_TIMING",
      "severity": "warning",
      "message": "Cột 'cover_crop__thr3' không khai trong schema, coi như không rõ thời điểm đo",
      "count": 1,
      "column": "cover_crop__thr3",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P07.UNKNOWN_TIMING",
      "severity": "warning",
      "message": "Cột 'cover_crop_type__grouped' không khai trong schema, coi như không rõ thời điểm đo",
      "count": 1,
      "column": "cover_crop_type__grouped",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P07.SUMMARY",
      "severity": "info",
      "message": "Module summary",
      "count": 0,
      "column": null,
      "sample_ids": [],
      "details": {
       "_trimmed": true,
       "_note": "details lớn, rút gọn trong mock"
      }
     }
    ],
    "artifacts": {},
    "context_updates": [
     "blocked_columns",
     "eligible_columns"
    ]
   },
   {
    "module_id": "P08",
    "module_name": "variable_roles",
    "spec_version": "1.0",
    "status": "warning",
    "started_at": "2026-09-24T11:21:45.735210419",
    "duration_s": 0.003,
    "n_rows_in": 301,
    "n_rows_out": 301,
    "n_cols_in": 50,
    "n_cols_out": 50,
    "rows_dropped": 0,
    "rows_flagged": 39,
    "columns_added": [],
    "columns_modified": [],
    "params_effective": {
     "source": "schema_roles",
     "allow_data_driven": false,
     "manual_list": [],
     "include_roles": [
      "confounder"
     ],
     "include_precision_vars": true,
     "exclude_roles": [
      "mediator",
      "collider",
      "instrument",
      "noise",
      "outcome",
      "treatment",
      "treatment_version",
      "id"
     ],
     "ambiguous_action": "both",
     "basis": {
      "continuous": "quadratic",
      "spline_df": 4
     },
     "interactions": [
      [
       "country",
       "*"
      ]
     ],
     "rare_level_action": "group",
     "rare_level_threshold": 0.01,
     "min_variation": 1e-12
    },
    "findings": [
     {
      "code": "P08.AMBIGUOUS_ROLE",
      "severity": "warning",
      "message": "Created variants for ['no_till', 'organic_fert', 'rotation_len_yr']",
      "count": 3,
      "column": null,
      "sample_ids": [],
      "details": {
       "ambiguous": [
        "no_till",
        "organic_fert",
        "rotation_len_yr"
       ]
      }
     },
     {
      "code": "P08.ADJUSTMENT_SET_BUILT",
      "severity": "info",
      "message": "Built L with 13 columns",
      "count": 13,
      "column": null,
      "sample_ids": [],
      "details": {
       "columns": [
        "contract",
        "country",
        "experience_yr",
        "extension_access",
        "field_size_ha",
        "irrigation",
        "no_till",
        "organic_fert",
        "rain_longterm_mm",
        "rotation_len_yr",
        "soil_om_baseline_pct",
        "temp_longterm_c",
        "year"
       ]
      }
     },
     {
      "code": "P08.SUMMARY",
      "severity": "info",
      "message": "Module summary",
      "count": 0,
      "column": null,
      "sample_ids": [],
      "details": {
       "ps_basis_spec": {
        "basis": {
         "continuous": "quadratic",
         "spline_df": 4
        },
        "interactions": [
         [
          "country",
          "*"
         ]
        ]
       }
      }
     }
    ],
    "artifacts": {
     "data_dictionary": "data_dictionary.csv"
    },
    "context_updates": [
     "adjustment_set",
     "adjustment_set_variants",
     "ps_basis_spec"
    ]
   },
   {
    "module_id": "P06",
    "module_name": "missingness",
    "spec_version": "1.0",
    "status": "ok",
    "started_at": "2026-09-24T11:21:45.748743534",
    "duration_s": 0.137,
    "n_rows_in": 301,
    "n_rows_out": 301,
    "n_cols_in": 50,
    "n_cols_out": 55,
    "rows_dropped": 0,
    "rows_flagged": 64,
    "columns_added": [
     "c_outcome_observed",
     "flag__p06__imputed__contract",
     "flag__p06__imputed__experience_yr",
     "flag__p06__imputed__irrigation",
     "flag__p06__missing_any_L"
    ],
    "columns_modified": [
     "contract",
     "experience_yr",
     "irrigation"
    ],
    "params_effective": {
     "scope": "adjustment_set_plus_ay",
     "outcome_missing": "ipcw_flag",
     "covariate_missing": "median_indicator",
     "impute_group_by": [
      "country"
     ],
     "min_group_size": 30,
     "keep_indicator": true,
     "max_missing_col": 0.4,
     "mechanism_check": [
      "describe",
      "regress"
     ],
     "diff_warn_threshold": 0.05
    },
    "findings": [
     {
      "code": "P06.SMALL_GROUP",
      "severity": "info",
      "message": "Group C4 size 25 < 30, using global impute for contract",
      "count": 25,
      "column": "contract",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P06.IMPUTED",
      "severity": "info",
      "message": "Imputed contract",
      "count": 1,
      "column": "contract",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P06.SMALL_GROUP",
      "severity": "info",
      "message": "Group C4 size 22 < 30, using global impute for experience_yr",
      "count": 22,
      "column": "experience_yr",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P06.IMPUTED",
      "severity": "info",
      "message": "Imputed experience_yr",
      "count": 30,
      "column": "experience_yr",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P06.SMALL_GROUP",
      "severity": "info",
      "message": "Group C4 size 25 < 30, using global impute for irrigation",
      "count": 25,
      "column": "irrigation",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P06.IMPUTED",
      "severity": "info",
      "message": "Imputed irrigation",
      "count": 1,
      "column": "irrigation",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P06.OUTCOME_MISSING_RATE",
      "severity": "info",
      "message": "Outcome missing rate",
      "count": 15,
      "column": "yield_t_ha",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P06.MISSING_SUMMARY",
      "severity": "info",
      "message": "Missing summary",
      "count": 0,
      "column": null,
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P06.MECHANISM_REGRESS",
      "severity": "info",
      "message": "Top missingness predictors: ['country_C2', 'temp_longterm_c', 'extension_access', 'country_C3', 'field_size_ha', 'country_C4', 'experience_yr', 'no_till', 'rain_longterm_mm', 'contract_informal']",
      "count": 0,
      "column": null,
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P06.SUMMARY",
      "severity": "info",
      "message": "Module summary",
      "count": 0,
      "column": null,
      "sample_ids": [],
      "details": {
       "_trimmed": true,
       "_note": "details lớn, rút gọn trong mock"
      }
     }
    ],
    "artifacts": {},
    "context_updates": [
     "adjustment_set",
     "outcome_observed_column"
    ]
   },
   {
    "module_id": "P09",
    "module_name": "clusters",
    "spec_version": "1.0",
    "status": "ok",
    "started_at": "2026-09-24T11:21:45.899371862",
    "duration_s": 0.051,
    "n_rows_in": 301,
    "n_rows_out": 301,
    "n_cols_in": 55,
    "n_cols_out": 57,
    "rows_dropped": 0,
    "rows_flagged": 64,
    "columns_added": [
     "cluster_id",
     "fold_id"
    ],
    "columns_modified": [],
    "params_effective": {
     "cluster_key": [
      "grower_id"
     ],
     "fold_strategy": "group_stratified",
     "n_folds": 5,
     "seed": 20260921,
     "year_handling": "fixed_effect",
     "large_cluster_warn": 0.05,
     "compute_icc": true
    },
    "findings": [
     {
      "code": "P09.ICC_ESTIMATE",
      "severity": "info",
      "message": "ICC = 0.660",
      "count": 0,
      "column": null,
      "sample_ids": [],
      "details": {
       "icc": 0.6602974844031659
      }
     },
     {
      "code": "P09.CLUSTER_SUMMARY",
      "severity": "info",
      "message": "Clusters: 155",
      "count": 155,
      "column": null,
      "sample_ids": [],
      "details": {}
     }
    ],
    "artifacts": {},
    "context_updates": [
     "cluster_column",
     "fold_column",
     "year_handling"
    ]
   }
  ],
  "context_final": {
   "adjustment_set": [
    "contract",
    "country",
    "experience_yr",
    "extension_access",
    "field_size_ha",
    "irrigation",
    "no_till",
    "organic_fert",
    "rain_longterm_mm",
    "rotation_len_yr",
    "soil_om_baseline_pct",
    "temp_longterm_c",
    "year"
   ],
   "treatment_definition": {
    "source": "cover_crop_months",
    "rule": ">= 2.0",
    "partial_action": "to_na",
    "type_grouping": "group"
   },
   "cluster_column": "cluster_id",
   "fold_column": "fold_id",
   "outcome_observed_column": "c_outcome_observed"
  },
  "outputs": {
   "analysis_ready": "/tmp/claude-1000/-home-doan-Seminar/cadad364-d6f6-47e3-8482-a89e748efc7d/scratchpad/ui/out_A/processed/20260924-112145-95668ddd/analysis_ready.parquet",
   "artifacts": {}
  }
 },
 "B": {
  "run_id": "20260924-112147-4e42bf71",
  "started_at": "2026-09-24T11:21:47.382466+00:00",
  "finished_at": "2026-09-24T11:21:47.553155+00:00",
  "duration_s": 0.171,
  "status": "blocked",
  "failed_step": "P04",
  "config_digest": "46ec1c5a6f01",
  "schema_version": "1.0",
  "input": {
   "path": "/tmp/claude-1000/-home-doan-Seminar/cadad364-d6f6-47e3-8482-a89e748efc7d/scratchpad/ui/B.csv",
   "n_rows": 306,
   "n_cols": 30,
   "adapter": "canonical"
  },
  "steps": [
   {
    "module_id": "P01",
    "module_name": "schema_check",
    "spec_version": "1.0",
    "status": "warning",
    "started_at": "2026-09-24T11:21:47.400768042",
    "duration_s": 0.024,
    "n_rows_in": 306,
    "n_rows_out": 304,
    "n_cols_in": 30,
    "n_cols_out": 33,
    "rows_dropped": 2,
    "rows_flagged": 34,
    "columns_added": [
     "flag__p01__not_allowed__contract",
     "flag__p01__not_allowed__country",
     "flag__p01__out_of_range__yield_t_ha"
    ],
    "columns_modified": [
     "record_id",
     "grower_id",
     "field_id",
     "country",
     "year",
     "rain_longterm_mm",
     "temp_longterm_c",
     "soil_om_baseline_pct",
     "field_size_ha",
     "extension_access",
     "contract",
     "experience_yr",
     "irrigation",
     "no_till",
     "organic_fert",
     "rotation_len_yr",
     "cover_crop",
     "cover_crop_months",
     "cover_crop_type",
     "soil_om_post_pct",
     "weed_pressure",
     "season_rain_mm",
     "buyer_incentive",
     "noise_1",
     "noise_2",
     "noise_3",
     "noise_4",
     "noise_5",
     "yield_t_ha",
     "in_program"
    ],
    "params_effective": {
     "on_error": "quarantine",
     "dtype_coercion": "permissive",
     "out_of_range": "flag",
     "unknown_columns": "warn_keep",
     "duplicate_key_action": "defer_to_p03",
     "required_id_columns": [
      "record_id"
     ]
    },
    "findings": [
     {
      "code": "P01.NOT_ALLOWED_CATEGORY",
      "severity": "warning",
      "message": "Not allowed categories in country",
      "count": 16,
      "column": "country",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P01.COERCE_FAILED",
      "severity": "warning",
      "message": "Coercion failed in temp_longterm_c",
      "count": 1,
      "column": "temp_longterm_c",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P01.NOT_ALLOWED_CATEGORY",
      "severity": "warning",
      "message": "Not allowed categories in contract",
      "count": 1,
      "column": "contract",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P01.OUT_OF_RANGE",
      "severity": "warning",
      "message": "Out of range in yield_t_ha",
      "count": 21,
      "column": "yield_t_ha",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P01.BAD_RECORD_ID",
      "severity": "error",
      "message": "Bad ID in record_id",
      "count": 1,
      "column": "record_id",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P01.DUPLICATE_KEY_SEEN",
      "severity": "info",
      "message": "Duplicate record_ids deferred to P03",
      "count": 6,
      "column": "record_id",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P01.SUMMARY",
      "severity": "info",
      "message": "Module summary",
      "count": 0,
      "column": null,
      "sample_ids": [],
      "details": {
       "errors_by_column": {
        "country": {
         "coerce_failed": 0,
         "out_of_range": 0,
         "not_allowed": 16
        },
        "temp_longterm_c": {
         "coerce_failed": 1,
         "out_of_range": 0,
         "not_allowed": 0
        },
        "contract": {
         "coerce_failed": 0,
         "out_of_range": 0,
         "not_allowed": 1
        },
        "yield_t_ha": {
         "coerce_failed": 0,
         "out_of_range": 21,
         "not_allowed": 0
        }
       },
       "n_quarantined": 1,
       "schema_version": "1.0"
      }
     }
    ],
    "artifacts": {
     "quarantine": "quarantine.parquet"
    },
    "context_updates": [
     "quarantined_ids"
    ]
   },
   {
    "module_id": "P02",
    "module_name": "harmonize",
    "spec_version": "1.0",
    "status": "warning",
    "started_at": "2026-09-24T11:21:47.443436146",
    "duration_s": 0.017,
    "n_rows_in": 304,
    "n_rows_out": 304,
    "n_cols_in": 33,
    "n_cols_out": 34,
    "rows_dropped": 0,
    "rows_flagged": 34,
    "columns_added": [
     "flag__p02__unmapped__contract"
    ],
    "columns_modified": [
     "record_id",
     "grower_id",
     "field_id",
     "country",
     "contract"
    ],
    "params_effective": {
     "string_normalize": {
      "trim": true,
      "lower": true,
      "strip_accents": true,
      "collapse_spaces": true
     },
     "category_mapping_mode": "explicit",
     "fuzzy_threshold": 0.9,
     "unmapped_action": {
      "default": "to_na",
      "overrides": {
       "country": "raise",
       "cover_crop": "raise"
      }
     },
     "unit_policy": "unit_column",
     "unit_column_name": "yield_unit",
     "unit_fallback": "source_declaration",
     "unit_threshold": 1000.0,
     "decimal_comma": "auto",
     "category_levels_source": "schema"
    },
    "findings": [
     {
      "code": "P02.UNMAPPED_CATEGORY",
      "severity": "warning",
      "message": "Không ánh xạ được 'invalid_cat' trong contract",
      "count": 1,
      "column": "contract",
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P02.MIXED_UNIT_SUSPECTED",
      "severity": "warning",
      "message": "Bimodal yield distribution suggests mixed units",
      "count": 304,
      "column": null,
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P02.SUMMARY",
      "severity": "info",
      "message": "Module summary",
      "count": 0,
      "column": null,
      "sample_ids": [],
      "details": {
       "mapping_applied": [
        {
         "column": "country",
         "raw_value": "c-1",
         "mapped_value": "C1",
         "n_rows": 4
        },
        {
         "column": "country",
         "raw_value": "c1",
         "mapped_value": "C1",
         "n_rows": 123
        },
        {
         "column": "country",
         "raw_value": "c2",
         "mapped_value": "C2",
         "n_rows": 99
        },
        {
         "column": "country",
         "raw_value": "c3",
         "mapped_value": "C3",
         "n_rows": 44
        },
        {
         "column": "country",
         "raw_value": "c4",
         "mapped_value": "C4",
         "n_rows": 26
        },
        {
         "column": "country",
         "raw_value": "country 1",
         "mapped_value": "C1",
         "n_rows": 8
        }
       ],
       "unit_conversion": {
        "n_rows_converted": 0,
        "factor": 1.0,
        "policy_used": "none"
       },
       "fuzzy_suggestions": []
      }
     }
    ],
    "artifacts": {},
    "context_updates": [
     "unit_conversions"
    ]
   },
   {
    "module_id": "P03",
    "module_name": "deduplicate",
    "spec_version": "1.0",
    "status": "warning",
    "started_at": "2026-09-24T11:21:47.465290785",
    "duration_s": 0.052,
    "n_rows_in": 304,
    "n_rows_out": 301,
    "n_cols_in": 34,
    "n_cols_out": 37,
    "rows_dropped": 3,
    "rows_flagged": 39,
    "columns_added": [
     "dup_group_id",
     "flag__p03__conflict",
     "flag__p03__duplicate"
    ],
    "columns_modified": [
     "record_id",
     "grower_id",
     "field_id",
     "country",
     "year",
     "rain_longterm_mm",
     "temp_longterm_c",
     "soil_om_baseline_pct",
     "field_size_ha",
     "extension_access",
     "contract",
     "experience_yr",
     "irrigation",
     "no_till",
     "organic_fert",
     "rotation_len_yr",
     "cover_crop",
     "cover_crop_months",
     "cover_crop_type",
     "soil_om_post_pct",
     "weed_pressure",
     "season_rain_mm",
     "buyer_incentive",
     "noise_1",
     "noise_2",
     "noise_3",
     "noise_4",
     "noise_5",
     "yield_t_ha",
     "in_program",
     "flag__p01__not_allowed__country",
     "flag__p01__not_allowed__contract",
     "flag__p01__out_of_range__yield_t_ha",
     "flag__p02__unmapped__contract"
    ],
    "params_effective": {
     "key": [
      "grower_id",
      "field_id",
      "year"
     ],
     "resolve": "keep_most_complete",
     "timestamp_column": null,
     "conflict_action": "review_list",
     "critical_columns": [
      "cover_crop",
      "yield_t_ha",
      "country",
      "year"
     ],
     "numeric_tolerance": 1e-08,
     "aggregate_rules": {
      "numeric": "mean",
      "categorical": "mode",
      "boolean": "max"
     }
    },
    "findings": [
     {
      "code": "P03.EXACT_DUPLICATES",
      "severity": "info",
      "message": "Exact duplicates found",
      "count": 1,
      "column": null,
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P03.PARTIAL_DUPLICATES",
      "severity": "warning",
      "message": "Partial duplicates found",
      "count": 2,
      "column": null,
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P03.CONFLICTING_DUPLICATES",
      "severity": "error",
      "message": "Conflicting duplicates found",
      "count": 3,
      "column": null,
      "sample_ids": [],
      "details": {}
     },
     {
      "code": "P03.SUMMARY",
      "severity": "info",
      "message": "Module summary",
      "count": 0,
      "column": null,
      "sample_ids": [],
      "details": {
       "groups_by_type": {
        "exact": 1,
        "partial": 2,
        "conflict": 3
       },
       "rows_removed": 3,
       "conflict_columns_frequency": {
        "cover_crop": 2,
        "yield_t_ha": 1
       }
      }
     }
    ],
    "artifacts": {
     "review_list": "review_list.parquet"
    },
    "context_updates": [
     "duplicate_groups"
    ]
   },
   {
    "module_id": "P04",
    "module_name": "outliers",
    "spec_version": "1.0",
    "status": "blocked",
    "started_at": "2026-09-24T11:21:47.527680+00:00",
    "duration_s": 0.025,
    "n_rows_in": 301,
    "n_rows_out": 0,
    "n_cols_in": 37,
    "n_cols_out": 0,
    "rows_dropped": 0,
    "rows_flagged": 0,
    "columns_added": [],
    "columns_modified": [],
    "params_effective": {
     "columns": [
      "yield_t_ha",
      "field_size_ha",
      "soil_om_baseline_pct",
      "experience_yr"
     ],
     "method": "robust_z",
     "method_by_column": {
      "yield_t_ha": "domain_range",
      "field_size_ha": "domain_range"
     },
     "iqr_k": 3.0,
     "robust_z_threshold": 3.5,
     "percentile_bounds": [
      0.005,
      0.995
     ],
     "group_by": [
      "country"
     ],
     "min_group_size": 30,
     "action": "flag_only",
     "parallel_actions": [
      "winsorize"
     ],
     "winsorize_at": "bound",
     "max_flag_rate": 0.05,
     "unit_error_detection": true,
     "unit_error_factors": [
      1000.0,
      100.0,
      10.0,
      0.1,
      0.01,
      0.001
     ]
    },
    "findings": [
     {
      "code": "P04.MAX_FLAG_RATE_EXCEEDED",
      "severity": "blocking",
      "message": "Flag rate 6.3% exceeds 5.0%. Check unit conversions.",
      "count": 0,
      "column": null,
      "sample_ids": [],
      "details": {
       "rate": 0.06312292358803986,
       "limit": 0.05
      }
     }
    ],
    "artifacts": {},
    "context_updates": []
   }
  ],
  "context_final": {
   "adjustment_set": [],
   "treatment_definition": {},
   "cluster_column": null,
   "fold_column": null,
   "outcome_observed_column": null
  },
  "outputs": {
   "analysis_ready": "/tmp/claude-1000/-home-doan-Seminar/cadad364-d6f6-47e3-8482-a89e748efc7d/scratchpad/ui/out_B/processed/20260924-112147-4e42bf71/analysis_ready.parquet",
   "artifacts": {}
  }
 }
}
```

## §2. `params.json` — mặc định và giá trị cho phép của từng module

`defaults`: giá trị mặc định. `allowed`: danh sách giá trị hợp lệ (enum) hoặc kiểu dữ liệu; tham số lồng nhau có dạng object.

```json
{
 "P01": {
  "defaults": {
   "on_error": "quarantine",
   "dtype_coercion": "permissive",
   "out_of_range": "flag",
   "unknown_columns": "warn_keep",
   "duplicate_key_action": "defer_to_p03",
   "required_id_columns": [
    "record_id"
   ]
  },
  "allowed": {
   "on_error": [
    "quarantine",
    "raise",
    "flag"
   ],
   "dtype_coercion": [
    "strict",
    "permissive"
   ],
   "out_of_range": [
    "to_na",
    "flag",
    "clip",
    "raise"
   ],
   "unknown_columns": [
    "warn_keep",
    "drop",
    "raise"
   ],
   "duplicate_key_action": [
    "defer_to_p03",
    "raise"
   ],
   "required_id_columns": "array"
  }
 },
 "P02": {
  "defaults": {
   "string_normalize": {
    "trim": true,
    "lower": true,
    "strip_accents": true,
    "collapse_spaces": true
   },
   "category_mapping_mode": "explicit",
   "fuzzy_threshold": 0.9,
   "unmapped_action": {
    "default": "to_na",
    "overrides": {
     "country": "raise",
     "cover_crop": "raise"
    }
   },
   "unit_policy": "unit_column",
   "unit_column_name": "yield_unit",
   "unit_fallback": "source_declaration",
   "unit_threshold": 1000.0,
   "decimal_comma": "auto",
   "category_levels_source": "schema"
  },
  "allowed": {
   "string_normalize": {
    "trim": "boolean",
    "lower": "boolean",
    "strip_accents": "boolean",
    "collapse_spaces": "boolean"
   },
   "category_mapping_mode": [
    "explicit",
    "fuzzy_suggest",
    "fuzzy_auto"
   ],
   "fuzzy_threshold": "number",
   "unmapped_action": {
    "default": [
     "to_na",
     "keep_raw",
     "raise"
    ],
    "overrides": "object"
   },
   "unit_policy": [
    "unit_column",
    "source_declaration",
    "threshold_inference",
    "none"
   ],
   "unit_column_name": "string",
   "unit_fallback": [
    "source_declaration",
    "none",
    "raise"
   ],
   "unit_threshold": "number",
   "decimal_comma": [
    "auto",
    true,
    false
   ],
   "category_levels_source": [
    "schema",
    "data"
   ]
  }
 },
 "P03": {
  "defaults": {
   "key": [
    "grower_id",
    "field_id",
    "year"
   ],
   "resolve": "keep_most_complete",
   "timestamp_column": null,
   "conflict_action": "review_list",
   "critical_columns": [
    "cover_crop",
    "yield_t_ha",
    "country",
    "year"
   ],
   "numeric_tolerance": 1e-08,
   "aggregate_rules": {
    "numeric": "mean",
    "categorical": "mode",
    "boolean": "max"
   }
  },
  "allowed": {
   "key": "array",
   "resolve": [
    "keep_most_complete",
    "keep_first",
    "keep_last",
    "aggregate",
    "flag_only"
   ],
   "conflict_action": [
    "review_list",
    "drop_group",
    "resolve"
   ],
   "critical_columns": "array",
   "numeric_tolerance": "number",
   "aggregate_rules": "object"
  }
 },
 "P04": {
  "defaults": {
   "columns": [
    "yield_t_ha",
    "field_size_ha",
    "soil_om_baseline_pct",
    "experience_yr"
   ],
   "method": "robust_z",
   "method_by_column": {
    "yield_t_ha": "domain_range",
    "field_size_ha": "domain_range"
   },
   "iqr_k": 3.0,
   "robust_z_threshold": 3.5,
   "percentile_bounds": [
    0.005,
    0.995
   ],
   "group_by": [
    "country"
   ],
   "min_group_size": 30,
   "action": "flag_only",
   "parallel_actions": [
    "winsorize"
   ],
   "winsorize_at": "bound",
   "max_flag_rate": 0.05,
   "unit_error_detection": true,
   "unit_error_factors": [
    1000.0,
    100.0,
    10.0,
    0.1,
    0.01,
    0.001
   ]
  },
  "allowed": {
   "columns": "array",
   "method": [
    "domain_range",
    "iqr",
    "robust_z",
    "percentile"
   ],
   "method_by_column": "object",
   "iqr_k": "number",
   "robust_z_threshold": "number",
   "percentile_bounds": "array",
   "group_by": "array",
   "min_group_size": "integer",
   "action": [
    "flag_only",
    "winsorize",
    "to_na",
    "drop_row",
    "log_transform",
    "keep_as_feature"
   ],
   "parallel_actions": {
    "array_of": [
     "winsorize",
     "log_transform"
    ]
   },
   "winsorize_at": [
    "bound",
    "percentile"
   ],
   "max_flag_rate": "number",
   "unit_error_detection": "boolean",
   "unit_error_factors": "array"
  }
 },
 "P05": {
  "defaults": {
   "mode": "binary_threshold",
   "source_column": "cover_crop_months",
   "threshold_months": 2.0,
   "threshold_sensitivity": [
    1.0,
    2.0,
    3.0
   ],
   "partial_action": "to_na",
   "type_grouping": "group",
   "min_cell": 30,
   "write_treatment_column": true
  },
  "allowed": {
   "mode": [
    "binary_threshold",
    "multi_level",
    "per_version",
    "continuous"
   ],
   "source_column": "string",
   "threshold_months": "number",
   "threshold_sensitivity": "array",
   "partial_action": [
    "to_na",
    "treated",
    "control",
    "own_level"
   ],
   "type_grouping": [
    "group",
    "all",
    "keep"
   ],
   "min_cell": "integer",
   "write_treatment_column": "boolean"
  }
 },
 "P06": {
  "defaults": {
   "scope": "adjustment_set_plus_ay",
   "outcome_missing": "ipcw_flag",
   "covariate_missing": "median_indicator",
   "impute_group_by": [
    "country"
   ],
   "min_group_size": 30,
   "keep_indicator": true,
   "max_missing_col": 0.4,
   "mechanism_check": [
    "describe",
    "regress"
   ],
   "diff_warn_threshold": 0.05
  },
  "allowed": {
   "scope": [
    "adjustment_set_plus_ay",
    "all_columns"
   ],
   "outcome_missing": [
    "ipcw_flag",
    "complete_case",
    "both"
   ],
   "covariate_missing": [
    "median_indicator",
    "drop_row",
    "category_missing"
   ],
   "impute_group_by": "array",
   "min_group_size": "integer",
   "keep_indicator": "boolean",
   "max_missing_col": "number",
   "mechanism_check": "array",
   "diff_warn_threshold": "number"
  }
 },
 "P07": {
  "defaults": {
   "time_source": "schema",
   "unknown_action": "exclude",
   "strict": true,
   "allow_post_precision_vars": false,
   "allow_post_as_secondary_outcome": true,
   "diagnostics_on_post_vars": true
  },
  "allowed": {
   "time_source": [
    "schema",
    "name_suffix",
    "both"
   ],
   "unknown_action": [
    "exclude",
    "include",
    "raise"
   ],
   "strict": "boolean",
   "allow_post_precision_vars": "boolean",
   "allow_post_as_secondary_outcome": "boolean",
   "diagnostics_on_post_vars": "boolean"
  }
 },
 "P08": {
  "defaults": {
   "source": "schema_roles",
   "allow_data_driven": false,
   "manual_list": [],
   "include_roles": [
    "confounder"
   ],
   "include_precision_vars": true,
   "exclude_roles": [
    "mediator",
    "collider",
    "instrument",
    "noise",
    "outcome",
    "treatment",
    "treatment_version",
    "id"
   ],
   "ambiguous_action": "both",
   "basis": {
    "continuous": "quadratic",
    "spline_df": 4
   },
   "interactions": [
    [
     "country",
     "*"
    ]
   ],
   "rare_level_action": "group",
   "rare_level_threshold": 0.01,
   "min_variation": 1e-12
  },
  "allowed": {
   "source": [
    "schema_roles",
    "manual",
    "data_driven"
   ],
   "allow_data_driven": "boolean",
   "manual_list": "array",
   "include_roles": "array",
   "include_precision_vars": "boolean",
   "exclude_roles": "array",
   "ambiguous_action": [
    "both",
    "include",
    "exclude"
   ],
   "basis": {
    "continuous": [
     "linear",
     "quadratic",
     "spline"
    ],
    "spline_df": "integer"
   },
   "interactions": "array",
   "rare_level_action": [
    "group",
    "keep",
    "drop"
   ],
   "rare_level_threshold": "number",
   "min_variation": "number"
  }
 },
 "P09": {
  "defaults": {
   "cluster_key": [
    "grower_id"
   ],
   "fold_strategy": "group_stratified",
   "n_folds": 5,
   "seed": 20260921,
   "year_handling": "fixed_effect",
   "large_cluster_warn": 0.05,
   "compute_icc": true
  },
  "allowed": {
   "cluster_key": "array",
   "fold_strategy": [
    "group_stratified",
    "group",
    "random"
   ],
   "n_folds": "integer",
   "seed": "integer",
   "year_handling": [
    "fixed_effect",
    "second_cluster",
    "ignore"
   ],
   "large_cluster_warn": "number",
   "compute_icc": "boolean"
  }
 }
}
```

## §3. `variable_roles.json` — từ điển vai trò biến (từ `data_dictionary.csv` do P08 sinh)

`variant_membership`: biến thuộc biến thể L nào. Cột `reason` của backend đang rỗng — UI sinh lý do từ `blocked_reason_rules` ở §5.

```json
[
 {
  "column": "record_id",
  "dtype": "string",
  "measured_at": "pre",
  "affected_by_treatment": null,
  "dag_role": "id",
  "in_L": false,
  "variant_membership": "[]",
  "reason": null
 },
 {
  "column": "grower_id",
  "dtype": "string",
  "measured_at": "pre",
  "affected_by_treatment": null,
  "dag_role": "cluster",
  "in_L": false,
  "variant_membership": "[]",
  "reason": null
 },
 {
  "column": "field_id",
  "dtype": "string",
  "measured_at": "pre",
  "affected_by_treatment": null,
  "dag_role": "id",
  "in_L": false,
  "variant_membership": "[]",
  "reason": null
 },
 {
  "column": "country",
  "dtype": "category",
  "measured_at": "pre",
  "affected_by_treatment": null,
  "dag_role": "confounder",
  "in_L": true,
  "variant_membership": "['O_as_confounder', 'O_as_mediator']",
  "reason": null
 },
 {
  "column": "year",
  "dtype": "int16",
  "measured_at": "at",
  "affected_by_treatment": null,
  "dag_role": "confounder",
  "in_L": true,
  "variant_membership": "['O_as_confounder', 'O_as_mediator']",
  "reason": null
 },
 {
  "column": "rain_longterm_mm",
  "dtype": "float32",
  "measured_at": "pre",
  "affected_by_treatment": null,
  "dag_role": "confounder",
  "in_L": true,
  "variant_membership": "['O_as_confounder', 'O_as_mediator']",
  "reason": null
 },
 {
  "column": "temp_longterm_c",
  "dtype": "float32",
  "measured_at": "pre",
  "affected_by_treatment": null,
  "dag_role": "confounder",
  "in_L": true,
  "variant_membership": "['O_as_confounder', 'O_as_mediator']",
  "reason": null
 },
 {
  "column": "soil_om_baseline_pct",
  "dtype": "float32",
  "measured_at": "pre",
  "affected_by_treatment": null,
  "dag_role": "confounder",
  "in_L": true,
  "variant_membership": "['O_as_confounder', 'O_as_mediator']",
  "reason": null
 },
 {
  "column": "field_size_ha",
  "dtype": "float32",
  "measured_at": "pre",
  "affected_by_treatment": null,
  "dag_role": "confounder",
  "in_L": true,
  "variant_membership": "['O_as_confounder', 'O_as_mediator']",
  "reason": null
 },
 {
  "column": "extension_access",
  "dtype": "boolean",
  "measured_at": "pre",
  "affected_by_treatment": null,
  "dag_role": "confounder",
  "in_L": true,
  "variant_membership": "['O_as_confounder', 'O_as_mediator']",
  "reason": null
 },
 {
  "column": "contract",
  "dtype": "category",
  "measured_at": "pre",
  "affected_by_treatment": null,
  "dag_role": "confounder",
  "in_L": true,
  "variant_membership": "['O_as_confounder', 'O_as_mediator']",
  "reason": null
 },
 {
  "column": "experience_yr",
  "dtype": "int16",
  "measured_at": "pre",
  "affected_by_treatment": null,
  "dag_role": "confounder",
  "in_L": true,
  "variant_membership": "['O_as_confounder', 'O_as_mediator']",
  "reason": null
 },
 {
  "column": "irrigation",
  "dtype": "boolean",
  "measured_at": "pre",
  "affected_by_treatment": null,
  "dag_role": "confounder",
  "in_L": true,
  "variant_membership": "['O_as_confounder', 'O_as_mediator']",
  "reason": null
 },
 {
  "column": "no_till",
  "dtype": "boolean",
  "measured_at": "pre",
  "affected_by_treatment": null,
  "dag_role": "ambiguous",
  "in_L": true,
  "variant_membership": "['O_as_confounder']",
  "reason": null
 },
 {
  "column": "organic_fert",
  "dtype": "boolean",
  "measured_at": "pre",
  "affected_by_treatment": null,
  "dag_role": "ambiguous",
  "in_L": true,
  "variant_membership": "['O_as_confounder']",
  "reason": null
 },
 {
  "column": "rotation_len_yr",
  "dtype": "int16",
  "measured_at": "pre",
  "affected_by_treatment": null,
  "dag_role": "ambiguous",
  "in_L": true,
  "variant_membership": "['O_as_confounder']",
  "reason": null
 },
 {
  "column": "cover_crop",
  "dtype": "boolean",
  "measured_at": "at",
  "affected_by_treatment": null,
  "dag_role": "treatment",
  "in_L": false,
  "variant_membership": "[]",
  "reason": null
 },
 {
  "column": "cover_crop_months",
  "dtype": "float32",
  "measured_at": "at",
  "affected_by_treatment": null,
  "dag_role": "treatment_version",
  "in_L": false,
  "variant_membership": "[]",
  "reason": null
 },
 {
  "column": "cover_crop_type",
  "dtype": "category",
  "measured_at": "at",
  "affected_by_treatment": null,
  "dag_role": "treatment_version",
  "in_L": false,
  "variant_membership": "[]",
  "reason": null
 },
 {
  "column": "soil_om_post_pct",
  "dtype": "float32",
  "measured_at": "post",
  "affected_by_treatment": true,
  "dag_role": "mediator",
  "in_L": false,
  "variant_membership": "[]",
  "reason": null
 },
 {
  "column": "weed_pressure",
  "dtype": "int8",
  "measured_at": "post",
  "affected_by_treatment": true,
  "dag_role": "mediator",
  "in_L": false,
  "variant_membership": "[]",
  "reason": null
 },
 {
  "column": "season_rain_mm",
  "dtype": "float32",
  "measured_at": "post",
  "affected_by_treatment": false,
  "dag_role": "outcome_predictor",
  "in_L": false,
  "variant_membership": "[]",
  "reason": null
 },
 {
  "column": "buyer_incentive",
  "dtype": "boolean",
  "measured_at": "pre",
  "affected_by_treatment": null,
  "dag_role": "instrument",
  "in_L": false,
  "variant_membership": "[]",
  "reason": null
 },
 {
  "column": "noise_1",
  "dtype": "float32",
  "measured_at": "pre",
  "affected_by_treatment": null,
  "dag_role": "noise",
  "in_L": false,
  "variant_membership": "[]",
  "reason": null
 },
 {
  "column": "noise_2",
  "dtype": "float32",
  "measured_at": "pre",
  "affected_by_treatment": null,
  "dag_role": "noise",
  "in_L": false,
  "variant_membership": "[]",
  "reason": null
 },
 {
  "column": "noise_3",
  "dtype": "float32",
  "measured_at": "pre",
  "affected_by_treatment": null,
  "dag_role": "noise",
  "in_L": false,
  "variant_membership": "[]",
  "reason": null
 },
 {
  "column": "noise_4",
  "dtype": "float32",
  "measured_at": "pre",
  "affected_by_treatment": null,
  "dag_role": "noise",
  "in_L": false,
  "variant_membership": "[]",
  "reason": null
 },
 {
  "column": "noise_5",
  "dtype": "float32",
  "measured_at": "pre",
  "affected_by_treatment": null,
  "dag_role": "noise",
  "in_L": false,
  "variant_membership": "[]",
  "reason": null
 },
 {
  "column": "yield_t_ha",
  "dtype": "float32",
  "measured_at": "post",
  "affected_by_treatment": true,
  "dag_role": "outcome",
  "in_L": false,
  "variant_membership": "[]",
  "reason": null
 },
 {
  "column": "in_program",
  "dtype": "boolean",
  "measured_at": "post",
  "affected_by_treatment": true,
  "dag_role": "collider",
  "in_L": false,
  "variant_membership": "[]",
  "reason": null
 }
]
```

## §4. `artifacts_preview.json` — xem trước artifact của kịch bản A

```json
{
 "quarantine": {
  "step": "P01",
  "n_rows": 2,
  "columns": [
   "record_id",
   "grower_id",
   "field_id",
   "year",
   "country",
   "cover_crop",
   "yield_t_ha",
   "temp_longterm_c"
  ],
  "rows": [
   {
    "record_id": "<NA>",
    "grower_id": "G0109",
    "field_id": "F_G0109_3",
    "year": "2026",
    "country": "C2",
    "cover_crop": "False",
    "yield_t_ha": "52.097122",
    "temp_longterm_c": "29.18415"
   },
   {
    "record_id": "R00247",
    "grower_id": "G0106",
    "field_id": "F_G0106_3",
    "year": "2028",
    "country": "C2",
    "cover_crop": "False",
    "yield_t_ha": "321.323",
    "temp_longterm_c": "<NA>"
   }
  ]
 },
 "review_list": {
  "step": "P03",
  "n_rows": 6,
  "columns": [
   "record_id",
   "grower_id",
   "field_id",
   "year",
   "country",
   "cover_crop",
   "yield_t_ha",
   "dup_group_id"
  ],
  "rows": [
   {
    "record_id": "R00033",
    "grower_id": "G0022",
    "field_id": "F_G0022_2",
    "year": "2019",
    "country": "C3",
    "cover_crop": "False",
    "yield_t_ha": "50.300976",
    "dup_group_id": "g0deb55"
   },
   {
    "record_id": "R00033",
    "grower_id": "G0022",
    "field_id": "F_G0022_2",
    "year": "2019",
    "country": "C3",
    "cover_crop": "True",
    "yield_t_ha": "50.300976",
    "dup_group_id": "g0deb55"
   },
   {
    "record_id": "R00245",
    "grower_id": "G0136",
    "field_id": "F_G0136_3",
    "year": "2021",
    "country": "C3",
    "cover_crop": "False",
    "yield_t_ha": "43.37418",
    "dup_group_id": "gfa4f43"
   },
   {
    "record_id": "R00245",
    "grower_id": "G0136",
    "field_id": "F_G0136_3",
    "year": "2021",
    "country": "C3",
    "cover_crop": "False",
    "yield_t_ha": "<NA>",
    "dup_group_id": "gfa4f43"
   },
   {
    "record_id": "R00248",
    "grower_id": "G0169",
    "field_id": "F_G0169_1",
    "year": "2025",
    "country": "C3",
    "cover_crop": "False",
    "yield_t_ha": "53.89576",
    "dup_group_id": "g122162"
   },
   {
    "record_id": "R00248",
    "grower_id": "G0169",
    "field_id": "F_G0169_1",
    "year": "2025",
    "country": "C3",
    "cover_crop": "True",
    "yield_t_ha": "53.89576",
    "dup_group_id": "g122162"
   }
  ]
 }
}
```

## §5. `modules.json` — nội dung tiếng Việt của 9 module, làn, cạnh context, quy tắc lý do

`short`: câu Tầng 2 (dùng nguyên văn). `long` + `risk`: tab Vấn đề. Thứ tự trong `modules` chính là **thứ tự chạy**.

```json
{
 "modules": [
  {
   "id": "P01",
   "name": "schema_check",
   "file": "p01_schema_check.py",
   "lane": 1,
   "short": "Chặn dữ liệu sai dạng ngay ở cửa vào, trước khi lỗi âm thầm thành ô trống",
   "long": "Kiểm tra dữ liệu có đúng dạng cam kết trong canonical.yaml: đủ cột bắt buộc, đúng kiểu, record_id hợp lệ. Dòng hỏng thật (chuỗi trong cột số, record_id rỗng) bị cách ly vào artifact quarantine. Hạng mục lạ, số ngoài miền và cột nhị phân ghi dạng chữ (Yes/No) chỉ được đánh dấu, vì P02 và P04 mới là nơi xử lý chúng.",
   "risk": "Lỗi định dạng âm thầm biến thành ô trống ở các bước sau, đến cuối pipeline mới lộ ra và không còn truy được nguồn gốc."
  },
  {
   "id": "P02",
   "name": "harmonize",
   "file": "p02_harmonize.py",
   "lane": 1,
   "short": "Đưa một thứ ghi nhiều kiểu (tên nước, kg/ha vs t/ha, Yes/No) về một mã chuẩn",
   "long": "Chuẩn hóa chuỗi để so khớp rồi ánh xạ về mã canonical: 'Country 1', 'c1 ', 'C-1' thành C1; 'Yes/No/Có/Không' thành 1/0; quy đổi yield kg/ha sang t/ha khi có cột đơn vị. Giá trị khai null trong bảng alias (vd 'Partial') thành ô trống kèm cờ. Giá trị lạ ở country hoặc cover_crop dừng pipeline và được liệt kê hết trong một lần.",
   "risk": "Biến country phình thành hàng chục mức; các dòng ghi kg/ha lớn gấp 1000 lần và bị P04 coi là outlier hàng loạt."
  },
  {
   "id": "P03",
   "name": "deduplicate",
   "file": "p03_deduplicate.py",
   "lane": 1,
   "short": "Một ruộng-năm chỉ được đếm một lần — trùng lặp làm sai số chuẩn nhỏ giả",
   "long": "Nhóm theo khóa grower_id + field_id + year và phân loại: trùng hệt, trùng một phần, hoặc mâu thuẫn (khác nhau ở cover_crop, yield_t_ha, country, year). Trùng hệt và trùng một phần được gộp, giữ dòng đầy đủ nhất. Nhóm mâu thuẫn được giữ nguyên và đẩy sang artifact review_list để người xem.",
   "risk": "Cỡ mẫu to giả làm sai số chuẩn nhỏ giả, và một đơn vị bị nhân đôi trọng số ở bước IPW."
  },
  {
   "id": "P04",
   "name": "outliers",
   "file": "p04_outliers.py",
   "lane": 1,
   "short": "Phân biệt giá trị cực trị thật với lỗi nhập liệu; mặc định chỉ gắn cờ",
   "long": "Phát hiện giá trị bất thường trong từng nước: yield và diện tích dùng miền giá trị của schema, biến khác dùng robust z-score. Thử chia giá trị bất thường cho 10, 100, 1000 để nhận ra lỗi đơn vị. Mặc định chỉ gắn cờ. Nếu tỷ lệ dòng bị gắn cờ vượt max_flag_rate thì chặn pipeline, vì đó thường là lỗi hệ thống (đơn vị, nhầm cột) chứ không phải outlier lẻ.",
   "risk": "Độ lệch chuẩn bị thổi phồng làm chỉ số cân bằng SMD 'đẹp giả'; một điểm cực trị trong nước ít mẫu có thể chi phối cả ước lượng."
  },
  {
   "id": "P05",
   "name": "treatment_define",
   "file": "p05_treatment_define.py",
   "lane": 2,
   "short": "Định nghĩa \"có cover crop\": ngưỡng số tháng, dòng \"Partial\", phiên bản treatment",
   "long": "Biến cover_crop_months thành A ∈ {0,1} theo ngưỡng (mặc định ≥ 2 tháng), sinh cột độ nhạy cho ngưỡng 1/2/3 tháng, gắn cờ và tách riêng các dòng 'Partial' để xem lại, và cảnh báo khi các loại cây che phủ cho năng suất lệch nhau nhiều (dấu hiệu vi phạm consistency).",
   "risk": "Ước lượng trộn nhiều phiên bản can thiệp khác nhau và phụ thuộc cơ cấu mẫu; ngưỡng định nghĩa treatment không được ghi lại."
  },
  {
   "id": "P07",
   "name": "time_order",
   "file": "p07_time_order.py",
   "lane": 2,
   "short": "Chặn biến đo sau can thiệp khỏi tập điều chỉnh (mediator, collider)",
   "long": "Đọc thời điểm đo (measured_at) và affected_by_treatment của từng cột trong schema, chặn mọi biến đo sau can thiệp khỏi danh sách được phép điều chỉnh. Hậu điều kiện cứng: soil_om_post_pct, weed_pressure, in_program luôn phải bị chặn. Cột không khai trong schema bị coi là không rõ thời điểm đo và bị chặn theo mặc định.",
   "risk": "Điều chỉnh theo mediator làm ước lượng tụt về gần 0; điều chỉnh theo collider tạo ra liên hệ giả. Không chỉ số thống kê nào phát hiện được lỗi này — chỉ thứ tự thời gian mới phân biệt được."
  },
  {
   "id": "P08",
   "name": "variable_roles",
   "file": "p08_variable_roles.py",
   "lane": 2,
   "short": "Dựng tập điều chỉnh L theo vai trò trong DAG, không theo độ dự báo",
   "long": "Dựng tập điều chỉnh L từ vai trò khai trong schema: lấy confounder, loại mediator, collider, instrument, noise. Các practice RA khác (no_till, organic_fert, rotation_len_yr) chưa rõ vai trò nên được tạo thành hai biến thể O_as_confounder / O_as_mediator để báo cáo cả hai.",
   "risk": "Chọn biến theo độ dự báo sẽ kéo mediator vào (vì dự báo Y tốt), kéo biến kiểu instrument vào (làm khuếch đại bias còn lại), và kéo biến nhiễu vào (làm propensity score quá khớp)."
  },
  {
   "id": "P06",
   "name": "missingness",
   "file": "p06_missingness.py",
   "lane": 3,
   "short": "Mô tả thiếu dữ liệu trong L, A, Y; điền thiếu kèm cờ; không kết luận MAR/MNAR",
   "long": "Chỉ xét biến trong L, A và Y. Lập bảng thiếu theo cột × nước × nhóm A, cảnh báo khi thiếu lệch giữa hai nhóm A hoặc thiếu có cấu trúc (100% ở một nước). Loại khỏi L cột thiếu quá 40%, điền trung vị theo nước kèm cờ, và tạo cột c_outcome_observed cho bước IPCW sau này. Chỉ mô tả cơ chế thiếu, không kết luận MAR hay MNAR.",
   "risk": "Thư viện mô hình tự bỏ dòng có ô trống, nên quần thể phân tích đổi mà không ai chủ động quyết định."
  },
  {
   "id": "P09",
   "name": "clusters",
   "file": "p09_clusters.py",
   "lane": 3,
   "short": "Gom dòng theo nông hộ và chia fold theo cụm để tránh rò rỉ khi cross-fit",
   "long": "Gán cluster_id theo nông hộ, chia 5 fold theo cụm có phân tầng theo A, bảo đảm một nông hộ không nằm ở hai fold. Tính ICC thô của yield để biết mức tương quan trong cụm.",
   "risk": "Sai số chuẩn nhỏ giả (khoảng tin cậy hẹp hơn thực tế) và rò rỉ thông tin giữa các fold khi cross-fit."
  }
 ],
 "lanes": [
  {
   "id": 1,
   "label": "Lớp 1 · Chất lượng dữ liệu",
   "question": "Dữ liệu có đọc được không?",
   "modules": [
    "P01",
    "P02",
    "P03",
    "P04"
   ]
  },
  {
   "id": 2,
   "label": "Lớp 2 · Định nghĩa biến",
   "question": "Ta đang đo cái gì, được phép điều chỉnh theo cái gì?",
   "modules": [
    "P05",
    "P07",
    "P08"
   ]
  },
  {
   "id": 3,
   "label": "Lớp 3 · Cấu trúc mẫu",
   "question": "Mỗi dòng có phải một đơn vị độc lập không?",
   "modules": [
    "P06",
    "P09"
   ]
  }
 ],
 "context_edges": [
  {
   "from": "P07",
   "to": "P08",
   "key": "eligible_columns",
   "meaning": "Danh sách cột được phép xét làm biến điều chỉnh"
  },
  {
   "from": "P08",
   "to": "P06",
   "key": "adjustment_set",
   "meaning": "Tập điều chỉnh L — P06 chỉ điền thiếu cho biến trong L"
  },
  {
   "from": "P05",
   "to": "P06",
   "key": "treatment_column",
   "meaning": "Cột treatment dùng để so tỷ lệ thiếu giữa hai nhóm A"
  },
  {
   "from": "P05",
   "to": "P09",
   "key": "treatment_column",
   "meaning": "Cột treatment dùng để phân tầng khi chia fold"
  }
 ],
 "blocked_reason_rules": [
  {
   "when": {
    "dag_role": "mediator"
   },
   "text": "Đo sau can thiệp và nằm trên đường A → Y (mediator). Điều chỉnh sẽ chặn chính tác động cần đo."
  },
  {
   "when": {
    "dag_role": "collider"
   },
   "text": "Chịu ảnh hưởng của cả A và Y (collider). Điều chỉnh sẽ tạo liên hệ giả."
  },
  {
   "when": {
    "dag_role": "outcome"
   },
   "text": "Là outcome Y."
  },
  {
   "when": {
    "dag_role": "treatment"
   },
   "text": "Là treatment A."
  },
  {
   "when": {
    "dag_role": "treatment_version"
   },
   "text": "Mô tả phiên bản treatment, không phải biến điều chỉnh."
  },
  {
   "when": {
    "dag_role": "instrument"
   },
   "text": "Kiểu instrument: dự báo A mạnh nhưng không cần điều chỉnh; đưa vào sẽ khuếch đại bias còn lại."
  },
  {
   "when": {
    "dag_role": "noise"
   },
   "text": "Biến nhiễu, không liên quan nhân quả."
  },
  {
   "when": {
    "dag_role": "id"
   },
   "text": "Mã định danh."
  },
  {
   "when": {
    "dag_role": "cluster"
   },
   "text": "Khóa cụm (nông hộ) — dùng ở P09, không phải biến điều chỉnh."
  },
  {
   "when": {
    "dag_role": "outcome_predictor",
    "measured_at": "post"
   },
   "text": "Đo sau time zero nhưng không chịu ảnh hưởng can thiệp; chỉ được dùng khi bật allow_post_precision_vars."
  },
  {
   "when": {
    "in_L": true,
    "variant_membership_len": 1
   },
   "text": "Practice RA khác, vai trò chưa rõ: chỉ có trong biến thể O_as_confounder."
  }
 ]
}
```

## §6. `error_codes.json` — từ điển mã (tooltip + panel tra cứu)

Mã bắt đầu bằng `*.` áp dụng cho mọi module (khớp theo hậu tố).

```json
[
 {
  "code": "P01.MISSING_REQUIRED_COLUMN",
  "explain": "Thiếu cột bắt buộc theo schema; pipeline dừng vì không có gì để phân tích."
 },
 {
  "code": "P01.UNKNOWN_COLUMN",
  "explain": "Có cột không khai trong schema; được giữ lại kèm cảnh báo."
 },
 {
  "code": "P01.COERCE_FAILED",
  "explain": "Ô không ép được sang kiểu của schema (vd chữ 'abc' trong cột số); dòng đó bị cách ly."
 },
 {
  "code": "P01.OUT_OF_RANGE",
  "explain": "Giá trị nằm ngoài miền 'không thể' của schema; chỉ đánh dấu, vì có thể là lỗi đơn vị mà P02 sẽ quy đổi."
 },
 {
  "code": "P01.NOT_ALLOWED_CATEGORY",
  "explain": "Giá trị hạng mục chưa đúng mã chuẩn (vd 'Country 1'); chỉ đánh dấu để P02 ánh xạ."
 },
 {
  "code": "P01.BAD_RECORD_ID",
  "explain": "record_id rỗng hoặc thiếu; dòng luôn bị cách ly vì không truy vết được."
 },
 {
  "code": "P01.DUPLICATE_KEY_SEEN",
  "explain": "Phát hiện record_id trùng; để P03 xử lý."
 },
 {
  "code": "P01.EMPTY_INPUT",
  "explain": "Dữ liệu vào rỗng."
 },
 {
  "code": "P01.DEFERRED_TO_P02",
  "explain": "Cột nhị phân/hạng mục ghi dạng chữ (Yes/No/Có/Không) được để nguyên cho P02 ánh xạ, không bị coi là lỗi."
 },
 {
  "code": "P01.SCHEMA_ERROR",
  "explain": "Có lỗi schema và on_error = raise nên pipeline dừng."
 },
 {
  "code": "P02.UNMAPPED_CATEGORY",
  "explain": "Giá trị không có trong bảng alias. Ở country/cover_crop thì dừng pipeline và liệt kê mọi giá trị lạ; ở cột khác thì thành ô trống kèm cờ."
 },
 {
  "code": "P02.ALIAS_TO_NA",
  "explain": "Giá trị hợp lệ nhưng được khai 'cố ý để trống' (alias null, vd 'Partial'); thành ô trống kèm cờ để xem lại."
 },
 {
  "code": "P02.FUZZY_SUGGESTION",
  "explain": "Đề xuất ánh xạ gần đúng; chưa áp dụng vào dữ liệu."
 },
 {
  "code": "P02.UNIT_CONVERTED",
  "explain": "Đã quy đổi yield từ kg/ha sang t/ha theo cột đơn vị."
 },
 {
  "code": "P02.UNIT_INFERRED",
  "explain": "Đơn vị được SUY LUẬN theo ngưỡng chứ không khai báo; một ruộng năng suất thật sự cao có thể bị chia nhầm."
 },
 {
  "code": "P02.UNIT_POLICY_UNAVAILABLE",
  "explain": "Không có thông tin đơn vị nên không quy đổi; P04 sẽ gắn cờ nghi lỗi đơn vị."
 },
 {
  "code": "P02.MIXED_UNIT_SUSPECTED",
  "explain": "Phân phối yield có hai cụm cách nhau khoảng 1000 lần — dấu hiệu trộn đơn vị."
 },
 {
  "code": "P02.CATEGORY_LEVELS_FROM_DATA",
  "explain": "Mức hạng mục lấy từ dữ liệu thay vì schema; tập mức có thể đổi giữa các lần chạy."
 },
 {
  "code": "P03.EXACT_DUPLICATES",
  "explain": "Có nhóm dòng trùng hệt nhau; đã gộp."
 },
 {
  "code": "P03.PARTIAL_DUPLICATES",
  "explain": "Có nhóm trùng khóa nhưng khác ở cột phụ; đã gộp, giữ dòng đầy đủ nhất."
 },
 {
  "code": "P03.CONFLICTING_DUPLICATES",
  "explain": "Có nhóm trùng khóa nhưng khác ở cột quan trọng (A, Y, nước, năm) — dấu hiệu lỗi ghép bảng. Giữ nguyên mọi dòng, xem trong review_list."
 },
 {
  "code": "P03.NULL_KEY",
  "explain": "Có dòng thiếu một phần khóa nghiệp vụ; không gộp được."
 },
 {
  "code": "P03.KEY_NOT_UNIQUE_AFTER_RESOLVE",
  "explain": "Sau khi gộp mà khóa vẫn trùng — lỗi logic của module."
 },
 {
  "code": "P03.CONFIG_ERROR",
  "explain": "Cấu hình không hợp lệ (vd keep_last mà thiếu timestamp_column)."
 },
 {
  "code": "P04.OUTLIERS_FLAGGED",
  "explain": "Đã gắn cờ giá trị bất thường; dữ liệu không bị sửa (mặc định flag_only)."
 },
 {
  "code": "P04.SUSPECTED_UNIT_ERROR",
  "explain": "Giá trị bất thường chia cho 10/100/1000 thì rơi vào miền hợp lệ — nghi nhầm đơn vị."
 },
 {
  "code": "P04.MAX_FLAG_RATE_EXCEEDED",
  "explain": "Tỷ lệ dòng bị gắn cờ vượt max_flag_rate. Thường là lỗi hệ thống (đơn vị, nhầm cột) chứ không phải outlier lẻ — hãy quay lại P02."
 },
 {
  "code": "P04.SMALL_GROUP",
  "explain": "Nhóm (nước) quá nhỏ để đặt ngưỡng riêng; dùng ngưỡng toàn cục."
 },
 {
  "code": "P04.ZERO_MAD",
  "explain": "Độ lệch tuyệt đối trung vị bằng 0; bỏ qua cột này ở nhóm đó."
 },
 {
  "code": "P04.NON_NUMERIC_COLUMN_SKIPPED",
  "explain": "Cột không phải số; không kiểm tra outlier."
 },
 {
  "code": "P04.ROWS_DROPPED",
  "explain": "Đã loại dòng bị gắn cờ (action = drop_row)."
 },
 {
  "code": "P05.FALLBACK_TO_BINARY",
  "explain": "Không có cột số tháng; dùng thẳng cover_crop dạng Có/Không."
 },
 {
  "code": "P05.PARTIAL_FLAGGED",
  "explain": "Dòng 'Partial' được giữ lại, gắn cờ và tách ra partial_review để xem lại."
 },
 {
  "code": "P05.OWN_LEVEL_NOT_BINARY",
  "explain": "partial_action = own_level cần treatment nhiều mức; với treatment nhị phân các dòng này để trống."
 },
 {
  "code": "P05.THRESHOLD_SENSITIVITY",
  "explain": "Số dòng đổi trạng thái treatment khi đổi ngưỡng số tháng — độ nhạy của định nghĩa A."
 },
 {
  "code": "P05.VERSION_HETEROGENEITY",
  "explain": "Năng suất giữa các loại cây che phủ lệch hơn 1 độ lệch chuẩn — nghi vi phạm consistency."
 },
 {
  "code": "P05.SMALL_VERSION_CELL",
  "explain": "Một phiên bản treatment có quá ít dòng để ước lượng riêng."
 },
 {
  "code": "P05.TREATMENT_MISSING",
  "explain": "Có dòng không xác định được treatment (ô trống)."
 },
 {
  "code": "P06.MISSING_SUMMARY",
  "explain": "Tóm tắt tỷ lệ thiếu theo cột, nước và nhóm A."
 },
 {
  "code": "P06.MISSING_DIFFERS_BY_TREATMENT",
  "explain": "Tỷ lệ thiếu lệch giữa hai nhóm A — complete-case sẽ lệch, nên dùng trọng số IPCW."
 },
 {
  "code": "P06.STRUCTURAL_MISSING",
  "explain": "Một cột thiếu 100% ở ít nhất một nước — vấn đề thiết kế khảo sát."
 },
 {
  "code": "P06.COLUMN_DROPPED_HIGH_MISSING",
  "explain": "Cột thiếu quá max_missing_col nên bị loại khỏi L."
 },
 {
  "code": "P06.IMPUTED",
  "explain": "Đã điền thiếu (trung vị hoặc giá trị phổ biến) và gắn cờ các ô được điền."
 },
 {
  "code": "P06.SMALL_GROUP",
  "explain": "Nhóm quá nhỏ; điền bằng giá trị toàn cục thay vì theo nước."
 },
 {
  "code": "P06.OUTCOME_MISSING_RATE",
  "explain": "Số dòng thiếu outcome; không bỏ dòng, chỉ tạo cờ c_outcome_observed."
 },
 {
  "code": "P06.MECHANISM_REGRESS",
  "explain": "Các biến dự báo mạnh nhất cho việc thiếu outcome (chỉ mô tả, không kết luận MAR/MNAR)."
 },
 {
  "code": "P06.MISSING_ADJUSTMENT_SET",
  "explain": "P06 chạy khi chưa có tập L (P08 chưa chạy)."
 },
 {
  "code": "P07.BLOCKED_POST_TREATMENT",
  "explain": "Biến đo sau can thiệp bị chặn khỏi tập điều chỉnh. Đây là hành vi ĐÚNG, không phải lỗi."
 },
 {
  "code": "P07.UNKNOWN_TIMING",
  "explain": "Không rõ thời điểm đo (cột không khai trong schema); chặn theo mặc định."
 },
 {
  "code": "P07.PRECISION_VAR_ALLOWED",
  "explain": "Cho phép một biến đo sau time zero nhưng không chịu ảnh hưởng can thiệp; cần ghi lý do trong báo cáo."
 },
 {
  "code": "P07.SECONDARY_OUTCOME_ALLOWED",
  "explain": "Outcome được giữ trong dữ liệu để phân tích sau; không vào tập điều chỉnh."
 },
 {
  "code": "P07.TIME_SOURCE_CONFLICT",
  "explain": "Schema và hậu tố tên cột mâu thuẫn về thời điểm đo; ưu tiên schema."
 },
 {
  "code": "P07.POST_VAR_NOT_BLOCKED",
  "explain": "LỖI: một biến bắt buộc phải chặn (mediator/collider) lại không bị chặn."
 },
 {
  "code": "P08.ADJUSTMENT_SET_BUILT",
  "explain": "Đã dựng tập điều chỉnh L."
 },
 {
  "code": "P08.AMBIGUOUS_ROLE",
  "explain": "Có biến vai trò chưa rõ (practice RA khác); đã tạo hai biến thể L để báo cáo cả hai."
 },
 {
  "code": "P08.RARE_LEVEL_GROUPED",
  "explain": "Mức hạng mục hiếm được gộp thành 'other'."
 },
 {
  "code": "P08.ZERO_VARIANCE_DROPPED",
  "explain": "Biến gần như không biến thiên (hoặc toàn ô trống) bị loại khỏi L."
 },
 {
  "code": "P08.DATA_DRIVEN_USED",
  "explain": "Chọn biến theo dữ liệu — chỉ dùng để đối chứng, không dùng cho phân tích chính."
 },
 {
  "code": "P08.FORBIDDEN_COLUMN_IN_L",
  "explain": "LỖI: biến bị cấm (mediator, collider, instrument, outcome…) lọt vào L."
 },
 {
  "code": "P08.MISSING_ELIGIBLE_COLUMNS",
  "explain": "P08 chạy khi chưa có danh sách cột hợp lệ (P07 chưa chạy)."
 },
 {
  "code": "P09.CLUSTER_SUMMARY",
  "explain": "Số cụm (nông hộ) và phân phối kích thước."
 },
 {
  "code": "P09.LARGE_CLUSTER",
  "explain": "Một cụm chiếm quá nhiều dòng — dấu hiệu lỗi ghép bảng."
 },
 {
  "code": "P09.MISSING_CLUSTER_KEY",
  "explain": "Dòng thiếu khóa cụm được coi là một cụm riêng."
 },
 {
  "code": "P09.MISSING_TREATMENT",
  "explain": "Dòng thiếu treatment nhận fold_id = -1, không tham gia chia fold."
 },
 {
  "code": "P09.FALLBACK_TO_GROUP_KFOLD",
  "explain": "Quá ít cụm hoặc mẫu để phân tầng; lùi về GroupKFold."
 },
 {
  "code": "P09.ICC_ESTIMATE",
  "explain": "ICC thô của yield — mức tương quan trong cùng nông hộ (chỉ để phát hiện, không để báo cáo)."
 },
 {
  "code": "P09.CLUSTER_SPLIT_ACROSS_FOLDS",
  "explain": "LỖI: một nông hộ nằm ở hai fold."
 },
 {
  "code": "*.SUMMARY",
  "explain": "Thống kê tổng hợp của module (nằm trong details). Không hiển thị như một phát hiện."
 },
 {
  "code": "*.EXCESSIVE_ROW_LOSS",
  "explain": "Bước này loại quá tỷ lệ dòng cho phép (mặc định 20%) nên pipeline dừng ngay tại đây."
 },
 {
  "code": "*.UNEXPECTED_EXCEPTION",
  "explain": "Lỗi lập trình ngoài dự kiến; xem traceback trong details."
 },
 {
  "code": "*.LOST_ROWS",
  "explain": "Module làm mất dòng mà không khai báo — vi phạm hợp đồng."
 },
 {
  "code": "*.DUPLICATE_RECORD_ID",
  "explain": "Module tự tạo ra record_id trùng — vi phạm hợp đồng."
 }
]
```

## §7. `param_docs.json` — mô tả tham số (tooltip trong tab Tham số)

```json
{
 "P01": {
  "on_error": "Xử lý dòng lỗi schema: cách ly, dừng, hay chỉ gắn cờ.",
  "dtype_coercion": "permissive: thử ép kiểu, ô hỏng thành trống; strict: ép hỏng là dừng.",
  "out_of_range": "Giá trị ngoài miền: flag chỉ đánh dấu (mặc định, để P02/P04 xử lý).",
  "unknown_columns": "Cột không có trong schema: giữ kèm cảnh báo, bỏ, hay dừng.",
  "duplicate_key_action": "record_id trùng: để P03 xử lý hay dừng ngay.",
  "required_id_columns": "Cột định danh; dòng rỗng ở đây luôn bị cách ly."
 },
 "P02": {
  "string_normalize": "Cắt khoảng trắng, hạ hoa, bỏ dấu — chỉ để SO KHỚP, giá trị ghi ra vẫn là mã chuẩn.",
  "category_mapping_mode": "explicit: chỉ dùng bảng alias; fuzzy_suggest: đề xuất; fuzzy_auto: tự ánh xạ gần đúng.",
  "fuzzy_threshold": "Độ tương đồng tối thiểu cho khớp gần đúng.",
  "unmapped_action": "Giá trị không có trong alias: to_na, keep_raw, hay raise (dừng). country và cover_crop đặt raise.",
  "unit_policy": "Cách xác định đơn vị yield: theo cột đơn vị, theo khai báo nguồn, hay suy luận theo ngưỡng.",
  "unit_column_name": "Tên cột ghi đơn vị trong dữ liệu thô.",
  "unit_fallback": "Khi không có cột đơn vị.",
  "unit_threshold": "Ngưỡng suy luận kg/ha (chỉ dùng khi unit_policy = threshold_inference).",
  "decimal_comma": "Nhận dấu phẩy thập phân (3,8).",
  "category_levels_source": "Tập mức hạng mục lấy từ schema (ổn định) hay từ dữ liệu."
 },
 "P03": {
  "key": "Khóa nghiệp vụ xác định một ruộng-năm.",
  "resolve": "Cách gộp nhóm trùng.",
  "timestamp_column": "Cột thời gian, bắt buộc khi resolve = keep_last.",
  "conflict_action": "Nhóm mâu thuẫn: đưa vào review_list (mặc định, giữ nguyên dòng), bỏ cả nhóm, hay gộp.",
  "critical_columns": "Khác nhau ở các cột này thì coi là mâu thuẫn chứ không phải trùng lặp.",
  "numeric_tolerance": "Dung sai khi so hai số thực.",
  "aggregate_rules": "Quy tắc gộp khi resolve = aggregate."
 },
 "P04": {
  "columns": "Các cột được kiểm tra outlier.",
  "method": "Phương pháp mặc định.",
  "method_by_column": "Phương pháp riêng cho từng cột (ghi đè method).",
  "iqr_k": "Hệ số k của IQR.",
  "robust_z_threshold": "Ngưỡng z bền (theo MAD).",
  "percentile_bounds": "Cận phân vị dưới/trên.",
  "group_by": "Tính ngưỡng trong từng nhóm (mặc định theo nước).",
  "min_group_size": "Nhóm nhỏ hơn thì dùng ngưỡng toàn cục.",
  "action": "Xử lý giá trị bất thường; mặc định flag_only — không sửa dữ liệu.",
  "parallel_actions": "Sinh thêm cột dẫn xuất để so sánh (vd yield_t_ha__winsorized).",
  "winsorize_at": "Kéo về đúng ngưỡng phát hiện hay về phân vị.",
  "max_flag_rate": "Vượt tỷ lệ này thì chặn pipeline (BLOCKED).",
  "unit_error_detection": "Thử chia 10/100/1000 để nhận ra lỗi đơn vị.",
  "unit_error_factors": "Các hệ số thử."
 },
 "P05": {
  "mode": "Chỉ binary_threshold đã hiện thực; các giá trị khác chưa có tác dụng.",
  "source_column": "Cột nguồn để định nghĩa treatment.",
  "threshold_months": "A = 1 khi số tháng ≥ ngưỡng này.",
  "threshold_sensitivity": "Các ngưỡng sinh cột độ nhạy cover_crop__thr*.",
  "partial_action": "Giá trị của cover_crop ở dòng 'Partial'. Mọi lựa chọn đều giữ dòng và gắn cờ.",
  "type_grouping": "Gộp loại cây che phủ.",
  "min_cell": "Phiên bản ít hơn số dòng này thì cảnh báo.",
  "write_treatment_column": "Ghi đè cột cover_crop bằng định nghĩa mới (giá trị cũ lưu ở cover_crop__raw)."
 },
 "P06": {
  "scope": "Chỉ xét L + A + Y (mặc định) hay mọi cột.",
  "outcome_missing": "ipcw_flag: không bỏ dòng, chỉ tạo cờ c_outcome_observed.",
  "covariate_missing": "Cách điền thiếu covariate.",
  "impute_group_by": "Điền theo nhóm (mặc định theo nước).",
  "min_group_size": "Nhóm nhỏ hơn thì điền bằng giá trị toàn cục.",
  "keep_indicator": "Giữ cột cờ cho ô được điền.",
  "max_missing_col": "Cột thiếu quá tỷ lệ này bị loại khỏi L.",
  "mechanism_check": "describe: bảng mô tả; regress: hồi quy cờ thiếu theo L và A (chỉ mô tả).",
  "diff_warn_threshold": "Chênh lệch tỷ lệ thiếu giữa hai nhóm A để cảnh báo."
 },
 "P07": {
  "time_source": "Lấy thời điểm đo từ schema, từ hậu tố _post của tên cột, hay cả hai.",
  "unknown_action": "Cột không rõ thời điểm đo: loại khỏi L (mặc định), cho vào, hay dừng.",
  "strict": "Vi phạm hậu điều kiện thì dừng thay vì chỉ cảnh báo.",
  "allow_post_precision_vars": "Cho phép biến đo sau time zero nhưng không chịu ảnh hưởng can thiệp (vd season_rain_mm).",
  "allow_post_as_secondary_outcome": "Giữ outcome trong dữ liệu để phân tích sau.",
  "diagnostics_on_post_vars": "Mô tả biến đo sau can thiệp theo nhóm A (chỉ báo cáo)."
 },
 "P08": {
  "source": "Nguồn vai trò biến: schema (mặc định), danh sách tay, hay theo dữ liệu.",
  "allow_data_driven": "Phải bật mới được chọn biến theo dữ liệu.",
  "manual_list": "Danh sách biến khi source = manual.",
  "include_roles": "Vai trò được đưa vào L.",
  "include_precision_vars": "Thêm biến chỉ ảnh hưởng Y để giảm phương sai.",
  "exclude_roles": "Vai trò luôn bị loại khỏi L.",
  "ambiguous_action": "Biến vai trò chưa rõ: both tạo hai biến thể L.",
  "basis": "Dạng hàm cho propensity score sau này (chỉ khai báo).",
  "interactions": "Tương tác cho propensity score sau này (chỉ khai báo).",
  "rare_level_action": "Xử lý mức hạng mục hiếm.",
  "rare_level_threshold": "Mức chiếm ít hơn tỷ lệ này là hiếm.",
  "min_variation": "Biến có phương sai nhỏ hơn bị loại."
 },
 "P09": {
  "cluster_key": "Cột xác định cụm (mặc định nông hộ).",
  "fold_strategy": "Chia fold theo cụm, có phân tầng theo A.",
  "n_folds": "Số fold.",
  "seed": "Seed chia fold — cố định để chạy lại cho cùng kết quả.",
  "year_handling": "Cách xử lý năm (hiện chỉ khai báo).",
  "large_cluster_warn": "Một cụm chiếm quá tỷ lệ này thì cảnh báo.",
  "compute_icc": "Tính ICC thô của yield."
 }
}
```
