"""Sinh src/content/param_guide.json: mỗi tham số nhận giá trị nào, mỗi giá trị xử lý ra sao.

Chạy: python3 scripts/build_param_guide.py src/mock/params.json src/content/param_guide.json
(sửa code P0x thì sửa nội dung ở đây rồi chạy lại; script dừng nếu thiếu tham số hoặc lệch danh sách allowed).

Nội dung đối chiếu trực tiếp với src/ra_causal/preprocess/p0*.py (không theo spec):
giá trị nào code chưa có nhánh xử lý thì ghi implemented=False và nói rõ hiện hành xử thế nào.
Tag: stop (dừng pipeline) · drop (bỏ dòng) · modify (sửa giá trị) · flag (gắn cờ, giữ dòng)
     · cols (thêm/bỏ cột) · select (đổi tập cột được xét / tập L) · report (chỉ báo cáo)
"""
import json, sys

def E(value, label, effect, tags, implemented=True):
    return {"value": value, "label": label, "effect": effect, "tags": tags, "implemented": implemented}

G = {}

G["P01"] = {
  "on_error": {"kind": "enum", "ask": "Dòng có ô không ép được về đúng kiểu thì làm gì?",
    "options": [
      E("quarantine", "Cách ly dòng", "Dòng lỗi bị tách sang artifact quarantine và không đi tiếp vào P02.", ["drop"]),
      E("flag", "Giữ, gắn cờ", "Dòng vẫn đi tiếp; cột flag__p01__schema_error = True để lọc về sau.", ["flag"]),
      E("raise", "Dừng pipeline", "Chỉ cần một dòng lỗi là dừng với P01.SCHEMA_ERROR.", ["stop"]),
    ],
    "note": "Dòng có record_id rỗng luôn bị cách ly, bất kể chọn giá trị nào."},
  "dtype_coercion": {"kind": "enum", "ask": "Ép kiểu dữ liệu theo schema chặt đến đâu?",
    "options": [
      E("permissive", "Ép mềm", "Thử ép từng ô; ô hỏng thành trống và dòng đó tính là lỗi (xử lý theo on_error). Cột nhị phân/hạng mục còn ghi bằng chữ được để nguyên cho P02 ánh xạ.", ["modify"]),
      E("strict", "Ép cứng", "Một cột không ép được là dừng ngay với P01.COERCE_FAILED.", ["stop"]),
    ]},
  "out_of_range": {"kind": "enum", "ask": "Giá trị nằm ngoài miền khai trong schema thì làm gì?",
    "options": [
      E("flag", "Chỉ gắn cờ", "Giữ nguyên giá trị, thêm cột flag__p01__out_of_range__<cột>. Để P02 (lỗi đơn vị) và P04 (cực trị) quyết định.", ["flag"]),
      E("to_na", "Xóa thành ô trống", "Ô ngoài miền thành trống, kèm cờ. P06 sẽ coi là dữ liệu thiếu.", ["modify", "flag"]),
      E("clip", "Kéo về biên", "Giá trị bị cắt về min/max của schema, kèm cờ. Giá trị ghi sai đơn vị sẽ bị kéo về biên thay vì được P02 quy đổi.", ["modify", "flag"]),
      E("raise", "Dừng pipeline", "Có giá trị ngoài miền là dừng với P01.OUT_OF_RANGE.", ["stop"]),
    ]},
  "unknown_columns": {"kind": "enum", "ask": "Cột không có trong schema thì làm gì?",
    "options": [
      E("warn_keep", "Giữ, cảnh báo", "Cột được giữ nguyên, báo P01.UNKNOWN_COLUMN. P07 sau đó coi cột này là không rõ thời điểm đo.", ["report"]),
      E("drop", "Bỏ cột", "Cột lạ bị xóa khỏi dữ liệu ngay tại P01.", ["cols"]),
      E("raise", "Dừng pipeline", "Có cột lạ là dừng với P01.UNKNOWN_COLUMN.", ["stop"]),
    ],
    "note": "Cột bắt đầu bằng noise_ không bị tính là cột lạ."},
  "duplicate_key_action": {"kind": "enum", "ask": "record_id bị trùng thì làm gì?",
    "options": [
      E("defer_to_p03", "Để P03 xử lý", "Chỉ ghi nhận P01.DUPLICATE_KEY_SEEN, không bỏ dòng nào.", ["report"]),
      E("raise", "Dừng pipeline", "Có record_id trùng là dừng ngay.", ["stop"]),
    ]},
  "required_id_columns": {"kind": "list", "ask": "Cột nào là mã định danh bắt buộc?",
    "explain": "Dòng trống ở bất kỳ cột nào trong danh sách luôn bị cách ly (P01.BAD_RECORD_ID)."},
}

