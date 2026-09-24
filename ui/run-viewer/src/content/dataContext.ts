/**
 * Nội dung trang "Bối cảnh dữ liệu".
 *
 * - Nhóm khái niệm + mũi tên: theo DAG v0 trong Atlas_Nhan_qua_RA.html, gán xuống từng cột
 *   của configs/schema/canonical.yaml (cột nào thuộc nút nào).
 * - Cách sinh mock: theo tests/fixtures/make_frames.py (make_dirty_frame, 300 dòng + 6 dòng trùng).
 * - Việc module làm với từng biến: theo code P0x và báo cáo lượt chạy mẫu. Chuỗi {CODE@cột}
 *   được thay bằng `count` của finding tương ứng trong lượt chạy (xem fillCounts).
 */

export type Role = 'conf' | 'trt' | 'out' | 'med' | 'col' | 'prec' | 'instr' | 'unc' | 'unm' | 'tech';

export const ROLE_META: Record<Role, { label: string; color: string }> = {
  conf: { label: 'Confounder', color: 'conf' },
  trt: { label: 'Can thiệp A', color: 'accent' },
  out: { label: 'Kết quả Y', color: 'info' },
  med: { label: 'Mediator', color: 'teal' },
  col: { label: 'Collider', color: 'failed' },
  prec: { label: 'Chỉ ảnh hưởng Y', color: 'prec' },
  instr: { label: 'Instrument', color: 'instr' },
  unc: { label: 'Vai trò chưa rõ', color: 'warn' },
  unm: { label: 'Không đo được', color: 'unm' },
  tech: { label: 'Ngoài DAG', color: 'faint' },
};

export interface Concept {
  id: string;
  code: string;
  label: string;
  role: Role;
  vars: string[];
  x: number; y: number; w: number;
  dashed?: boolean;
  strong?: boolean;
  cols?: 1 | 2;
  info: [string, string][];
}

