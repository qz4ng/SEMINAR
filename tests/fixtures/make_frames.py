import pandas as pd
import numpy as np

def make_clean_frame(n: int = 200, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    
    # 60% with 1 row, 30% with 2 rows, 10% with 3+
    n_growers = int(n * 0.7)
    grower_ids = [f"G{str(i).zfill(4)}" for i in range(1, n_growers + 1)]
    
    # Randomly assign growers to rows to get approx the distribution
    weights = [0.6] * int(n_growers * 0.6) + [0.3] * int(n_growers * 0.3) + [0.1] * (n_growers - int(n_growers * 0.6) - int(n_growers * 0.3))
    weights = np.array(weights) / sum(weights)
    
    selected_growers = rng.choice(grower_ids, size=n, p=weights)
    
    countries = ["C1", "C2", "C3", "C4"]
    c_weights = [0.4, 0.3, 0.2, 0.1]
    
    data = []
    used_keys: set[tuple[str, str, int]] = set()
    for i in range(n):
        record_id = f"R{str(i+1).zfill(5)}"
        grower = selected_growers[i]

        # Khóa nghiệp vụ (grower, field, year) phải DUY NHẤT trong khung "sạch".
        # Nếu không, P03 sẽ báo trùng ngay trên dữ liệu sạch và test loại 5
        # ("module không làm gì khi dữ liệu sạch") mất ý nghĩa.
        for _ in range(100):
            field_id = f"F_{grower}_{rng.integers(1, 4)}"
            year = int(rng.integers(2015, 2030, endpoint=True))
            if (grower, field_id, year) not in used_keys:
                break
        else:  # không tìm được tổ hợp trống: tách bằng hậu tố của record_id
            field_id = f"F_{grower}_{record_id}"
            year = int(rng.integers(2015, 2030, endpoint=True))
        used_keys.add((grower, field_id, year))

        country = rng.choice(countries, p=c_weights)
        rain = rng.uniform(500, 2000)
        temp = rng.uniform(15, 30)
        som = rng.uniform(1, 10)
        size = rng.uniform(0.5, 10)
        ext = bool(rng.choice([0, 1]))
        contract = rng.choice(["none", "informal", "formal"])
        exp = rng.integers(1, 40)
        irr = bool(rng.choice([0, 1]))
        no_till = bool(rng.choice([0, 1]))
        org = bool(rng.choice([0, 1]))
        rot = rng.integers(1, 5)
        
        cc = bool(rng.choice([0, 1]))
        cc_months = rng.uniform(1, 6) if cc else 0.0
        cc_type = rng.choice(["legume", "grass", "mixed"]) if cc else "none"
        
        som_post = som + rng.uniform(-1, 2)
        som_post = max(0, min(20, som_post))
        weed = rng.integers(1, 5, endpoint=True)
        s_rain = rng.uniform(100, 1000)
        buyer = bool(rng.choice([0, 1]))
        n1, n2, n3, n4, n5 = rng.standard_normal(5)
        yield_t = rng.uniform(5, 60)
        in_prog = bool(rng.choice([0, 1]))
        
        data.append({
            "record_id": record_id,
            "grower_id": grower,
            "field_id": field_id,
            "country": country,
            "year": year,
            "rain_longterm_mm": float(rain),
            "temp_longterm_c": float(temp),
            "soil_om_baseline_pct": float(som),
            "field_size_ha": float(size),
            "extension_access": ext,
            "contract": contract,
            "experience_yr": exp,
            "irrigation": irr,
            "no_till": no_till,
            "organic_fert": org,
            "rotation_len_yr": rot,
            "cover_crop": cc,
            "cover_crop_months": float(cc_months),
            "cover_crop_type": cc_type,
            "soil_om_post_pct": float(som_post),
            "weed_pressure": int(weed),
            "season_rain_mm": float(s_rain),
            "buyer_incentive": buyer,
            "noise_1": float(n1),
            "noise_2": float(n2),
            "noise_3": float(n3),
            "noise_4": float(n4),
            "noise_5": float(n5),
            "yield_t_ha": float(yield_t),
            "in_program": in_prog
        })
        
    df = pd.DataFrame(data)
    # Ensure correct types
    df["country"] = df["country"].astype("category")
    df["contract"] = df["contract"].astype("category")
    df["cover_crop_type"] = df["cover_crop_type"].astype("category")
    
    return df

def inject_country_variants(df: pd.DataFrame, frac: float = 0.1, seed: int = 0):
    rng = np.random.default_rng(seed)
    n_change = int(len(df) * frac)
    if n_change == 0:
        return df.copy(), []
    
    df_out = df.copy()
    idx = rng.choice(df.index, size=n_change, replace=False)
    
    # Needs to be string to inject dirty values, will be handled by P02
    df_out["country"] = df_out["country"].astype(str)
    
    variants = ["Country 1", " c1 ", "C-1"]
    for i in idx:
        df_out.loc[i, "country"] = rng.choice(variants)
        
    return df_out, df.loc[idx, "record_id"].tolist()

def inject_unit_mix(df: pd.DataFrame, frac: float = 0.2, seed: int = 0, declare_unit: bool = True):
    """Một phần dòng ghi yield theo kg/ha thay vì t/ha.

    `declare_unit=True` kèm theo cột `yield_unit` như bản xuất khảo sát thật thường có:
    đó là đường P02 quy đổi được an toàn. Đặt False để mô phỏng trường hợp không có
    thông tin đơn vị — khi đó P02 không quy đổi và P04 phải bắt được là nghi lỗi đơn vị.
    """
    rng = np.random.default_rng(seed)
    n_change = int(len(df) * frac)
    if n_change == 0:
        return df.copy(), []

    df_out = df.copy()
    idx = rng.choice(df.index, size=n_change, replace=False)

    df_out.loc[idx, "yield_t_ha"] = df_out.loc[idx, "yield_t_ha"] * 1000.0
    if declare_unit:
        df_out["yield_unit"] = "t/ha"
        df_out.loc[idx, "yield_unit"] = "kg/ha"
    return df_out, df.loc[idx, "record_id"].tolist()

def inject_duplicates(df: pd.DataFrame, n_exact: int = 5, n_partial: int = 3, n_conflict: int = 2, seed: int = 0):
    rng = np.random.default_rng(seed)
    df_out = df.copy()
    
    idx_to_dup = rng.choice(df.index, size=n_exact + n_partial + n_conflict, replace=False)
    
    exact_idx = idx_to_dup[:n_exact]
    partial_idx = idx_to_dup[n_exact:n_exact+n_partial]
    conflict_idx = idx_to_dup[n_exact+n_partial:]
    
    exact_dups = df_out.loc[exact_idx].copy()
    
    partial_dups = df_out.loc[partial_idx].copy()
    partial_dups["noise_1"] = partial_dups["noise_1"] + 1.0
    
    conflict_dups = df_out.loc[conflict_idx].copy()
    conflict_dups["cover_crop"] = ~conflict_dups["cover_crop"]
    
    df_out = pd.concat([df_out, exact_dups, partial_dups, conflict_dups], ignore_index=True)
    truth = df.loc[idx_to_dup, "record_id"].tolist()
    
    return df_out, truth

def inject_outliers(df: pd.DataFrame, n: int = 5, factor: float = 10.0, seed: int = 0):
    rng = np.random.default_rng(seed)
    df_out = df.copy()
    
    idx = rng.choice(df.index, size=n, replace=False)
    df_out.loc[idx, "yield_t_ha"] = df_out.loc[idx, "yield_t_ha"] * factor
    
    return df_out, df.loc[idx, "record_id"].tolist()

def inject_missing(df: pd.DataFrame, col_fracs: dict, seed: int = 0):
    rng = np.random.default_rng(seed)
    df_out = df.copy()
    truth = []
    
    for col, frac in col_fracs.items():
        n_change = int(len(df) * frac)
        if n_change > 0:
            idx = rng.choice(df.index, size=n_change, replace=False)
            df_out.loc[idx, col] = np.nan
            truth.extend(df.loc[idx, "record_id"].tolist())
            
    return df_out, list(set(truth))

def inject_schema_errors(df: pd.DataFrame, n: int = 5, seed: int = 0):
    rng = np.random.default_rng(seed)
    df_out = df.copy()
    
    idx = rng.choice(df.index, size=n, replace=False)
    # str into numeric
    df_out["temp_longterm_c"] = df_out["temp_longterm_c"].astype(object)
    df_out.loc[idx[0], "temp_longterm_c"] = "abc"
    # out of range
    df_out.loc[idx[1], "yield_t_ha"] = -10.0
    # empty record id
    df_out.loc[idx[2], "record_id"] = ""
    # Hạng mục lạ: đặt ở cột KHÔNG thuộc nhóm "không được đoán".
    # `country` và `cover_crop` có chính sách raise (xem configs/preprocess.yaml), nên
    # nhét rác vào đó sẽ chặn cả chuỗi — đúng thiết kế, nhưng không phải thứ ta muốn
    # mô phỏng ở khung dữ liệu bẩn dùng chung. Test riêng của P02 kiểm tra chính sách raise đó.
    if len(idx) > 3:
        df_out["contract"] = df_out["contract"].astype(object)
        df_out.loc[idx[3], "contract"] = "invalid_cat"
    if len(idx) > 4:
        df_out["irrigation"] = df_out["irrigation"].astype(object)
        df_out.loc[idx[4], "irrigation"] = np.nan
        
    return df_out, df.loc[idx, "record_id"].tolist()

def inject_treatment_versions(df: pd.DataFrame, seed: int = 0):
    # This just means ensuring we have valid treatment version cells for P05 tests
    # make_clean_frame already does this.
    return df.copy(), []

def make_dirty_frame(n: int = 300, seed: int = 0):
    df = make_clean_frame(n, seed)
    truth_all = {}
    
    df, t = inject_country_variants(df, frac=0.05, seed=seed)
    truth_all["country_variants"] = t
    
    df, t = inject_unit_mix(df, frac=0.05, seed=seed+1)
    truth_all["unit_mix"] = t
    
    df, t = inject_duplicates(df, n_exact=2, n_partial=2, n_conflict=2, seed=seed+2)
    truth_all["duplicates"] = t
    
    df, t = inject_outliers(df, n=3, factor=15.0, seed=seed+3)
    truth_all["outliers"] = t
    
    df, t = inject_missing(df, {"experience_yr": 0.1, "yield_t_ha": 0.05}, seed=seed+4)
    truth_all["missing"] = t
    
    df, t = inject_schema_errors(df, n=5, seed=seed+5)
    truth_all["schema_errors"] = t
    
    return df, truth_all