G["P02"] = {
  "string_normalize": {"kind": "fields", "ask": "Chuẩn hóa chuỗi thế nào trước khi so khớp?",
    "fields": {
      "trim": "Cắt khoảng trắng hai đầu. Chỉ có tác dụng khi collapse_spaces = false (collapse_spaces đã cắt luôn hai đầu).",
      "lower": "Hạ chữ thường: 'Yes' và 'yes' khớp cùng một alias.",
      "strip_accents": "Bỏ dấu tiếng Việt: 'Có' khớp 'co'.",
      "collapse_spaces": "Gộp nhiều khoảng trắng thành một.",
    },
    "note": "Chỉ dùng để SO KHỚP ở cột hạng mục/nhị phân; giá trị ghi ra vẫn là mã chuẩn. Cột mã định danh chỉ được cắt khoảng trắng, không hạ hoa hay bỏ dấu."},
  "category_mapping_mode": {"kind": "enum", "ask": "Ánh xạ giá trị hạng mục về mã chuẩn bằng cách nào?",
    "options": [
      E("explicit", "Chỉ bảng alias", "Chỉ đổi khi giá trị khớp mã chuẩn hoặc có trong bảng alias (raw_assumed.yaml). Còn lại xử lý theo unmapped_action.", ["modify"]),
      E("fuzzy_suggest", "Gợi ý gần đúng", "Như explicit, và ghi thêm vào báo cáo các cặp gần giống (độ giống ≥ fuzzy_threshold). Không tự đổi.", ["modify", "report"]),
      E("fuzzy_auto", "Tự đổi gần đúng", "Giá trị gần giống một mã chuẩn (độ giống ≥ fuzzy_threshold) bị đổi luôn sang mã đó. Có thể ghép nhầm hai mã tên gần giống.", ["modify"]),
    ]},
  "fuzzy_threshold": {"kind": "number", "ask": "Giống đến đâu thì coi là cùng một mã?",
    "up": "Khắt khe hơn: ít cặp được ghép, nhiều giá trị rơi vào unmapped.",
    "down": "Dễ dãi hơn: ghép được nhiều hơn nhưng dễ ghép nhầm.",
    "when": {"param": "category_mapping_mode", "in": ["fuzzy_suggest", "fuzzy_auto"]}, "when_text": "category_mapping_mode là fuzzy_suggest hoặc fuzzy_auto"},
  "unmapped_action": {"kind": "enum_map", "ask": "Giá trị không ánh xạ được thì làm gì?",
    "options": [
      E("to_na", "Thành ô trống", "Ô đó thành trống và dòng được gắn cờ flag__p02__unmapped__<cột>.", ["modify", "flag"]),
      E("keep_raw", "Giữ giá trị thô", "Giữ nguyên chữ gốc, vẫn gắn cờ flag__p02__unmapped__<cột>.", ["flag"]),
      E("raise", "Dừng pipeline", "Gom hết giá trị lạ của mọi cột rồi dừng một lần, kèm danh sách để bổ sung alias.", ["stop"]),
    ],
    "map_explain": "default áp cho mọi cột; overrides ghi đè cho từng cột.",
    "note": "Alias khai null (vd 'Partial': null) nghĩa là cố ý để trống: không bị raise chặn, chỉ thành ô trống kèm cờ flag__p02__intentional_na__<cột>."},
  "unit_policy": {"kind": "enum", "ask": "Xác định đơn vị năng suất (kg/ha hay t/ha) bằng cách nào?",
    "options": [
      E("unit_column", "Theo cột đơn vị", "Dòng có cột đơn vị chứa 'kg' được chia 1000, cột đơn vị đổi thành t/ha. Không có cột đơn vị thì theo unit_fallback.", ["modify"]),
      E("source_declaration", "Theo khai báo nguồn", "Nếu raw_assumed.yaml khai yield = kg/ha thì chia cả cột cho 1000; không khai thì giữ nguyên.", ["modify"]),
      E("threshold_inference", "Suy theo ngưỡng", "Chỉ dòng có yield > unit_threshold bị chia 1000 và gắn cờ flag__p02__unit_inferred. Ruộng năng suất thật sự cao có thể bị chia nhầm.", ["modify", "flag"]),
      E("none", "Không quy đổi", "Giữ nguyên số. Vẫn cảnh báo P02.MIXED_UNIT_SUSPECTED nếu thấy hai cụm giá trị.", ["report"]),
    ]},
  "unit_column_name": {"kind": "string", "ask": "Cột nào ghi đơn vị năng suất?",
    "explain": "Tên cột trong dữ liệu thô chứa đơn vị (vd 'kg/ha', 't/ha').",
    "when": {"param": "unit_policy", "in": ["unit_column"]}, "when_text": "unit_policy = unit_column"},
  "unit_fallback": {"kind": "enum", "ask": "Dữ liệu không có cột đơn vị thì làm gì?",
    "options": [
      E("source_declaration", "Theo khai báo nguồn", "Giống unit_policy = source_declaration.", ["modify"]),
      E("none", "Không quy đổi", "Giữ nguyên số; lỗi đơn vị (nếu có) sẽ lộ ra ở P04.", ["report"]),
      E("raise", "Dừng pipeline", "Dừng với P02.UNIT_POLICY_UNAVAILABLE.", ["stop"]),
    ],
    "when": {"param": "unit_policy", "in": ["unit_column"]}, "when_text": "unit_policy = unit_column"},
  "unit_threshold": {"kind": "number", "ask": "Trên mức nào thì coi yield đang ghi kg/ha?",
    "up": "Ít dòng bị quy đổi; giá trị kg/ha nhỏ có thể lọt qua.",
    "down": "Nhiều dòng bị quy đổi; dễ chia nhầm ruộng năng suất cao.",
    "when": {"param": "unit_policy", "in": ["threshold_inference"]}, "when_text": "unit_policy = threshold_inference"},
  "decimal_comma": {"kind": "enum", "ask": "Có đọc '3,8' thành 3.8 không?",
    "options": [
      E("auto", "Tự nhận", "Chỉ đổi dấu phẩy thành dấu chấm ở cột số khi hơn nửa giá trị có dạng 3,8.", ["modify"]),
      E(True, "Luôn đổi", "Mọi cột số còn ở dạng chữ đều đổi dấu phẩy thành dấu chấm.", ["modify"]),
      E(False, "Không đổi", "Giữ nguyên chuỗi có dấu phẩy.", []),
    ]},
  "category_levels_source": {"kind": "enum", "ask": "Danh sách mức hợp lệ của cột hạng mục lấy từ đâu?",
    "options": [
      E("schema", "Từ schema", "Mức hợp lệ cố định theo schema: giống nhau giữa các lần chạy.", []),
      E("data", "Từ dữ liệu", "Mọi giá trị đang có đều thành hợp lệ (không còn giá trị lạ để bắt); cảnh báo P02.CATEGORY_LEVELS_FROM_DATA vì tập mức đổi theo từng file.", ["report"]),
    ]},
}