export const CONCEPTS: Concept[] = [
  { id: 'C', code: 'C', label: 'Quốc gia / vùng', role: 'conf', vars: ['country'], x: 0, y: 0, w: 240,
    info: [['Vì sao', 'Điều kiện nông học và thị trường khác nhau giữa các nước, ảnh hưởng cả quyết định trồng cover crop lẫn năng suất.'],
           ['Điều chỉnh?', 'Có. Đồng thời là biến để ước lượng tác động theo từng nước.']] },
  { id: 'YR', code: 'YR', label: 'Năm sản xuất', role: 'conf', vars: ['year'], x: 0, y: 84, w: 240,
    info: [['Vì sao', 'Cú sốc thời tiết và giá theo năm; xu hướng áp dụng RA cũng đổi theo năm.'],
           ['Điều chỉnh?', 'Có (tháng 2 đưa vào PS model). Đo "at" — cùng lúc quyết định.']] },
  { id: 'K', code: 'K', label: 'Khí hậu dài hạn', role: 'conf', vars: ['rain_longterm_mm', 'temp_longterm_c'], x: 0, y: 168, w: 240,
    info: [['Vì sao', 'Mưa, nhiệt độ trung bình nhiều năm quyết định cả việc có trồng được cover crop lẫn năng suất.'],
           ['Rủi ro', 'Vùng khí hậu không trồng được cover crop → vi phạm positivity.']] },
  { id: 'S0', code: 'S₀', label: 'Đất nền trước áp dụng', role: 'conf', vars: ['soil_om_baseline_pct'], x: 0, y: 280, w: 240,
    info: [['Vì sao', 'Chất lượng đất vừa quyết định việc áp dụng RA vừa quyết định năng suất.'],
           ['Phân biệt', 'Chỉ số đất đo SAU áp dụng là mediator (soil_om_post_pct), không phải S₀.']] },
  { id: 'F', code: 'F', label: 'Ruộng & tưới', role: 'conf', vars: ['field_size_ha', 'irrigation'], x: 0, y: 364, w: 240,
    info: [['Vì sao', 'Quy mô ruộng được CIAT nêu là confounder; tưới tiêu ảnh hưởng cả khả năng trồng cây che phủ lẫn năng suất.'],
           ['Điều chỉnh?', 'Có.']] },
  { id: 'E', code: 'E', label: 'Kinh nghiệm, khuyến nông, hợp đồng', role: 'conf', vars: ['extension_access', 'contract', 'experience_yr'], x: 0, y: 476, w: 240,
    info: [['Vì sao', 'Hộ có tập huấn hoặc hợp đồng dễ áp dụng RA hơn và cũng quản lý tốt hơn — nguồn confounding mạnh.'],
           ['Điều chỉnh?', 'Có, khi dữ liệu có đo.']] },
  { id: 'O', code: 'O', label: 'Practice RA khác', role: 'unc', vars: ['no_till', 'organic_fert', 'rotation_len_yr'], x: 0, y: 632, w: 240, dashed: true,
    info: [['Vì sao', 'Không cày xới, phân hữu cơ, luân canh. CIAT coi là covariate.'],
           ['Rủi ro', 'Nếu quyết định cùng lúc hoặc sau cover crop thì có thể là mediator/collider.'],
           ['Xử lý', 'P08 tạo hai biến thể L: O_as_confounder (có O) và O_as_mediator (không có O).']] },
  { id: 'U', code: 'U', label: 'Năng lực quản lý', role: 'unm', vars: [], x: 0, y: 772, w: 240, dashed: true,
    info: [['Vì sao', 'Hộ giỏi quản lý vừa dễ áp dụng RA vừa có năng suất cao, nhưng không đo được.'],
           ['Điều chỉnh?', 'Không thể. Chỉ làm sensitivity analysis.']] },
  { id: 'Z', code: 'Z', label: 'Ưu đãi của người mua', role: 'instr', vars: ['buyer_incentive'], x: 380, y: 40, w: 240,
    info: [['Vì sao', 'Giả định chỉ tác động lên việc áp dụng A, không trực tiếp lên năng suất.'],
           ['Điều chỉnh?', 'Không: đưa instrument vào PS làm khuếch đại bias còn lại (bias amplification).']] },
  { id: 'M', code: 'M', label: 'Đất & cỏ dại SAU áp dụng', role: 'med', vars: ['soil_om_post_pct', 'weed_pressure'], x: 700, y: 330, w: 220,
    info: [['Vì sao', 'Cover crop đổi chất đất và cỏ dại; các thay đổi đó lại ảnh hưởng năng suất.'],
           ['Điều chỉnh?', 'Không — sẽ chặn mất một phần tác động thật (P07 chặn vì đo sau can thiệp).']] },
  { id: 'W', code: 'W', label: 'Thời tiết trong mùa vụ', role: 'prec', vars: ['season_rain_mm'], x: 700, y: 520, w: 220,
    info: [['Vì sao', 'Xảy ra sau quyết định nên không gây ra A, nhưng ảnh hưởng Y.'],
           ['Điều chỉnh?', 'Không đưa vào PS. Có thể dùng ở outcome model; cấu hình hiện tại P07 chặn.']] },
  { id: 'A', code: 'A', label: 'Cover cropping', role: 'trt', vars: ['cover_crop', 'cover_crop_months', 'cover_crop_type'], x: 380, y: 190, w: 240, strong: true,
    info: [['Định nghĩa', 'A = 1 khi trồng cây che phủ ≥ 2 tháng trong mùa nghỉ trước vụ khoai tây (P05).'],
           ['Time zero', 'Lúc quyết định trồng. Mọi biến trong L phải đo trước thời điểm này.'],
           ['Phiên bản', 'Số tháng và loại cây (legume/grass/mixed) là các phiên bản của cùng một can thiệp.']] },
  { id: 'Y', code: 'Y', label: 'Năng suất khoai tây', role: 'out', vars: ['yield_t_ha'], x: 380, y: 520, w: 240, strong: true,
    info: [['Đo', 't/ha lúc thu hoạch; tự khai hoặc từ hồ sơ chuỗi cung ứng.'],
           ['Kiểm tra', 'Đơn vị (kg/ha lẫn t/ha), outlier theo nước, thiếu Y có thể gây selection bias.']] },
  { id: 'P', code: 'P', label: 'Tham gia chương trình', role: 'col', vars: ['in_program'], x: 380, y: 700, w: 240,
    info: [['Vì sao', 'Việc có mặt trong chương trình phụ thuộc cả việc áp dụng A lẫn năng suất Y.'],
           ['Điều chỉnh?', 'Không: điều chỉnh collider tạo ra bias dù ban đầu không có.']] },
  { id: 'T', code: '—', label: 'Cột kỹ thuật & nhiễu', role: 'tech', vars: ['record_id', 'field_id', 'grower_id', 'yield_unit', 'noise_1', 'noise_2', 'noise_3', 'noise_4', 'noise_5'], x: 0, y: 0, w: 300, cols: 2,
    info: [['Gồm', 'Mã dòng, mã ruộng, mã nông hộ (khóa cụm cho P09), cột đơn vị thô và 5 cột nhiễu.'],
           ['Vì sao có nhiễu', 'noise_1…5 không liên quan A hay Y: dùng để kiểm tra module không lỡ đưa biến rác vào L.']] },
];

