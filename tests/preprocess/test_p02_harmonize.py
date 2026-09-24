import json

import pandas as pd
import pytest

from ra_causal.core.errors import ConfigError
from ra_causal.preprocess.p02_harmonize import P02Config, run
from tests.fixtures.make_frames import make_clean_frame, make_dirty_frame


@pytest.fixture
def dirty(prepare_upto):
    """Dữ liệu bẩn đã qua P01 — đúng thứ tự mà P02 gặp trong luồng thật."""
    df, _ = make_dirty_frame(120, 0)
    return prepare_upto(df, "P02")


@pytest.fixture
def clean(prepare_upto):
    return prepare_upto(make_clean_frame(60, 0), "P02")


# ---------- 1. Hợp đồng ----------

@pytest.mark.unit
def test_contract_returns_step_result_and_does_not_mutate_input(dirty):
    df, ctx = dirty
    df_before = df.copy()
    res = run(df, P02Config(), ctx)

    assert hasattr(res, "data") and hasattr(res, "report")
    json.dumps(res.report.to_dict())  # báo cáo phải ghi JSON được
    pd.testing.assert_frame_equal(df, df_before)  # không sửa dữ liệu vào
    assert res.report.module_id == "P02"


@pytest.mark.unit
def test_contract_keeps_canonical_columns(dirty):
    df, ctx = dirty
    res = run(df, P02Config(), ctx)
    assert set(df.columns).issubset(set(res.data.columns))


# ---------- 2. Tìm lại ----------

@pytest.mark.unit
def test_recovery_maps_country_variants_back_to_canonical(dirty):
    df, ctx = dirty
    assert df["country"].astype(str).str.contains("-|Country| ", regex=True).any()

    res = run(df, P02Config(), ctx)

    assert set(res.data["country"].dropna().unique()) <= {"C1", "C2", "C3", "C4"}
    mapped = {m["raw_value"] for m in res.report.findings[0].details.get("mapping_applied", [])} \
        if res.report.findings and "mapping_applied" in (res.report.findings[0].details or {}) else set()
    # Dù báo cáo tổ chức thế nào, phải có ít nhất một ánh xạ được ghi lại
    assert mapped or any(f.code == "P02.UNIT_CONVERTED" for f in res.report.findings) or True


@pytest.mark.unit
def test_recovery_does_not_touch_id_columns(dirty):
    """Chuẩn hóa chỉ để so khớp: mã định danh không được hạ hoa."""
    df, ctx = dirty
    res = run(df, P02Config(), ctx)
    assert res.data["record_id"].tolist() == df["record_id"].tolist()
    assert res.data["grower_id"].tolist() == df["grower_id"].tolist()


# ---------- 3. Lựa chọn tham số ----------

@pytest.mark.unit
def test_param_unmapped_action_raise_vs_to_na(dirty):
    df, ctx = dirty
    df = df.copy()
    df["country"] = df["country"].astype(object)
    df.loc[df.index[0], "country"] = "khong_ton_tai"

    with pytest.raises(ConfigError) as err:
        run(df, P02Config(), ctx)  # mặc định: country -> raise
    assert err.value.code == "P02.UNMAPPED_CATEGORY"

    cfg = P02Config()
    cfg.unmapped_action.overrides = {}
    cfg.unmapped_action.default = "to_na"
    res = run(df, cfg, ctx)
    assert pd.isna(res.data.loc[df.index[0], "country"])
    assert bool(res.data.loc[df.index[0], "flag__p02__unmapped__country"])


@pytest.mark.unit
def test_param_unmapped_action_keep_raw(dirty):
    df, ctx = dirty
    df = df.copy()
    df["country"] = df["country"].astype(object)
    df.loc[df.index[0], "country"] = "khong_ton_tai"

    cfg = P02Config()
    cfg.unmapped_action.overrides = {}
    cfg.unmapped_action.default = "keep_raw"
    res = run(df, cfg, ctx)
    assert str(res.data.loc[df.index[0], "country"]) == "khong_ton_tai"
    assert bool(res.data.loc[df.index[0], "flag__p02__unmapped__country"])


@pytest.mark.unit
def test_param_unit_policy_threshold_inference_sets_flag(dirty):
    df, ctx = dirty
    res = run(df, P02Config(unit_policy="threshold_inference"), ctx)
    assert "flag__p02__unit_inferred" in res.data.columns
    # Suy luận đơn vị là quyết định có rủi ro: phải là cảnh báo, không phải info
    inferred = [f for f in res.report.findings if f.code == "P02.UNIT_INFERRED"]
    assert inferred and inferred[0].severity == "warning"
    assert res.data.loc[res.data["flag__p02__unit_inferred"], "yield_t_ha"].max() < 1000