G["P03"] = {
  "key": {"kind": "list", "ask": "Cột nào xác định một ruộng-năm?",
    "explain": "Các dòng trùng mọi cột này là một nhóm trùng. Dòng thiếu giá trị ở khóa không được xét (P03.NULL_KEY)."},
  "resolve": {"kind": "enum", "ask": "Nhóm trùng (không mâu thuẫn) giữ lại dòng nào?",
    "options": [
      E("keep_most_complete", "Giữ dòng đầy đủ nhất", "Giữ dòng ít ô trống nhất (hòa thì lấy record_id nhỏ nhất), bỏ phần còn lại.", ["drop"]),
      E("keep_first", "Giữ dòng đầu", "Giữ dòng xuất hiện đầu tiên trong file.", ["drop"]),
      E("keep_last", "Giữ dòng mới nhất", "Giữ dòng có timestamp_column lớn nhất; chưa đặt timestamp_column thì lỗi cấu hình.", ["drop"]),
      E("aggregate", "Gộp thành một dòng", "Gộp theo aggregate_rules (số: trung bình, hạng mục: mode, nhị phân: max); dòng gộp có cờ flag__p03__aggregated.", ["modify", "drop", "flag"]),
      E("flag_only", "Chỉ gắn cờ", "Giữ mọi dòng; chỉ có cờ flag__p03__duplicate và mã nhóm dup_group_id.", ["flag"]),
    ],
    "note": "Mọi nhóm trùng đều được gắn flag__p03__duplicate và dup_group_id. Nhóm mâu thuẫn xử lý theo conflict_action trước."},
  "timestamp_column": {"kind": "string", "ask": "Cột thời gian để biết dòng nào mới hơn?",
    "explain": "Bắt buộc khi resolve = keep_last.",
    "when": {"param": "resolve", "in": ["keep_last"]}, "when_text": "resolve = keep_last"},
  "conflict_action": {"kind": "enum", "ask": "Nhóm trùng nhưng khác nhau ở cột quan trọng thì làm gì?",
    "options": [
      E("review_list", "Đưa vào danh sách rà soát", "Giữ nguyên mọi dòng của nhóm (gắn cờ flag__p03__conflict), xuất artifact review_list để người xem quyết định.", ["flag", "report"]),
      E("drop_group", "Bỏ cả nhóm", "Mọi dòng của nhóm mâu thuẫn bị loại.", ["drop"]),
      E("resolve", "Xử lý như trùng thường", "Áp luôn quy tắc resolve lên nhóm mâu thuẫn, tức là chọn một dòng dù các dòng khai khác nhau.", ["drop"]),
    ]},
  "critical_columns": {"kind": "list", "ask": "Khác nhau ở cột nào thì là mâu thuẫn?",
    "explain": "Cùng khóa mà khác nhau ở một trong các cột này → nhóm mâu thuẫn (P03.CONFLICTING_DUPLICATES). Chỉ khác ở cột khác → trùng một phần."},
  "numeric_tolerance": {"kind": "number", "ask": "Hai số chênh bao nhiêu thì vẫn coi là bằng nhau?",
    "up": "Nhiều nhóm được coi là trùng khớp hoàn toàn hơn.",
    "down": "Sai số làm tròn nhỏ cũng bị tính là khác nhau."},
  "aggregate_rules": {"kind": "fields", "ask": "Gộp từng loại cột bằng phép gì?",
    "fields": {
      "numeric": "mean: lấy trung bình. Giá trị khác hiện không có tác dụng (cột giữ giá trị của dòng đầy đủ nhất).",
      "categorical": "mode: lấy giá trị hay gặp nhất.",
      "boolean": "max: có ít nhất một dòng True thì là True.",
    },
    "when": {"param": "resolve", "in": ["aggregate"]}, "when_text": "resolve = aggregate"},
}