/** [từ, đến, cạnh ra, cạnh vào, kiểu, nhãn] — cạnh: t/b/l/r. */
export type EdgeKind = 'solid' | 'dashed' | 'main';
export const DAG_EDGES: [string, string, string, string, EdgeKind, string?][] = [
  // Cột trái (nguyên nhân chung) → A và Y, vào cạnh trái của hai nút
  ...(['C', 'YR', 'K', 'S0', 'F', 'E'] as const).flatMap(c => [[c, 'A', 'r', 'l', 'solid'], [c, 'Y', 'r', 'l', 'solid']] as [string, string, string, string, EdgeKind][]),
  ['O', 'A', 'r', 'l', 'dashed'], ['O', 'Y', 'r', 'l', 'dashed'],
  ['U', 'A', 'r', 'l', 'dashed'], ['U', 'Y', 'r', 'l', 'dashed'],
  ['Z', 'A', 'b', 't', 'solid'],
  ['A', 'Y', 'b', 't', 'main', 'tác động cần ước lượng'],
  ['A', 'M', 'r', 't', 'solid', 'qua đất'],
  ['M', 'Y', 'b', 'r', 'solid'],
  ['W', 'Y', 'l', 'r', 'solid'],
  ['A', 'P', 'l', 'l', 'solid'],
  ['Y', 'P', 'b', 't', 'solid', 'chọn vào dữ liệu'],
];

export interface VarInfo { label: string; unit?: string; desc: string; mock: string }