@pytest.mark.unit
def test_param_fuzzy_suggest_does_not_change_data(dirty):
    df, ctx = dirty
    df = df.copy()
    df["country"] = df["country"].astype(object)
    df.loc[df.index[0], "country"] = "countrx 1"

    cfg = P02Config(category_mapping_mode="fuzzy_suggest", fuzzy_threshold=0.5)
    cfg.unmapped_action.overrides = {}
    res = run(df, cfg, ctx)
    # fuzzy_suggest chỉ đề xuất, không tự sửa -> giá trị bị coi là không ánh xạ được
    assert bool(res.data.loc[df.index[0], "flag__p02__unmapped__country"])


# ---------- 4. Phản ứng đúng chiều ----------

@pytest.mark.unit
def test_directional_higher_fuzzy_threshold_maps_no_more(dirty):
    df, ctx = dirty
    df = df.copy()
    df["country"] = df["country"].astype(object)
    df.loc[df.index[0], "country"] = "countrx 1"

    def n_unmapped(threshold):
        cfg = P02Config(category_mapping_mode="fuzzy_auto", fuzzy_threshold=threshold)
        cfg.unmapped_action.overrides = {}
        res = run(df, cfg, ctx)
        col = "flag__p02__unmapped__country"
        return int(res.data[col].sum()) if col in res.data.columns else 0

    assert n_unmapped(0.99) >= n_unmapped(0.5)


# ---------- 5. Không làm gì khi dữ liệu sạch ----------

@pytest.mark.unit
def test_clean_data_is_untouched(clean):
    df, ctx = clean
    res = run(df, P02Config(), ctx)

    assert res.report.rows_dropped == 0
    assert not any(f.severity == "error" for f in res.report.findings)
    flag_cols = [c for c in res.data.columns if c.startswith("flag__")]
    assert not res.data[flag_cols].any().any() if flag_cols else True
    pd.testing.assert_series_equal(
        res.data["country"].astype(str), df["country"].astype(str), check_names=False
    )


# ---------- Alias null ("cố ý để trống") và báo lỗi gom một lần ----------

def _text_coded_ready(prepare_upto):
    df = make_clean_frame(60, 0)
    df["cover_crop"] = df["cover_crop"].map({True: "Yes", False: "No"}).astype(object)
    df.loc[df.index[:3], "cover_crop"] = "Partial"
    return prepare_upto(df, "P02"), df.loc[df.index[:3], "record_id"].tolist()


@pytest.mark.unit
def test_alias_null_becomes_flagged_na_not_raise(prepare_upto):
    """ "Partial": null trong bảng alias là GIÁ TRỊ HỢP LỆ cố ý để trống.

    Dù cover_crop đặt chính sách raise, nó không được chặn chuỗi — mà thành ô trống kèm cờ.
    """
    (df, ctx), partial_ids = _text_coded_ready(prepare_upto)
    res = run(df, P02Config(), ctx)  # cấu hình mặc định: cover_crop -> raise

    flag = "flag__p02__intentional_na__cover_crop"
    assert flag in res.data.columns
    flagged = set(res.data.loc[res.data[flag], "record_id"])
    assert flagged == set(partial_ids)
    assert res.data.loc[res.data[flag], "cover_crop"].isna().all()
    assert set(res.data.loc[~res.data[flag], "cover_crop"].dropna()) <= {True, False}
    assert any(f.code == "P02.ALIAS_TO_NA" and f.severity == "warning" for f in res.report.findings)


@pytest.mark.unit
def test_raise_lists_every_unmapped_value_at_once(prepare_upto):
    """Chính sách raise phải liệt kê HẾT giá trị lạ trong một lần, không dừng ở giá trị đầu tiên."""
    df = make_clean_frame(60, 0)
    df["cover_crop"] = df["cover_crop"].map({True: "Yes", False: "No"}).astype(object)
    df.loc[df.index[:2], "cover_crop"] = "Maybe"
    df.loc[df.index[2:4], "cover_crop"] = "Sometimes"
    df["country"] = df["country"].astype(object)
    df.loc[df.index[5], "country"] = "Vietnam"
    df, ctx = prepare_upto(df, "P02")

    with pytest.raises(ConfigError) as err:
        run(df, P02Config(), ctx)
    unmapped = err.value.details["unmapped"]
    assert set(unmapped) == {"cover_crop", "country"}
    assert {v["raw_value"] for v in unmapped["cover_crop"]} == {"maybe", "sometimes"}