G["P04"] = {
  "columns": {"kind": "list", "ask": "Kiểm tra giá trị bất thường ở cột nào?",
    "explain": "Chỉ cột số; cột không phải số bị bỏ qua (P04.NON_NUMERIC_COLUMN_SKIPPED)."},
  "method": {"kind": "enum", "ask": "Phát hiện giá trị bất thường bằng cách nào?",
    "options": [
      E("domain_range", "Miền hợp lệ", "Ngoài [min, max] khai trong schema là bất thường. Không tính theo nhóm.", ["flag"]),
      E("iqr", "IQR", "Ngoài [Q1 − k·IQR, Q3 + k·IQR], tính riêng trong từng nhóm group_by.", ["flag"]),
      E("robust_z", "z bền (MAD)", "|0.6745·(x − trung vị) / MAD| > ngưỡng, tính trong từng nhóm. Nhóm có MAD = 0 bị bỏ qua (P04.ZERO_MAD).", ["flag"]),
      E("percentile", "Phân vị", "Ngoài cặp percentile_bounds trong từng nhóm. Luôn gắn cờ khoảng 1% dữ liệu dù không có gì bất thường.", ["flag"]),
    ],
    "note": "method chỉ quyết định PHÁT HIỆN. Sửa hay không là do action. method_by_column ghi đè method cho từng cột."},
  "method_by_column": {"kind": "map", "ask": "Cột nào dùng phương pháp riêng?",
    "explain": "Ghi đè method cho từng cột. Mặc định yield_t_ha và field_size_ha dùng domain_range vì có miền hợp lệ rõ ràng."},
  "iqr_k": {"kind": "number", "ask": "Hệ số k của IQR",
    "up": "Hàng rào rộng hơn: ít giá trị bị gắn cờ.", "down": "Hàng rào hẹp hơn: nhiều giá trị bị gắn cờ (Tukey dùng 1.5; 3 là 'rất xa').",
    "when": {"any": [{"param": "method", "in": ["iqr"]}, {"valuesOf": "method_by_column", "in": ["iqr"]}]}, "when_text": "có cột dùng iqr"},
  "robust_z_threshold": {"kind": "number", "ask": "Ngưỡng z bền",
    "up": "Ít giá trị bị gắn cờ.", "down": "Nhiều giá trị bị gắn cờ. 3.5 là mức Iglewicz & Hoaglin đề xuất.",
    "when": {"any": [{"param": "method", "in": ["robust_z"]}, {"valuesOf": "method_by_column", "in": ["robust_z"]}]}, "when_text": "có cột dùng robust_z"},
  "percentile_bounds": {"kind": "list", "ask": "Cặp phân vị dưới/trên",
    "explain": "Dùng làm ngưỡng khi method = percentile, và làm điểm kéo về khi winsorize_at = percentile."},
  "group_by": {"kind": "list", "ask": "Tính ngưỡng riêng theo nhóm nào?",
    "explain": "Mỗi nhóm có ngưỡng riêng (mặc định theo nước), vì năng suất bình thường khác nhau giữa các nước. Không áp cho domain_range."},
  "min_group_size": {"kind": "number", "ask": "Nhóm nhỏ nhất được tính ngưỡng riêng",
    "up": "Nhiều nhóm phải dùng ngưỡng toàn cục hơn (P04.SMALL_GROUP).", "down": "Nhóm nhỏ cũng có ngưỡng riêng, nhưng ngưỡng đó kém ổn định."},
  "action": {"kind": "enum", "ask": "Giá trị bất thường thì xử lý thế nào?",
    "options": [
      E("flag_only", "Chỉ gắn cờ", "Không sửa giá trị gốc; chỉ có cột cờ.", ["flag"]),
      E("winsorize", "Kéo về ngưỡng", "Giá trị vượt ngưỡng bị thay bằng ngưỡng (vị trí theo winsorize_at).", ["modify", "flag"]),
      E("to_na", "Xóa thành ô trống", "Ô bất thường thành trống; P06 coi là dữ liệu thiếu và có thể điền lại.", ["modify", "flag"]),
      E("drop_row", "Bỏ dòng", "Bỏ mọi dòng có ít nhất một cột bất thường. max_flag_rate vẫn được kiểm tra trước khi bỏ.", ["drop"]),
      E("log_transform", "Biến đổi log", "Chưa có trong code: hiện hành xử như flag_only.", [], False),
      E("keep_as_feature", "Giữ làm đặc trưng", "Chưa có trong code: hiện hành xử như flag_only.", [], False),
    ],
    "note": "Lựa chọn nào cũng tạo cờ flag__p04__outlier__<cột> và flag__p04__any."},
  "parallel_actions": {"kind": "multi", "ask": "Sinh thêm cột phiên bản đã xử lý để so sánh?",
    "options": [
      E("winsorize", "Thêm cột winsorize", "Thêm cột <cột>__winsorized (giá trị kéo về ngưỡng), cột gốc giữ nguyên. Chỉ tạo khi cột có giá trị bị gắn cờ.", ["cols"]),
      E("log_transform", "Thêm cột log", "Chưa có trong code: không tạo cột nào.", [], False),
    ]},
  "winsorize_at": {"kind": "enum", "ask": "Kéo về điểm nào?",
    "options": [
      E("bound", "Tại ngưỡng phát hiện", "Kéo về đúng ngưỡng đã dùng để gắn cờ.", ["modify"]),
      E("percentile", "Tại phân vị", "Kéo về cặp percentile_bounds của nhóm.", ["modify"]),
    ],
    "when": {"any": [{"param": "action", "in": ["winsorize"]}, {"param": "parallel_actions", "contains": "winsorize"}]}, "when_text": "action hoặc parallel_actions có winsorize"},
  "max_flag_rate": {"kind": "number", "ask": "Gắn cờ quá bao nhiêu phần dữ liệu thì chặn?",
    "up": "Dễ dãi hơn: có thể để lọt lỗi đơn vị chưa quy đổi.",
    "down": "Chặn sớm hơn (P04.MAX_FLAG_RATE_EXCEEDED): gắn cờ nhiều thường là dấu hiệu lỗi đơn vị, không phải cực trị thật.",
    "tags": ["stop"]},
  "unit_error_detection": {"kind": "enum", "ask": "Có thử nhận ra lỗi đơn vị không?",
    "options": [
      E(True, "Bật", "Chia giá trị bất thường cho từng hệ số trong unit_error_factors; rơi vào miền hợp lệ thì gắn cờ flag__p04__suspected_unit_error__<cột>.", ["flag"]),
      E(False, "Tắt", "Không thử.", []),
    ]},
  "unit_error_factors": {"kind": "list", "ask": "Thử những hệ số quy đổi nào?",
    "explain": "1000 ứng với kg/ha ↔ t/ha; 10 và 100 ứng với lỗi dời dấu phẩy.",
    "when": {"param": "unit_error_detection", "in": [True]}, "when_text": "unit_error_detection = true"},
}