export const VARS: Record<string, VarInfo> = {
  record_id: { label: 'Mã dòng', desc: 'Khóa kỹ thuật của một dòng.', mock: 'R00001…R00300; thêm 6 dòng trùng mã.' },
  grower_id: { label: 'Mã nông hộ', desc: 'Một hộ có thể có nhiều ruộng-năm → là khóa cụm.', mock: 'Rút có lặp từ 210 mã → thực tế 155 hộ, một hộ có thể có nhiều dòng.' },
  field_id: { label: 'Mã ruộng', desc: 'Cùng với grower_id và year tạo khóa nghiệp vụ ruộng-năm.', mock: 'F_<hộ>_<1–3>.' },
  country: { label: 'Quốc gia', desc: 'Nước của nông hộ (C1–C4).', mock: 'C1–C4 theo tỷ lệ 40/30/20/10%.' },
  year: { label: 'Năm sản xuất', unit: 'năm', desc: 'Mùa vụ khoai tây.', mock: 'Đều trong 2015–2030.' },
  rain_longterm_mm: { label: 'Mưa trung bình nhiều năm', unit: 'mm', desc: 'Khí hậu dài hạn của vùng.', mock: 'Uniform(500, 2000).' },
  temp_longterm_c: { label: 'Nhiệt độ trung bình nhiều năm', unit: '°C', desc: 'Khí hậu dài hạn của vùng.', mock: 'Uniform(15, 30).' },
  soil_om_baseline_pct: { label: 'Chất hữu cơ đất trước áp dụng', unit: '%', desc: 'Đất nền S₀, đo trước time zero.', mock: 'Uniform(1, 10).' },
  field_size_ha: { label: 'Diện tích ruộng', unit: 'ha', desc: 'Quy mô ruộng.', mock: 'Uniform(0.5, 10).' },
  irrigation: { label: 'Có tưới', desc: 'Ruộng có hệ thống tưới.', mock: 'Có/không 50/50.' },
  extension_access: { label: 'Tiếp cận khuyến nông', desc: 'Hộ có được tập huấn / khuyến nông.', mock: 'Có/không 50/50.' },
  contract: { label: 'Hợp đồng bao tiêu', desc: 'none / informal / formal.', mock: 'Ba mức đều nhau.' },
  experience_yr: { label: 'Số năm kinh nghiệm', unit: 'năm', desc: 'Kinh nghiệm trồng khoai tây của chủ hộ.', mock: 'Số nguyên 1–39.' },
  no_till: { label: 'Không cày xới', desc: 'Practice RA khác.', mock: 'Có/không 50/50.' },
  organic_fert: { label: 'Bón phân hữu cơ', desc: 'Practice RA khác.', mock: 'Có/không 50/50.' },
  rotation_len_yr: { label: 'Độ dài luân canh', unit: 'năm', desc: 'Practice RA khác.', mock: 'Số nguyên 1–4.' },
  cover_crop: { label: 'Trồng cây che phủ (A)', desc: 'Biến can thiệp. P05 ghi đè bằng định nghĩa theo số tháng.', mock: 'Có/không 50/50 (khai báo thô).' },
  cover_crop_months: { label: 'Số tháng trồng cây che phủ', unit: 'tháng', desc: 'Phiên bản của A; nguồn để P05 định nghĩa A.', mock: 'Uniform(1, 6) nếu có trồng, 0 nếu không.' },
  cover_crop_type: { label: 'Loại cây che phủ', desc: 'Phiên bản của A: legume / grass / mixed / none.', mock: 'Đều giữa legume/grass/mixed nếu có trồng.' },
  soil_om_post_pct: { label: 'Chất hữu cơ đất SAU áp dụng', unit: '%', desc: 'Mediator: đo sau time zero, chịu tác động của A.', mock: 'Bằng đất nền + Uniform(−1, 2) — biến duy nhất trong mock phụ thuộc biến khác.' },
  weed_pressure: { label: 'Áp lực cỏ dại', unit: 'thang 1–5', desc: 'Mediator: đo sau time zero.', mock: 'Số nguyên 1–5.' },
  season_rain_mm: { label: 'Mưa trong mùa vụ', unit: 'mm', desc: 'Chỉ ảnh hưởng Y, đo sau time zero.', mock: 'Uniform(100, 1000).' },
  buyer_incentive: { label: 'Ưu đãi của người mua', desc: 'Instrument: đẩy A nhưng không trực tiếp đổi Y.', mock: 'Có/không 50/50.' },
  noise_1: { label: 'Nhiễu 1', desc: 'Không liên quan A hay Y.', mock: 'N(0, 1).' },
  noise_2: { label: 'Nhiễu 2', desc: 'Không liên quan A hay Y.', mock: 'N(0, 1).' },
  noise_3: { label: 'Nhiễu 3', desc: 'Không liên quan A hay Y.', mock: 'N(0, 1).' },
  noise_4: { label: 'Nhiễu 4', desc: 'Không liên quan A hay Y.', mock: 'N(0, 1).' },
  noise_5: { label: 'Nhiễu 5', desc: 'Không liên quan A hay Y.', mock: 'N(0, 1).' },
  yield_t_ha: { label: 'Năng suất khoai tây (Y)', unit: 't/ha', desc: 'Kết quả cần ước lượng tác động.', mock: 'Uniform(5, 60) — không phụ thuộc biến nào.' },
  in_program: { label: 'Tham gia chương trình', desc: 'Collider: phụ thuộc cả A và Y.', mock: 'Có/không 50/50.' },
  yield_unit: { label: 'Đơn vị năng suất (thô)', desc: 'Không có trong schema; P02 dùng để quy đổi kg/ha → t/ha.', mock: '"t/ha", riêng các dòng bị cài lỗi đơn vị là "kg/ha".' },
};

// ---- Lăng kính module: bước Pxx làm gì với từng biến --------------------------------
export type Tone = 'check' | 'fix' | 'flag' | 'drop' | 'block' | 'keep' | 'create' | 'use';
export const TONE_META: Record<Tone, { label: string; color: string }> = {
  check: { label: 'kiểm tra, không đổi', color: 'text-muted' },
  use: { label: 'dùng làm khóa / nguồn', color: 'context-edge' },
  keep: { label: 'hợp lệ / vào L', color: 'ok' },
  flag: { label: 'gắn cờ, giữ nguyên', color: 'info' },
  fix: { label: 'sửa giá trị', color: 'warn' },
  drop: { label: 'bỏ / cách ly dòng', color: 'failed' },
  block: { label: 'chặn / loại khỏi L', color: 'blocked' },
  create: { label: 'sinh cột mới', color: 'teal' },
};

export interface Lens {
  summary: string;
  actions: Record<string, [Tone, string]>;
  /** Hành động mặc định cho các cột trong schema mà `actions` không nhắc tới */
  rest?: [Tone, string];
  creates: [string, string][];
}

export const BOOL_COLS = ['extension_access', 'irrigation', 'no_till', 'organic_fert', 'cover_crop', 'buyer_incentive', 'in_program'];

export const LENSES: Record<string, Lens> = {
  P01: {
    summary: 'Kiểm tra mọi cột theo canonical.yaml: đủ cột, đúng kiểu, trong miền. Chỉ cách ly dòng hỏng thật; lỗi mà bước sau sửa được thì chỉ đánh dấu.',
    actions: {
      record_id: ['drop', '{P01.BAD_RECORD_ID@record_id} dòng mã trống bị cách ly; {P01.DUPLICATE_KEY_SEEN@record_id} mã trùng để P03 xử lý.'],
      temp_longterm_c: ['drop', "{P01.COERCE_FAILED@temp_longterm_c} ô 'abc' không ép được thành số → cách ly cả dòng."],
      country: ['flag', "{P01.NOT_ALLOWED_CATEGORY@country} dòng ghi lệch ('Country 1', ' c1 ', 'C-1') → chỉ đánh dấu, để P02 ánh xạ."],
      contract: ['flag', "{P01.NOT_ALLOWED_CATEGORY@contract} giá trị 'invalid_cat' → đánh dấu."],
      yield_t_ha: ['flag', '{P01.OUT_OF_RANGE@yield_t_ha} giá trị ngoài [0, 120] (ghi kg/ha, ×15, −10) → chỉ đánh dấu.'],
      yield_unit: ['check', 'Không có trong schema → giữ lại, cảnh báo P01.UNKNOWN_COLUMN.'],
    },
    rest: ['check', 'Đúng kiểu, trong miền.'],
    creates: [['flag__p01__not_allowed__country', 'cờ hạng mục lạ'], ['flag__p01__not_allowed__contract', 'cờ hạng mục lạ'], ['flag__p01__out_of_range__yield_t_ha', 'cờ ngoài miền']],
  },
  P02: {
    summary: 'Đưa về cùng một cách viết và một đơn vị: ánh xạ hạng mục qua bảng alias, "True"/"False" → 1/0, kg/ha → t/ha.',
    actions: {
      country: ['fix', "{P01.NOT_ALLOWED_CATEGORY@country} dòng 'Country 1', ' c1 ', 'C-1' → C1."],
      yield_t_ha: ['fix', '{P02.UNIT_CONVERTED} dòng ghi kg/ha được chia 1000.'],
      yield_unit: ['use', 'Nguồn đơn vị (unit_policy = unit_column); sau quy đổi ghi lại thành t/ha.'],
      contract: ['flag', "'invalid_cat' không có alias → ô trống + cờ flag__p02__unmapped__contract."],
      ...Object.fromEntries(BOOL_COLS.map(c => [c, ['fix', "'True'/'False' → 1/0 qua bảng alias."]])),
    },
    creates: [['flag__p02__unmapped__contract', 'cờ không ánh xạ được']],
  },
  P03: {
    summary: 'Tìm dòng trùng theo khóa ruộng-năm. Khác nhau ở cột quan trọng → mâu thuẫn, giữ cả hai để rà soát.',
    actions: {
      grower_id: ['use', 'Khóa nghiệp vụ (cùng field_id, year).'],
      field_id: ['use', 'Khóa nghiệp vụ.'],
      year: ['use', 'Khóa nghiệp vụ, đồng thời là cột quan trọng.'],
      cover_crop: ['use', 'Cột quan trọng: hai bản khác nhau ở đây → mâu thuẫn (2 nhóm bị cài đảo A).'],
      yield_t_ha: ['use', 'Cột quan trọng: một bản sao bị thiếu Y → nhóm thành mâu thuẫn.'],
      country: ['use', 'Cột quan trọng.'],
      record_id: ['drop', '{P03.EXACT_DUPLICATES} nhóm y hệt + {P03.PARTIAL_DUPLICATES} nhóm trùng một phần → bỏ 3 dòng; {P03.CONFLICTING_DUPLICATES} nhóm mâu thuẫn giữ cả hai.'],
      noise_1: ['check', 'Hai nhóm trùng chỉ khác ở noise_1 → trùng một phần, giữ dòng đầy đủ nhất.'],
    },
    creates: [['dup_group_id', 'mã nhóm trùng'], ['flag__p03__duplicate', 'cờ trùng'], ['flag__p03__conflict', 'cờ mâu thuẫn']],
  },
  P04: {
    summary: 'Tìm giá trị bất thường ở 4 cột số. Mặc định chỉ gắn cờ và sinh thêm bản kéo về ngưỡng để so sánh, không sửa cột gốc.',
    actions: {
      yield_t_ha: ['flag', 'Miền [0, 120]: {P04.OUTLIERS_FLAGGED@yield_t_ha} giá trị (451, 491, −10) bị gắn cờ; 2 dòng nghi lỗi đơn vị. Giá trị gốc KHÔNG bị sửa.'],
      field_size_ha: ['check', 'Miền (0, 500]: không có giá trị bất thường.'],
      soil_om_baseline_pct: ['check', 'z bền theo nước (C4 < 30 dòng → dùng ngưỡng chung): không có.'],
      experience_yr: ['check', 'z bền theo nước (C4 < 30 dòng → dùng ngưỡng chung): không có.'],
      country: ['use', 'Nhóm để tính ngưỡng riêng (group_by).'],
    },
    creates: [['yield_t_ha__winsorized', 'Y kéo về [0, 120]'], ['flag__p04__outlier__<cột>', 'cờ bất thường ×4'], ['flag__p04__suspected_unit_error__yield_t_ha', 'cờ nghi lỗi đơn vị'], ['flag__p04__any', 'cờ tổng']],
  },
  P05: {
    summary: 'Định nghĩa lại A từ số tháng trồng: A = 1 khi ≥ 2 tháng. Khai báo "có trồng" nhưng dưới 2 tháng thì thành A = 0.',
    actions: {
      cover_crop_months: ['use', 'Nguồn định nghĩa A (threshold_months = 2).'],
      cover_crop: ['fix', 'Ghi đè: A = 1 từ {ds.raw.cover_crop_true} → {ds.final.treated} dòng. Bản khai báo gốc lưu ở cover_crop__raw.'],
      cover_crop_type: ['create', 'Chép sang cover_crop_type__grouped, kiểm tra ô ít dòng.'],
    },
    creates: [['cover_crop__raw', 'A khai báo gốc'], ['cover_crop__thr1 / thr2 / thr3', 'A theo ngưỡng 1/2/3 tháng — {P05.THRESHOLD_SENSITIVITY} dòng đổi nhóm'], ['cover_crop_type__grouped', 'loại cây đã gộp']],
  },
  P07: {
    summary: 'Xếp từng cột theo thời điểm đo so với time zero. Cột đo sau can thiệp bị chặn khỏi danh sách được xét làm biến điều chỉnh.',
    actions: {
      soil_om_post_pct: ['block', 'Đo sau, chịu tác động của A (mediator) → chặn.'],
      weed_pressure: ['block', 'Đo sau, chịu tác động của A (mediator) → chặn.'],
      in_program: ['block', 'Đo sau, collider → chặn.'],
      season_rain_mm: ['block', 'Đo sau, không chịu tác động của A, nhưng allow_post_precision_vars = false → chặn.'],
      yield_t_ha: ['keep', 'Outcome: giữ trong danh sách hợp lệ (P08 vẫn loại khỏi L).'],
      yield_unit: ['block', 'Không có trong schema → không rõ thời điểm đo → loại.'],
    },
    rest: ['keep', 'Đo trước / tại time zero → hợp lệ.'],
    creates: [],
  },
  P08: {
    summary: 'Dựng tập điều chỉnh L theo vai trò trong DAG: lấy confounder; biến vai trò chưa rõ (O) tạo hai biến thể L; loại mediator, collider, instrument, nhiễu.',
    actions: {},
    creates: [],
  },
  P06: {
    summary: 'Xử lý dữ liệu thiếu trên L + A + Y: điền biến trong L kèm cờ; không bỏ dòng thiếu Y mà tạo cờ quan sát cho IPCW.',
    actions: {
      experience_yr: ['fix', '{P06.IMPUTED@experience_yr} ô thiếu điền trung vị (C4 nhỏ → trung vị chung) + cờ.'],
      contract: ['fix', "{P06.IMPUTED@contract} ô (vốn là 'invalid_cat') điền giá trị hay gặp nhất + cờ."],
      irrigation: ['fix', '{P06.IMPUTED@irrigation} ô thiếu điền giá trị hay gặp nhất + cờ.'],
      yield_t_ha: ['flag', '{P06.OUTCOME_MISSING_RATE@yield_t_ha} dòng thiếu Y được giữ; c_outcome_observed = False.'],
      country: ['use', 'Nhóm để tính trung vị (impute_group_by).'],
    },
    creates: [['c_outcome_observed', 'cờ quan sát được Y'], ['flag__p06__imputed__<cột>', 'cờ ô được điền ×3'], ['flag__p06__missing_any_L', 'cờ thiếu trong L']],
  },
  P09: {
    summary: 'Nhận diện cụm nông hộ và chia 5 fold sao cho một hộ nằm trọn trong một fold, tỷ lệ A giữa các fold gần nhau.',
    actions: {
      grower_id: ['use', 'Khóa cụm → cluster_id ({P09.CLUSTER_SUMMARY} cụm).'],
      cover_crop: ['use', 'Phân tầng fold theo A.'],
      yield_t_ha: ['check', 'ICC của Y theo cụm = {P09.ICC_ESTIMATE:icc}.'],
    },
    creates: [['cluster_id', 'mã cụm'], ['fold_id', 'fold 0–4']],
  },
};