G["P05"] = {
  "mode": {"kind": "enum", "ask": "Định nghĩa biến can thiệp A theo kiểu nào?",
    "options": [
      E("binary_threshold", "Nhị phân theo ngưỡng", "A = 1 khi số tháng trồng cây che phủ ≥ threshold_months, ngược lại A = 0.", ["modify"]),
      E("multi_level", "Nhiều mức", "Chưa có trong code: vẫn chạy như binary_threshold.", [], False),
      E("per_version", "Theo phiên bản", "Chưa có trong code: vẫn chạy như binary_threshold.", [], False),
      E("continuous", "Liên tục", "Chưa có trong code: vẫn chạy như binary_threshold.", [], False),
    ]},
  "source_column": {"kind": "string", "ask": "Tính A từ cột nào?",
    "explain": "Cột này thiếu hoặc trống hoàn toàn thì dùng cột cover_crop có sẵn (P05.FALLBACK_TO_BINARY)."},
  "threshold_months": {"kind": "number", "ask": "Trồng tối thiểu bao nhiêu tháng thì A = 1?",
    "up": "Ít ruộng được tính là có áp dụng.", "down": "Nhiều ruộng được tính là có áp dụng."},
  "threshold_sensitivity": {"kind": "list", "ask": "Thử thêm những ngưỡng nào?",
    "explain": "Mỗi ngưỡng sinh một cột cover_crop__thr<k> để phân tích độ nhạy. Báo P05.THRESHOLD_SENSITIVITY khi có dòng đổi nhóm.",
    "tags": ["cols"]},
  "partial_action": {"kind": "enum", "ask": "Dòng ghi 'Partial' tính là gì?",
    "options": [
      E("to_na", "Để trống", "A của dòng Partial là trống.", ["modify", "flag"]),
      E("treated", "Có áp dụng", "A = 1.", ["modify", "flag"]),
      E("control", "Không áp dụng", "A = 0.", ["modify", "flag"]),
      E("own_level", "Mức riêng", "Cần A nhiều mức. Với A nhị phân hiện tại: để trống như to_na và báo thêm P05.OWN_LEVEL_NOT_BINARY.", ["modify", "flag"]),
    ],
    "note": "Không lựa chọn nào bỏ dòng: mọi dòng Partial được gắn cờ flag__p05__partial và xuất artifact partial_review."},
  "type_grouping": {"kind": "enum", "ask": "Gộp loại cây che phủ thế nào?",
    "options": [
      E("group", "Gộp nhóm", "Dự kiến gộp loại hiếm vào nhóm lớn. Hiện chỉ chép cover_crop_type sang cover_crop_type__grouped.", ["cols"], False),
      E("all", "Gộp tất cả", "Chưa có trong code: kết quả giống group.", ["cols"], False),
      E("keep", "Giữ nguyên", "Chưa có trong code: kết quả giống group.", ["cols"], False),
    ],
    "note": "Cả ba giá trị hiện cho cùng kết quả vì dữ liệu đã ở 4 nhóm (none/legume/grass/mixed)."},
  "min_cell": {"kind": "number", "ask": "Một loại cây che phủ cần ít nhất bao nhiêu dòng?",
    "up": "Cảnh báo P05.SMALL_VERSION_CELL cho nhiều loại hơn.", "down": "Ít cảnh báo hơn."},
  "write_treatment_column": {"kind": "enum", "ask": "Có ghi đè cột cover_crop không?",
    "options": [
      E(True, "Ghi đè", "cover_crop thành A theo định nghĩa mới; giá trị gốc lưu ở cover_crop__raw.", ["modify", "cols"]),
      E(False, "Không ghi đè", "cover_crop giữ nguyên; chỉ sinh các cột độ nhạy.", ["cols"]),
    ]},
}