// ---- Hành trình của lỗi được cài vào mock -------------------------------------------
export type Verdict = 'done' | 'flagged' | 'open';
export interface Journey {
  title: string; cols: string[]; injected: string; n: string;
  steps: [string, Tone, string][];
  outcome: string; verdict: Verdict;
}

export const JOURNEYS: Journey[] = [
  { title: 'Tên quốc gia viết lệch', cols: ['country'], n: '16 dòng', injected: "'Country 1' (8), ' c1 ' (4), 'C-1' (4)",
    steps: [['P01', 'flag', 'đánh dấu hạng mục lạ'], ['P02', 'fix', 'ánh xạ alias → C1']],
    outcome: 'Chỉ còn C1–C4.', verdict: 'done' },
  { title: 'Năng suất ghi kg/ha', cols: ['yield_t_ha', 'yield_unit'], n: '17 dòng', injected: 'yield ×1000, yield_unit = "kg/ha"',
    steps: [['P01', 'flag', 'ngoài miền [0, 120]'], ['P02', 'fix', 'chia 1000 theo cột đơn vị'], ['P07', 'block', 'yield_unit: không rõ thời điểm']],
    outcome: 'Đúng đơn vị t/ha.', verdict: 'done' },
  { title: 'Năng suất ghi sai ×15', cols: ['yield_t_ha'], n: '3 dòng', injected: 'yield ×15 (1 dòng trùng với lỗi "abc" nên bị cách ly)',
    steps: [['P01', 'flag', 'ngoài miền'], ['P04', 'flag', 'bất thường + nghi lỗi đơn vị']],
    outcome: 'Còn 451 và 491 t/ha trong analysis_ready, kèm cờ; bản kéo về 120 ở yield_t_ha__winsorized.', verdict: 'flagged' },
  { title: 'Năng suất âm', cols: ['yield_t_ha'], n: '1 dòng', injected: 'yield = −10 (R00244)',
    steps: [['P01', 'flag', 'ngoài miền'], ['P04', 'flag', 'bất thường']],
    outcome: 'Giá trị −10 vẫn còn trong analysis_ready (action = flag_only).', verdict: 'open' },
  { title: 'Chữ trong cột số', cols: ['temp_longterm_c'], n: '1 dòng', injected: "temp_longterm_c = 'abc' (R00247)",
    steps: [['P01', 'drop', 'không ép được số → cách ly']],
    outcome: 'Dòng nằm trong artifact quarantine.', verdict: 'done' },
  { title: 'Mã dòng trống', cols: ['record_id'], n: '1 dòng', injected: 'record_id = ""',
    steps: [['P01', 'drop', 'luôn cách ly']],
    outcome: 'Dòng nằm trong artifact quarantine.', verdict: 'done' },
  { title: 'Hạng mục không tồn tại', cols: ['contract'], n: '1 dòng', injected: "contract = 'invalid_cat'",
    steps: [['P01', 'flag', 'hạng mục lạ'], ['P02', 'flag', 'không có alias → ô trống + cờ'], ['P06', 'fix', 'điền giá trị hay gặp nhất']],
    outcome: 'Có giá trị hợp lệ, còn cờ để truy vết.', verdict: 'done' },
  { title: 'Dòng trùng', cols: ['record_id', 'cover_crop', 'noise_1'], n: '6 dòng', injected: '2 bản y hệt, 2 bản khác noise_1, 2 bản đảo cover_crop',
    steps: [['P01', 'check', 'thấy 6 mã trùng'], ['P03', 'drop', 'bỏ 3 dòng, 3 nhóm mâu thuẫn giữ lại']],
    outcome: '3 cặp record_id trùng còn trong analysis_ready, chờ rà soát (review_list). Một bản y hệt bị cài thêm thiếu Y nên thành mâu thuẫn.', verdict: 'open' },
  { title: 'Thiếu số năm kinh nghiệm', cols: ['experience_yr'], n: '30 ô (10%)', injected: 'experience_yr trống',
    steps: [['P06', 'fix', 'điền trung vị + cờ']],
    outcome: 'Không còn ô trống; cờ flag__p06__imputed__experience_yr.', verdict: 'done' },
  { title: 'Thiếu năng suất', cols: ['yield_t_ha'], n: '15 ô (5%)', injected: 'yield_t_ha trống',
    steps: [['P06', 'flag', 'giữ dòng, c_outcome_observed = False']],
    outcome: 'Giai đoạn ước lượng dùng trọng số IPCW cho các dòng này.', verdict: 'flagged' },
  { title: 'Thiếu thông tin tưới', cols: ['irrigation'], n: '1 ô', injected: 'irrigation trống',
    steps: [['P06', 'fix', 'điền giá trị hay gặp nhất']],
    outcome: 'Không còn ô trống.', verdict: 'done' },
];