G["P06"] = {
  "scope": {"kind": "enum", "ask": "Báo cáo dữ liệu thiếu trên những cột nào?",
    "options": [
      E("adjustment_set_plus_ay", "Chỉ L + A + Y", "Báo cáo tỷ lệ thiếu và kiểu thiếu trên tập điều chỉnh L, can thiệp A và kết quả Y.", ["report"]),
      E("all_columns", "Mọi cột", "Báo cáo trên mọi cột.", ["report"]),
    ],
    "note": "Điền thiếu luôn chỉ áp cho cột trong L; scope chỉ đổi phạm vi báo cáo và cảnh báo."},
  "outcome_missing": {"kind": "enum", "ask": "Dòng thiếu Y thì làm gì?",
    "options": [
      E("ipcw_flag", "Giữ dòng, tạo cờ quan sát", "Giữ mọi dòng; giai đoạn ước lượng dùng cột c_outcome_observed để tính trọng số IPCW.", ["flag"]),
      E("complete_case", "Bỏ dòng thiếu Y", "Loại dòng không có Y.", ["drop"]),
      E("both", "Cờ và bỏ dòng", "Code hiện tại cho kết quả giống complete_case.", ["drop"]),
    ],
    "note": "Cột c_outcome_observed luôn được tạo."},
  "covariate_missing": {"kind": "enum", "ask": "Biến trong L bị thiếu thì làm gì?",
    "options": [
      E("median_indicator", "Điền + cột cờ", "Số: điền trung vị; hạng mục: điền giá trị hay gặp nhất, tính theo nhóm impute_group_by. Thêm cờ flag__p06__imputed__<cột>.", ["modify", "flag"]),
      E("drop_row", "Bỏ dòng", "Loại dòng thiếu bất kỳ biến nào trong L.", ["drop"]),
      E("category_missing", "Mức 'Missing'", "Chưa có trong code: ô thiếu giữ nguyên trống.", [], False),
    ]},
  "impute_group_by": {"kind": "list", "ask": "Điền giá trị theo nhóm nào?",
    "explain": "Mỗi nhóm có trung vị/mode riêng (mặc định theo nước)."},
  "min_group_size": {"kind": "number", "ask": "Nhóm nhỏ nhất được điền bằng giá trị riêng",
    "up": "Nhiều nhóm dùng giá trị toàn cục hơn (P06.SMALL_GROUP).", "down": "Nhóm nhỏ cũng dùng trung vị riêng, nhưng kém ổn định."},
  "keep_indicator": {"kind": "enum", "ask": "Có giữ cột cờ đánh dấu ô đã điền không?",
    "options": [
      E(True, "Giữ", "Giữ cột flag__p06__imputed__<cột>; mô hình sau có thể dùng cờ này.", ["cols"]),
      E(False, "Bỏ", "Xóa cột cờ sau khi điền: không còn biết ô nào là giá trị điền.", ["cols"]),
    ],
    "when": {"param": "covariate_missing", "in": ["median_indicator"]}, "when_text": "covariate_missing = median_indicator"},
  "max_missing_col": {"kind": "number", "ask": "Cột thiếu quá bao nhiêu thì loại khỏi L?",
    "up": "Giữ lại nhiều cột hơn nhưng phải điền nhiều hơn.", "down": "Loại nhiều cột hơn khỏi L (P06.COLUMN_DROPPED_HIGH_MISSING).",
    "tags": ["select"]},
  "mechanism_check": {"kind": "multi", "ask": "Kiểm tra cơ chế thiếu bằng cách nào?",
    "options": [
      E("describe", "Mô tả", "Thêm P06.MISSING_SUMMARY: tỷ lệ thiếu theo cột × nước × A và 10 kiểu thiếu hay gặp.", ["report"]),
      E("regress", "Hồi quy", "Hồi quy logistic cờ quan sát Y theo L, báo 10 biến dự báo mạnh nhất (P06.MECHANISM_REGRESS). Chỉ để xem, không đổi dữ liệu.", ["report"]),
    ]},
  "diff_warn_threshold": {"kind": "number", "ask": "Chênh tỷ lệ thiếu giữa hai nhóm A bao nhiêu thì cảnh báo?",
    "up": "Ít cảnh báo P06.MISSING_DIFFERS_BY_TREATMENT hơn.", "down": "Nhạy hơn với thiếu dữ liệu lệch theo A."},
}

G["P07"] = {
  "time_source": {"kind": "enum", "ask": "Biết một cột đo trước hay sau can thiệp nhờ đâu?",
    "options": [
      E("schema", "Theo schema", "Dùng measured_at khai trong schema.", ["select"]),
      E("name_suffix", "Theo hậu tố _post", "Cột có tên kết thúc bằng _post là đo sau, còn lại coi là đo trước. Bỏ qua schema.", ["select"]),
      E("both", "Cả hai, ưu tiên schema", "Quyết định theo schema; báo P07.TIME_SOURCE_CONFLICT khi hai nguồn lệch nhau.", ["select", "report"]),
    ]},
  "unknown_action": {"kind": "enum", "ask": "Cột không rõ thời điểm đo thì làm gì?",
    "options": [
      E("exclude", "Loại khỏi danh sách hợp lệ", "Cột không được xét làm biến điều chỉnh.", ["select"]),
      E("include", "Cho vào", "Cột được xét làm biến điều chỉnh. Có thể để lọt biến đo sau can thiệp.", ["select"]),
      E("raise", "Dừng pipeline", "Dừng với P07.UNKNOWN_TIMING.", ["stop"]),
    ],
    "note": "Áp cho cột không có trong schema và cột có measured_at không rõ."},
  "strict": {"kind": "enum", "ask": "Biến đo sau can thiệp lọt qua thì dừng hay chỉ báo?",
    "options": [
      E(True, "Dừng", "Nếu soil_om_post_pct, weed_pressure hoặc in_program không bị chặn thì dừng với P07.POST_VAR_NOT_BLOCKED.", ["stop"]),
      E(False, "Chỉ báo lỗi", "Ghi P07.POST_VAR_NOT_BLOCKED mức error rồi chạy tiếp.", ["report"]),
    ]},
  "allow_post_precision_vars": {"kind": "enum", "ask": "Có cho biến đo sau nhưng không chịu tác động của A không?",
    "options": [
      E(True, "Cho phép", "Biến có affected_by_treatment = false (vd season_rain_mm) được xét làm biến điều chỉnh, kèm cảnh báo.", ["select"]),
      E(False, "Chặn", "Mọi biến đo sau can thiệp đều bị chặn.", ["select"]),
    ]},
  "allow_post_as_secondary_outcome": {"kind": "enum", "ask": "Có giữ Y trong danh sách cột hợp lệ không?",
    "options": [
      E(True, "Giữ", "yield_t_ha nằm trong danh sách hợp lệ (P08 vẫn loại outcome khỏi L).", ["select"]),
      E(False, "Chặn", "yield_t_ha bị đưa vào danh sách chặn và phải bị chặn.", ["select"]),
    ]},
  "diagnostics_on_post_vars": {"kind": "enum", "ask": "Mô tả biến đo sau can thiệp theo nhóm A?",
    "options": [
      E(True, "Bật", "Chưa có trong code: chưa sinh bảng mô tả nào.", [], False),
      E(False, "Tắt", "Không mô tả.", []),
    ]},
}

G["P08"] = {
  "source": {"kind": "enum", "ask": "Chọn biến điều chỉnh L theo nguồn nào?",
    "options": [
      E("schema_roles", "Theo vai trò trong DAG", "Lấy cột có vai trò trong include_roles (và biến chỉ ảnh hưởng Y nếu bật include_precision_vars), trong số cột P07 cho phép.", ["select"]),
      E("manual", "Danh sách tay", "L = manual_list, chỉ giữ cột P07 cho phép.", ["select"]),
      E("data_driven", "Theo dữ liệu", "Dừng với lỗi cấu hình trừ khi allow_data_driven = true. Khi được bật, code hiện chạy như schema_roles và cảnh báo P08.DATA_DRIVEN_USED.", ["stop"], False),
    ]},
  "allow_data_driven": {"kind": "enum", "ask": "Có cho chọn biến theo dữ liệu không?",
    "options": [
      E(False, "Không", "source = data_driven sẽ dừng pipeline.", ["stop"]),
      E(True, "Có", "Cho phép source = data_driven (kèm cảnh báo).", []),
    ]},
  "manual_list": {"kind": "list", "ask": "Danh sách biến khi chọn tay",
    "explain": "Chỉ cột có trong danh sách hợp lệ của P07 mới được giữ.",
    "when": {"param": "source", "in": ["manual"]}, "when_text": "source = manual"},
  "include_roles": {"kind": "list", "ask": "Vai trò nào được đưa vào L?",
    "explain": "confounder: gây nhiễu — ảnh hưởng cả A và Y, phải điều chỉnh."},
  "include_precision_vars": {"kind": "enum", "ask": "Có thêm biến chỉ ảnh hưởng Y không?",
    "options": [
      E(True, "Thêm", "Cột vai trò outcome_predictor được đưa vào L để giảm phương sai ước lượng.", ["select"]),
      E(False, "Không thêm", "L chỉ gồm vai trò trong include_roles.", ["select"]),
    ]},
  "exclude_roles": {"kind": "list", "ask": "Vai trò nào luôn bị loại khỏi L?",
    "explain": "mediator (trung gian), collider (va chạm), instrument (công cụ), noise, outcome, treatment, treatment_version, id. Ngoài ra còn một lưới an toàn: các vai trò cấm lọt vào L là dừng với P08.FORBIDDEN_COLUMN_IN_L."},
  "ambiguous_action": {"kind": "enum", "ask": "Biến vai trò chưa rõ (vd practice RA khác) thì sao?",
    "options": [
      E("both", "Tạo hai biến thể L", "O_as_confounder (có các biến này) và O_as_mediator (không có). L chính dùng bản có.", ["select"]),
      E("include", "Cho vào L", "Coi là confounder.", ["select"]),
      E("exclude", "Loại khỏi L", "Coi là mediator.", ["select"]),
    ]},
  "basis": {"kind": "fields", "ask": "Dạng hàm cho mô hình propensity score (giai đoạn sau)",
    "fields": {
      "continuous": "linear | quadratic | spline: cách đưa biến liên tục vào mô hình.",
      "spline_df": "Bậc tự do khi continuous = spline.",
    },
    "note": "P08 chỉ ghi vào context (ps_basis_spec) cho giai đoạn ước lượng, không đổi dữ liệu."},
  "interactions": {"kind": "list", "ask": "Tương tác cho mô hình propensity score (giai đoạn sau)",
    "explain": "['country', '*'] = country tương tác với mọi biến. Chỉ khai báo, P08 không dùng."},
  "rare_level_action": {"kind": "enum", "ask": "Mức hạng mục hiếm thì làm gì?",
    "options": [
      E("group", "Gộp thành 'other'", "Ở cột hạng mục trong L, mức chiếm ít hơn rare_level_threshold được gộp thành 'other'.", ["modify"]),
      E("keep", "Giữ nguyên", "Không đổi.", []),
      E("drop", "Bỏ", "Chưa có trong code: hiện giữ nguyên như keep.", [], False),
    ]},
  "rare_level_threshold": {"kind": "number", "ask": "Chiếm ít hơn bao nhiêu thì là mức hiếm?",
    "up": "Nhiều mức bị gộp hơn.", "down": "Ít mức bị gộp hơn.",
    "when": {"param": "rare_level_action", "in": ["group"]}, "when_text": "rare_level_action = group"},
  "min_variation": {"kind": "number", "ask": "Phương sai tối thiểu để giữ biến trong L",
    "up": "Loại thêm biến gần như hằng số (P08.ZERO_VARIANCE_DROPPED).", "down": "Chỉ loại biến hằng số tuyệt đối.",
    "tags": ["select"]},
}

G["P09"] = {
  "cluster_key": {"kind": "list", "ask": "Cột nào xác định cụm?",
    "explain": "Nhiều cột thì được nối thành một khóa. Dòng thiếu khóa thành một cụm riêng (P09.MISSING_CLUSTER_KEY). Kết quả ghi vào cột cluster_id.",
    "tags": ["cols"]},
  "fold_strategy": {"kind": "enum", "ask": "Chia fold cho cross-fitting thế nào?",
    "options": [
      E("group_stratified", "Theo cụm, cân A", "Một cụm nằm trọn trong một fold, tỷ lệ A giữa các fold gần nhau. Quá ít cụm hoặc ít mẫu thì tự lùi về group (P09.FALLBACK_TO_GROUP_KFOLD).", ["cols"]),
      E("group", "Theo cụm", "Một cụm nằm trọn trong một fold; không cân A, không dùng seed.", ["cols"]),
      E("random", "Ngẫu nhiên", "Chưa có trong code: hiện chạy như group.", [], False),
    ],
    "note": "Kết quả ghi vào cột fold_id; dòng thiếu A có fold_id = −1."},
  "n_folds": {"kind": "number", "ask": "Số fold",
    "up": "Mỗi lần huấn luyện dùng nhiều dữ liệu hơn, nhưng mỗi fold ít cụm hơn.", "down": "Mỗi fold nhiều cụm hơn, nhưng mỗi lần huấn luyện dùng ít dữ liệu hơn."},
  "seed": {"kind": "number", "ask": "Seed chia fold",
    "explain": "Cố định để chạy lại cho cùng cách chia.",
    "when": {"param": "fold_strategy", "in": ["group_stratified"]}, "when_text": "fold_strategy = group_stratified"},
  "year_handling": {"kind": "enum", "ask": "Xử lý năm ở giai đoạn ước lượng thế nào?",
    "options": [
      E("fixed_effect", "Hiệu ứng cố định", "Dự kiến: đưa năm vào mô hình như biến điều chỉnh.", [], False),
      E("second_cluster", "Cụm thứ hai", "Dự kiến: sai số chuẩn cụm hai chiều (nông hộ × năm).", [], False),
      E("ignore", "Bỏ qua", "Dự kiến: không xử lý riêng năm.", [], False),
    ],
    "note": "Hiện chỉ ghi vào context year_handling cho giai đoạn sau; không ảnh hưởng cách chia fold."},
  "large_cluster_warn": {"kind": "number", "ask": "Một cụm chiếm quá bao nhiêu thì cảnh báo?",
    "up": "Ít cảnh báo P09.LARGE_CLUSTER hơn.", "down": "Nhạy hơn với cụm lớn."},
  "compute_icc": {"kind": "enum", "ask": "Có tính ICC của Y theo cụm không?",
    "options": [
      E(True, "Tính", "Báo P09.ICC_ESTIMATE: phần phương sai Y nằm giữa các cụm (ICC cao → cần tính sai số theo cụm).", ["report"]),
      E(False, "Không tính", "Bỏ qua.", []),
    ]},
}

# Kiểm tra: mọi tham số trong params.json đều có hướng dẫn, và giá trị liệt kê khớp 'allowed'
params = json.load(open(sys.argv[1]))
problems = []
for mid, spec in params.items():
    for key, allowed in spec["allowed"].items():
        g = G.get(mid, {}).get(key)
        if g is None:
            problems.append(f"{mid}.{key}: thiếu hướng dẫn"); continue
        if g["kind"] in ("enum", "enum_map", "multi"):
            vals = [o["value"] for o in g["options"]]
            if allowed == "boolean":
                want = [True, False]
            elif isinstance(allowed, list):
                want = allowed
            elif isinstance(allowed, dict):
                want = allowed.get("default") or allowed.get("array_of")
            else:  # 'array' (vd mechanism_check): không có danh sách cho phép để so
                want = vals
            if sorted(map(str, vals)) != sorted(map(str, want)):
                problems.append(f"{mid}.{key}: {vals} ≠ allowed {want}")
    for key in G.get(mid, {}):
        if key not in spec["defaults"]:
            problems.append(f"{mid}.{key}: thừa (không có trong params.json)")
if problems:
    print("\n".join(problems)); sys.exit(1)
json.dump(G, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
print("ok", sum(len(v) for v in G.values()), "tham số")
