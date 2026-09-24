# Thiết kế giao diện — `ra_causal` Run Viewer (v1, chỉ đọc)

**Phiên bản:** 1.0 · **Ngày:** 2026-09-24 · **Dữ liệu mẫu:** [`MOCK_DATA.md`](MOCK_DATA.md) · **Prompt dựng UI:** [`PROMPT_antigravity.md`](PROMPT_antigravity.md)

---

## 0. Tóm tắt

Một trang duy nhất để đọc **một lần chạy** của pipeline tiền xử lý `ra_causal` (9 module P01–P09) và trả lời nhanh năm câu hỏi:

| # | Câu hỏi của người dùng | Trả lời ở đâu | Số thao tác |
|---|---|---|---|
| 1 | Lần chạy này có ổn không? | Header + banner | 0 |
| 2 | Bước nào làm mất dòng, mất bao nhiêu? | Phễu dòng | 0 |
| 3 | Vì sao bước này cảnh báo / bị chặn? | Dòng "phát hiện đáng chú ý" trên node → drawer tab Kết quả | 0 → 1 |
| 4 | Tập điều chỉnh L gồm biến nào, biến nào bị chặn và vì sao? | Panel trái "Tập điều chỉnh L" | 1 |
| 5 | Bước này đã chạy với tham số nào? | Drawer tab Tham số | 1–2 |

**Không làm trong v1:** chạy lại pipeline, sửa config, đăng nhập, cài đặt, so sánh hai lần chạy, mobile.

**Người dùng:** kỹ sư dữ liệu và sinh viên nghiên cứu suy luận nhân quả. Họ đọc được mã (`P04.MAX_FLAG_RATE_EXCEEDED`, `adjustment_set`), nhưng không muốn đọc JSON thô để biết pipeline có ổn không.

---

## 1. Nguyên tắc thiết kế

1. **Tiết lộ dần, ba tầng.** Mở trang chỉ thấy cái cần để trả lời câu hỏi 1 và 2. Mọi chi tiết khác nằm sau đúng một thao tác.
2. **Đúng ngữ nghĩa trước, đẹp sau.** Màu đỏ chỉ dành cho lỗi thật. Hành vi đúng của pipeline (chặn biến hậu can thiệp) không bao giờ được tô đỏ.
3. **Không bịa dữ liệu.** Mọi con số lấy từ `run_report.json`; trường không có thì hiện "—", không tự tính ra số trông hợp lý.
4. **Màu không bao giờ đứng một mình.** Mọi trạng thái đều có icon + chữ.
5. **Tiếng Việt cho nhãn, tiếng Anh cho mã.** Mã module, mã lỗi, tên tham số, tên cột, tên trường JSON giữ nguyên tiếng Anh, font mono.

### 1.1 Ba tầng hiển thị

| Tầng | Khi nào hiện | Nội dung | Quy tắc |
|---|---|---|---|
| **1 · Canvas** | Luôn luôn | 9 node gọn, cạnh dữ liệu, phễu dòng | Không có khối con nào trên canvas |
| **2 · Node mở rộng** | Hover node 250ms, hoặc node đang được chọn | Node nở ra 3 khối, mỗi khối 1 dòng | Tối đa **một** node ở tầng 2 tại một thời điểm. Nở ra **đè lên** nội dung bên dưới (z-index), không đẩy node khác |
| **3 · Drawer** | Click một khối (mở đúng tab của khối đó), hoặc click thân node (mở tab Vấn đề) | Chi tiết đầy đủ trong 3 tab | Drawer mở thì node tương ứng giữ trạng thái "đang chọn" |

---

## 2. Bố cục màn hình

Màn hình mục tiêu **1440 × 900**, tối thiểu **1280 × 800**. Dưới 1024px hiện thông báo "Hãy mở trên màn hình rộng hơn".

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ HEADER 56px                                                                              │
│ ra_causal · Run Viewer │ 20260924-111454-11ef44c6 ⧉ │ ▲ Có cảnh báo │ digest 46ec1c5a6f01 ⧉│
│                        │ ⏱ 0.47s │ 306 → 301 dòng                  [ A · Chạy xong | B · Bị chặn ] │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ BANNER 48px (chỉ khi blocked / failed)                                                   │
│ ⛔ Dừng tại P04 · P04.MAX_FLAG_RATE_EXCEEDED · Flag rate 6.3% exceeds 5.0%…  [Mở bước P04]│
├────────┬─────────────────────────────────────────────────────────────────────────────────┤
│ PANEL  │ CANVAS (flex-1)                                                                 │
│ TRÁI   │  Lớp 1 · Chất lượng dữ liệu — Dữ liệu có đọc được không?                        │
│ 280px  │  ┌P01─────┐   ┌P02─────┐   ┌P03─────┐   ┌P04─────┐                            │
│ (gập   │  │        │──▶│        │──▶│        │──▶│        │                            │
│ còn    │  └────────┘   └────────┘   └────────┘   └───┬────┘                            │
│ 56px)  │                                             │                                  │
│        │  Lớp 2 · Định nghĩa biến — Ta đang đo cái gì, được điều chỉnh theo cái gì?      │
│ ◉ L    │  ┌P05─────┐   ┌P07─────┐   ┌P08─────┐  ◀────┘                                  │
│ ▣ Art. │  │        │──▶│        │──▶│        │                                         │
│ ⌕ Mã   │  └────────┘   └────────┘   └───┬────┘                                         │
│        │  Lớp 3 · Cấu trúc mẫu — Mỗi dòng có phải một đơn vị độc lập không?              │
│        │  ┌P06─────┐   ┌P09─────┐  ◀────┘                                               │
│        │  │        │──▶│        │                                                       │
│        │  └────────┘   └────────┘                                                       │
│        ├─────────────────────────────────────────────────────────────────────────────────┤
│        │ PHỄU DÒNG 96px                                                                  │
│        │  Vào  P01  P02  P03  P04  P05  P07  P08  P06  P09                                │
│        │  306  304  304  301  301  301  301  301  301  301                                │
│        │       −2        −3                                                               │
└────────┴─────────────────────────────────────────────────────────────────────────────────┘
                                                       ┌──────────── DRAWER 520px ──────────┐
                                                       │ (trượt vào từ phải, đè lên canvas) │
                                                       └────────────────────────────────────┘
```

| Vùng | Kích thước | Ghi chú |
|---|---|---|
| Header | cao 56px, cố định trên | Luôn thấy |
| Banner | cao 48px | Chỉ khi `status ∈ {blocked, failed}` |
| Panel trái | rộng 280px, gập còn 56px (chỉ icon) | Mặc định **gập** — tránh quá tải khi mở trang |
| Canvas | phần còn lại | Zoom/pan được; `fitView` khi mở trang và khi đổi kịch bản |
| Phễu dòng | cao 96px, dưới canvas | Luôn thấy |
| Drawer | rộng 520px, cao toàn màn hình dưới header | Đè lên canvas; khi mở, canvas cuộn sao cho node đang chọn nằm trong phần canvas còn thấy được bên trái drawer |

---

## 3. Canvas pipeline

### 3.1 Làn (swimlane) và vị trí node

Ba làn xếp **chồng dọc**, mỗi làn chạy **trái → phải**. Đây là cách giữ canvas vừa màn hình (tối đa 4 node một hàng) mà vẫn đọc được thứ tự.

| Làn | Nhãn | Câu hỏi (chữ phụ) | Node theo thứ tự |
|---|---|---|---|
| 1 | Lớp 1 · Chất lượng dữ liệu | Dữ liệu có đọc được không? | P01, P02, P03, P04 |
| 2 | Lớp 2 · Định nghĩa biến | Ta đang đo cái gì, được điều chỉnh theo cái gì? | P05, P07, P08 |
| 3 | Lớp 3 · Cấu trúc mẫu | Mỗi dòng có phải một đơn vị độc lập không? | P06, P09 |

Vị trí cố định (không dùng auto-layout, để vị trí ổn định giữa các lần mở):

| Node | x | y |
|---|---|---|
| P01, P02, P03, P04 | 0, 260, 520, 780 | 40 |
| P05, P07, P08 | 0, 260, 520 | 220 |
| P06, P09 | 0, 260 | 400 |

Nền làn: dải Zinc-900 với alpha 40%, bo góc 12px, nhãn làn ở góc trên trái (13px, Zinc-400), chữ phụ nhỏ hơn (12px, Zinc-500).

> **Thứ tự chạy KHÔNG theo số:** P01 → P02 → P03 → P04 → P05 → P07 → P08 → **P06** → P09. P06 chạy sau P08 vì cần tập L do P08 dựng. Đây là điểm người đọc dễ hiểu sai nhất — nên node P06 có tooltip nhỏ ở mã: "Chạy sau P08 (cần adjustment_set)".

### 3.2 Hai loại cạnh

| Loại | Kiểu vẽ | Khi nào hiện | Nối |
|---|---|---|---|
| **Cạnh dữ liệu** | Nét liền 1.5px, Cyan-400, mũi tên, kiểu `smoothstep` | Luôn | Theo thứ tự chạy. Cạnh chuyển làn (P04→P05, P08→P06) đi từ **đáy** node nguồn xuống, sang trái, rồi vào **đỉnh** node đích |
| **Cạnh context** | Nét đứt 1.5px, Violet-400, cong (bezier), lệch 40px khỏi cạnh dữ liệu để không đè | **Chỉ khi hover hoặc chọn** một node ở hai đầu cạnh | P07→P08 `eligible_columns` · P08→P06 `adjustment_set` · P05→P06 `treatment_column` · P05→P09 `treatment_column` |

Cạnh context có nhãn chip nhỏ ở giữa (mono 11px, nền Zinc-900, viền Violet-400/40%) mang tên khóa context; hover nhãn → tooltip nghĩa của khóa (lấy từ `context_edges[].meaning`).

Trạng thái cạnh dữ liệu theo bước:
- Cạnh **vào** một node "Chưa chạy": nét đứt Zinc-700, không mũi tên sáng.
- Cạnh **vào** node `blocked`/`failed`: màu của trạng thái đó.
- Cạnh đi qua node đang chọn: sáng hơn (opacity 100%, các cạnh khác 60%).

### 3.3 Điều khiển canvas

Zoom bằng cuộn chuột + nút (+/−/vừa khung) ở góc dưới phải canvas. **Không** có minimap (9 node không cần). Không kéo thả node được (chỉ đọc).

---

## 4. Node — Tầng 1 (gọn)

Kích thước **220 × 96px**, bo góc 10px, nền Zinc-900, viền 1px Zinc-800, viền trái 3px theo màu trạng thái.

```
┌──────────────────────────────────────┐
│ P04  outliers           ▲ Cảnh báo   │  ← dòng 1
│ 301 → 301 dòng · 0.02s               │  ← dòng 2
│ ● P04.SUSPECTED_UNIT_ERROR · 6       │  ← dòng 3: phát hiện đáng chú ý
└──────────────────────────────────────┘
```

| Dòng | Nội dung | Kiểu chữ |
|---|---|---|
| 1 | Mã (`P04`, mono 13px đậm) · tên (`outliers`, mono 12px Zinc-300) · badge trạng thái bên phải | |
| 2 | `n_rows_in → n_rows_out dòng · duration_s` | 12px Zinc-400; nếu mất dòng thì phần `→ 301` màu Orange-400 |
| 3 | Chấm severity + `mã · count` của phát hiện đáng chú ý nhất | mono 11px, cắt bằng dấu "…" |

- Tên file (`p04_outliers.py`) chỉ hiện trong tooltip khi hover mã module.
- Hover: viền sáng Zinc-600 (150ms). Đang chọn: viền 2px Cyan-400 + bóng Cyan-400/20%.
- Con trỏ tay trên toàn node.

### 4.1 Trạng thái node

| Giá trị `step.status` | Nhãn | Màu | Icon (lucide) | Nghĩa hiển thị trong tooltip badge |
|---|---|---|---|---|
| `ok` | Ổn | Emerald-500 | `CircleCheck` | Chạy xong, không có gì đáng ngại |
| `warning` | Cảnh báo | Amber-400 | `TriangleAlert` | Chạy xong, có cảnh báo cần xem |
| `blocked` | Bị chặn | Orange-500, badge **nền đặc** | `OctagonMinus` | Module chạy đúng nhưng **dữ liệu** vi phạm ngưỡng — hãy xem lại dữ liệu |
| `failed` | Lỗi | Rose-600, badge nền đặc | `CircleX` | Lỗi kỹ thuật — hãy xem lại code hoặc cấu hình |
| *(không có trong `steps[]`)* | Chưa chạy | Zinc-600, **viền đứt**, nội dung mờ 50% | `CircleDashed` | Không chạy vì một bước trước đó dừng pipeline |

`warning` (amber, badge viền) và `blocked` (orange, badge nền đặc) phải phân biệt được **cả khi không nhìn màu**: khác icon, khác kiểu badge, khác chữ.

**Node "Chưa chạy":** dòng 2 hiện `— · —`, dòng 3 hiện "Chưa chạy trong lần này". Vẫn hover/click được để đọc tab Vấn đề.

### 4.2 Quy tắc dữ liệu cho Tầng 1

| Trường hiển thị | Cách tính |
|---|---|
| Trạng thái | `step.status`. **Không** suy ra từ severity lớn nhất của findings (P03 có finding `error` nhưng status `warning`) |
| Dòng ra của bước `blocked`/`failed` | Hiện `—`, **không** hiện `0` (backend ghi `n_rows_out = 0` cho bước hỏng, đó không phải mất dòng) |
| Phát hiện đáng chú ý | Bỏ mọi finding có mã kết thúc bằng `.SUMMARY`; sắp theo severity `blocking > error > warning > info`, rồi `count` giảm dần, rồi `code` tăng dần; lấy phần tử đầu. Không còn finding nào → "Không có phát hiện" (Zinc-500) |
| Màu chấm severity | `blocking` Orange-500 · `error` Rose-500 · `warning` Amber-400 · `info` Sky-400 |

---

## 5. Node mở rộng — Tầng 2

Khi hover (trễ 250ms) hoặc khi node đang được chọn, node nở ra phía dưới thêm ba khối, tổng cao ~216px. Chiều rộng giữ 220px. Animation chiều cao 160ms ease-out. Nở ra **đè** lên làn bên dưới, không làm dịch node nào.

```
┌──────────────────────────────────────┐
│ P04  outliers           ▲ Cảnh báo   │
│ 301 → 301 dòng · 0.02s               │
│ ● P04.SUSPECTED_UNIT_ERROR · 6       │
├──────────────────────────────────────┤
│ ◎ Vấn đề                           › │
│   Phân biệt giá trị cực trị thật…    │
├──────────────────────────────────────┤
│ ⚙ Tham số                          › │
│   Mặc định · 14 tham số              │
├──────────────────────────────────────┤
│ ▣ Kết quả                          › │
│   4 phát hiện · 0 artifact · ghi: —  │
└──────────────────────────────────────┘
```

| Khối | Icon (lucide) | Dòng tóm tắt | Click → |
|---|---|---|---|
| **Vấn đề** | `Target` | `modules[].short`, cắt 1 dòng, hover hiện đầy đủ | Drawer, tab Vấn đề |
| **Tham số** | `SlidersHorizontal` | Có tham số khác mặc định → `threshold_months = 3 · +1 khác` (tối đa 1 tham số + số còn lại); không có → `Mặc định · n tham số` | Drawer, tab Tham số |
| **Kết quả** | `Package` | `{số findings không tính SUMMARY} phát hiện · {số artifact} artifact · ghi: {khóa context đầu tiên} +{k}`; không ghi context → `ghi: —` | Drawer, tab Kết quả |

Mỗi khối là một hàng bấm được (cao 44px), hover nền Zinc-800, focus bằng bàn phím có viền Cyan-400.

Node "Chưa chạy" ở tầng 2: khối Tham số hiện `Mặc định · n tham số (chưa chạy)`, khối Kết quả hiện `Chưa có kết quả` và **không** bấm được.

---

## 6. Drawer — Tầng 3

Rộng 520px, trượt từ phải 200ms ease-out, nền Zinc-950, viền trái Zinc-800, bóng lớn. Đóng bằng nút ✕, phím Esc, hoặc click ra canvas.

**Đầu drawer (cố định khi cuộn):**
- Dòng 1: `P04` (mono 16px đậm) · `outliers` · badge trạng thái.
- Dòng 2: `p04_outliers.py` (mono 12px Zinc-500) · `spec 1.0`.
- Dòng 3: nút ‹ › để sang bước trước/sau **theo thứ tự chạy** (giữ nguyên tab đang mở).
- Thanh tab: **Vấn đề · Tham số · Kết quả** (tab Kết quả vô hiệu với node "Chưa chạy").

### 6.1 Tab Vấn đề

1. Tiêu đề: `modules[].short` (15px, đậm).
2. Đoạn `modules[].long` (14px, Zinc-300, dòng cao 1.6).
3. Hộp **"Nếu bỏ qua bước này"**: viền trái 3px Amber-400, nền Amber-400/5%, nội dung `modules[].risk`.
4. **Context:** hai hàng chip — "Đọc từ context" và "Ghi vào context" (suy từ `context_edges`: node là `to` → đọc; là `from` → ghi). Hover chip → nghĩa của khóa.
5. **Chỉ với P07 và P08:** bảng vai trò biến từ `variable_roles`:

   | Cột | measured_at | affected_by_treatment | dag_role | Trong L |
   |---|---|---|---|---|

   - Lọc nhanh bằng segmented control: **Tất cả · Trong L · Bị chặn**.
   - Cột "Trong L": ✓ Emerald hoặc ✕ Zinc-500; với biến chỉ có trong biến thể `O_as_confounder` hiện chip "chỉ biến thể O_as_confounder".
   - Hover hàng bị chặn → tooltip lý do, sinh từ `blocked_reason_rules`.
   - Ghi chú cố định dưới bảng (12px, Zinc-500): *"Vai trò biến là giả định DAG v0, chưa được CIAT xác nhận."*
   - Kịch bản B (P07, P08 chưa chạy): không hiện bảng, chỉ hiện ghi chú "Bước này chưa chạy trong lần này".

### 6.2 Tab Tham số

1. **Khối "Khác mặc định"** — so `step.params_effective` với `params[MÃ].defaults` theo từng khóa cấp một (so bằng JSON đã sắp khóa). Mỗi tham số khác: tên (mono) · giá trị hiện tại · gạch ngang giá trị mặc định · chip "đã đổi" (Cyan).
   - Không có tham số nào khác → trạng thái trống bình tĩnh: *"Tất cả 14 tham số đang ở giá trị mặc định."* (icon `CircleCheck` Zinc-500).
2. Nút **"Xem tất cả (14)"** mở bảng đầy đủ:

   | Tham số | Giá trị | |
   |---|---|---|
   | `max_flag_rate` | `0.05` | *(chip "đã đổi" nếu có)* |

   - Tham số lồng nhau (`string_normalize`, `unmapped_action`, `basis`…) hiện dạng hàng gập được.
   - Hover tên tham số → tooltip: mô tả từ `param_docs` + dòng "Giá trị cho phép: …" từ `params[MÃ].allowed` (enum hiện dạng chip mono; kiểu dữ liệu hiện dạng `number`, `boolean`…).
3. Công tắc **"Dạng bảng / Dạng YAML"**: dạng YAML hiện `params_effective` chuyển sang YAML, tô cú pháp, có nút copy. Chỉ đọc.
4. Node "Chưa chạy": hiện `defaults` với nhãn *"Giá trị mặc định — bước này chưa chạy nên không có tham số thực tế."*

### 6.3 Tab Kết quả

1. **Thẻ số** (lưới 3 cột, mỗi thẻ cao 64px):

   | Thẻ | Giá trị | Ghi chú |
   |---|---|---|
   | Dòng vào | `n_rows_in` | |
   | Dòng ra | `n_rows_out` (bước hỏng: `—`) | |
   | Dòng bị loại | `n_rows_in − n_rows_out` (bước hỏng: `—`) | > 0 thì số màu Orange-400 |
   | Cột mới | `len(columns_added)` | hover → danh sách cột |
   | Cột cờ mới | số tên cột bắt đầu `flag__` trong `columns_added` | hover → danh sách. **Không dùng `rows_flagged`** (trường này cộng dồn cả các bước trước) |
   | Cột bị sửa | `len(columns_modified)` | hover → danh sách |

2. **Phát hiện** — nhóm theo severity, mỗi nhóm là một accordion có số đếm ở tiêu đề:
   - `blocking` và `error`: **mở sẵn**.
   - `warning`: mở sẵn, hiện 3 mục đầu + "Xem thêm n".
   - `info`: **gập**.
   - Không tính và không hiện finding `*.SUMMARY` (chúng chỉ có trong JSON gốc).

   Mỗi finding là một thẻ:
   ```
   ● P04.SUSPECTED_UNIT_ERROR                       6 dòng
     cột: yield_t_ha
     Unit error suspected in yield_t_ha
     R00004  R00046  R00050  …                      [Chi tiết ▾]
   ```
   - Mã: mono 12px; hover 300ms → tooltip giải thích từ `error_codes` (khớp đúng mã trước, rồi khớp hậu tố cho mã `*.`).
   - `message` hiện **nguyên văn** (backend có câu tiếng Anh lẫn tiếng Việt).
   - `sample_ids`: chip mono, tối đa 10, click chip → copy.
   - "Chi tiết": mở JSON tree của `details`; nếu `details._trimmed` → ghi chú "Chi tiết lớn, đã rút gọn trong dữ liệu mẫu".

3. **Artifact** — mỗi artifact (`step.artifacts`) một hàng: tên · số dòng (từ `artifacts_preview` nếu có) · nút **"Xem bảng"** mở Dialog bảng xem trước (tìm kiếm theo `record_id`, 50 dòng đầu, tiêu đề cột dính khi cuộn). Artifact không có dữ liệu xem trước → nút vô hiệu, tooltip "Chưa có bản xem trước".

4. **Context đã ghi** — chip cho từng khóa trong `context_updates`.

5. Nút phụ cuối tab: **"Xem JSON gốc"** → Dialog rộng 80vw hiện toàn bộ StepReport dạng JSON tree (mở sẵn 1 cấp, gập/mở từng nút, copy giá trị, copy đường dẫn).

---

## 7. Header, banner, phễu dòng

### 7.1 Header

Trái → phải: `ra_causal · Run Viewer` (14px đậm) │ `run_id` (mono, nút copy) │ badge trạng thái tổng (quy tắc như node) │ `failed_step` dạng chip (chỉ khi có; click → chọn node đó) │ `config_digest` (mono Zinc-400, nút copy, tooltip "Mã băm cấu hình — hai lần chạy cùng mã dùng cùng tham số") │ `⏱ duration_s` │ số dòng │ *(đẩy sang phải)* công tắc kịch bản.

Số dòng: `input.n_rows → n_rows_out của bước cuối cùng chạy thành công` + " dòng". Nếu có bước hỏng: `306 → — (dừng tại P04)`.

Công tắc kịch bản: segmented control hai lựa chọn **"A · Chạy xong"** và **"B · Bị chặn tại P04"**. Đổi kịch bản → đóng drawer, bỏ chọn node, `fitView`.

### 7.2 Banner (chỉ khi `status ∈ {blocked, failed}`)

Cao 48px, nền màu trạng thái 12%, viền dưới màu trạng thái. Nội dung lấy từ finding đầu tiên của bước `failed_step`:

`⛔ Dừng tại P04 · P04.MAX_FLAG_RATE_EXCEEDED · Flag rate 6.3% exceeds 5.0%. Check unit conversions.` — kèm nút **"Mở bước P04"** (chọn node + mở drawer tab Kết quả). Bên phải có dòng phụ: *"Các bước sau không chạy: P05, P07, P08, P06, P09"*.

### 7.3 Phễu dòng

Mười cột đứng: `Vào` (= `input.n_rows`) rồi 9 bước theo **thứ tự chạy**.

| Phần tử | Hiển thị |
|---|---|
| Cột | Cao theo số dòng, trục y **bắt đầu từ 0** (không cắt trục để phóng đại chênh lệch), màu Zinc-600; cột của node đang chọn màu Cyan-400 |
| Nhãn trên cột | Số dòng (mono 11px) |
| Nhãn dưới cột | `−2` màu Orange-400 nếu bước đó làm mất dòng; không mất thì để trống |
| Bước `blocked`/`failed` | Cột sọc chéo màu trạng thái, nhãn "chặn" / "lỗi" thay cho số |
| Bước chưa chạy | Khung viền đứt Zinc-700, không có cột |

Hover cột → tooltip `P03 deduplicate · 304 → 301 (−3)`. Click cột → chọn node tương ứng (không mở drawer).

---

## 8. Panel trái (gập được)

Mặc định **gập** (56px, chỉ icon + tooltip). Click một icon → mở rộng 280px và hiện đúng mục đó. Chỉ một mục mở tại một thời điểm.

### 8.1 Tập điều chỉnh L (icon `ListChecks`)

- Đầu mục: "Tập điều chỉnh L · 13 biến" + công tắc biến thể **O_as_confounder (13) / O_as_mediator (10)**.
  - Chọn một biến thể → danh sách chip các biến có `variant_membership` chứa biến thể đó.
  - Biến chỉ có trong O_as_confounder (`no_till`, `organic_fert`, `rotation_len_yr`) có chấm Violet và tooltip "Practice RA khác, vai trò chưa rõ".
- Mục **"Bị chặn / không dùng"** — biến có `in_L = false`, nhóm thành:
  - *Đo sau can thiệp* (`measured_at = post`): `soil_om_post_pct`, `weed_pressure`, `season_rain_mm`, `yield_t_ha`, `in_program`
  - *Không phải biến điều chỉnh*: treatment, phiên bản treatment, instrument, noise, id, cluster
  - Mỗi biến kèm một dòng lý do từ `blocked_reason_rules`.
- Ghi chú cuối: *"Vai trò biến là giả định DAG v0, chưa được CIAT xác nhận."*
- Kịch bản B: trạng thái trống *"Chưa có tập L — P08 chưa chạy trong lần này."*

### 8.2 Artifact (icon `Archive`)

Danh sách artifact của mọi bước **đã chạy**: tên · bước sinh ra (chip mã) · số dòng · nút "Xem bảng" (cùng Dialog với tab Kết quả). Kịch bản A có `quarantine` (P01), `review_list` (P03), `data_dictionary` (P08). Kịch bản B chỉ có `quarantine`, `review_list`.

### 8.3 Từ điển mã (icon `BookOpen`, phím tắt `/`)

Ô tìm kiếm kiểu command palette trên toàn bộ `error_codes`: gõ `P04` hoặc `đơn vị` đều ra kết quả. Mỗi kết quả: mã (mono) + giải thích. Mã có xuất hiện trong lần chạy hiện tại được gắn chip "có trong lần chạy này" và click được để nhảy tới node đó.

---

## 9. Tương tác và bàn phím

| Thao tác | Kết quả |
|---|---|
| Hover node 250ms | Node lên Tầng 2; cạnh context của node đó hiện ra |
| Click thân node | Chọn node + mở drawer tab Vấn đề |
| Click một khối ở Tầng 2 | Mở drawer đúng tab |
| `Tab` / `Shift+Tab` | Di chuyển giữa các node theo **thứ tự chạy** |
| `←` / `→` khi đã chọn node | Sang node trước/sau theo thứ tự chạy (drawer đi theo, giữ tab) |
| `Enter` | Mở drawer tab Vấn đề |
| `1` `2` `3` khi drawer mở | Chuyển tab Vấn đề / Tham số / Kết quả |
| `Esc` | Đóng dialog → đóng drawer → bỏ chọn node (theo thứ tự) |
| `/` | Mở từ điển mã |

**Trạng thái trên URL** (để chia sẻ đường dẫn): `?scenario=A&node=P04&tab=result`. Mở trang với URL này phải khôi phục đúng trạng thái.

**Chuyển động:** hover viền 150ms · node nở 160ms · drawer 200ms ease-out · tooltip trễ 300ms. Tôn trọng `prefers-reduced-motion` (tắt mọi animation, giữ chuyển trạng thái tức thì).

---

## 10. Hệ thống thị giác

### 10.1 Màu (token)

| Token | Giá trị | Dùng cho |
|---|---|---|
| `bg` | `#09090b` (Zinc-950) | Nền trang, drawer |
| `surface` | `#18181b` (Zinc-900) | Node, thẻ, panel |
| `surface-2` | `#27272a` (Zinc-800) | Hover, viền |
| `border` | `#27272a` | Viền 1px |
| `text` | `#f4f4f5` (Zinc-100) | Chữ chính |
| `text-muted` | `#a1a1aa` (Zinc-400) | Chữ phụ |
| `text-faint` | `#71717a` (Zinc-500) | Ghi chú |
| `ok` | `#10b981` (Emerald-500) | Trạng thái ok |
| `warn` | `#fbbf24` (Amber-400) | Trạng thái warning, severity warning |
| `blocked` | `#f97316` (Orange-500) | Trạng thái blocked, severity blocking, số dòng bị mất |
| `failed` | `#e11d48` (Rose-600) | Trạng thái failed, severity error |
| `info` | `#38bdf8` (Sky-400) | Severity info |
| `data-edge` | `#22d3ee` (Cyan-400) | Cạnh dữ liệu, node đang chọn, chip "đã đổi" |
| `context-edge` | `#a78bfa` (Violet-400) | Cạnh context, biến thể L |

Tương phản chữ tối thiểu WCAG AA (4.5:1 cho chữ thường) trên nền `bg` và `surface`.

### 10.2 Chữ

| Vai trò | Font | Cỡ / độ đậm |
|---|---|---|
| UI | Inter | 12 / 13 / 14 / 16 / 20px; 400 / 500 / 600 |
| Mã, JSON, YAML, tên cột, tên tham số, số liệu | JetBrains Mono | 11 / 12 / 13px; 400 / 600 |

Số liệu dùng `font-variant-numeric: tabular-nums` để cột số thẳng hàng.

### 10.3 Hình khối

Bo góc: node 10px · thẻ 8px · chip 6px · drawer 0. Khoảng cách theo lưới 4px. Bóng chỉ dùng cho drawer, dialog, node đang chọn.

---

## 11. Công nghệ đề xuất

| Việc | Thư viện | Vì sao chọn |
|---|---|---|
| Khung ứng dụng | **Vite + React 18 + TypeScript** | Nhẹ, dựng nhanh, hệ sinh thái lớn nhất cho dashboard |
| Canvas node | **React Flow (`@xyflow/react` v12)** | Chuẩn thực tế cho giao diện dạng DAG/pipeline; node là component React nên làm tiết lộ dần dễ; có sẵn zoom/pan, cạnh `smoothstep`, nhãn cạnh, cạnh tùy biến |
| Thành phần UI | **shadcn/ui** (trên Radix UI) + **Tailwind CSS** | Đúng thẩm mỹ Linear/Vercel/Langfuse; Radix lo sẵn khả năng truy cập (focus, bàn phím, ARIA) cho Sheet, Tabs, Tooltip, HoverCard, Dialog, Accordion, Command |
| Icon | **lucide-react** | Cùng hệ với shadcn, nét mảnh hợp dark mode |
| Phễu dòng | **Recharts** | Biểu đồ cột có tooltip, tùy biến ô cột (sọc chéo, viền đứt) đủ cho 10 cột |
| JSON tree | **`@uiw/react-json-view`** | Có theme tối, gập/mở từng nút, copy giá trị |
| Tô cú pháp YAML | **Shiki** (theme `github-dark-default`) + gói **`yaml`** để chuyển JSON → YAML | Chất lượng tô cú pháp giống VS Code; nạp lười (lazy) chỉ khi mở dạng YAML |
| Bảng artifact | **TanStack Table v8** | Lọc/tìm, tiêu đề dính, không áp style |
| Từ điển mã | **cmdk** (qua `Command` của shadcn) | Command palette chuẩn |
| Chuyển động | **motion** (Framer Motion) | Node nở mượt, tự tôn trọng reduced-motion |
| Trạng thái UI | **Zustand** + đồng bộ URL | Nhỏ, không cần boilerplate |
| Font | `@fontsource-variable/inter`, `@fontsource/jetbrains-mono` | Không phụ thuộc CDN |
| Kiểm thử logic suy dẫn | **Vitest** | Các quy tắc ở §4.2, §6.3 là hàm thuần, phải có test |

**Không dùng:** thư viện dashboard trọn gói (Tremor, Ant Design Pro — áp thẩm mỹ riêng, khó ra phong cách Dagster), D3 trực tiếp cho canvas (tự dựng zoom/pan/cạnh là việc React Flow đã làm), CDN runtime.

---

## 12. Nguồn dữ liệu và quy tắc suy dẫn

### 12.1 Hợp đồng dữ liệu

UI chỉ đọc các trường sau của `run_report.json` — không tự thêm trường:

- **Cấp trên:** `run_id, started_at, finished_at, duration_s, status, failed_step, config_digest, schema_version, input{path, n_rows, n_cols, adapter}, steps[], context_final{adjustment_set, treatment_definition, cluster_column, fold_column, outcome_observed_column}, outputs`
- **Mỗi `steps[]`:** `module_id, module_name, spec_version, status, started_at, duration_s, n_rows_in, n_rows_out, n_cols_in, n_cols_out, rows_dropped, rows_flagged, columns_added[], columns_modified[], params_effective{}, findings[], artifacts{}, context_updates[]`
- **Mỗi finding:** `code, severity (info | warning | error | blocking), message, column, count, sample_ids[], details{}`

Nguồn phụ (tĩnh, trong `MOCK_DATA.md`): `params` (mặc định + giá trị cho phép), `variable_roles` (từ `data_dictionary.csv`), `artifacts_preview`, `modules`, `lanes`, `context_edges`, `blocked_reason_rules`, `error_codes`, `param_docs`.

### 12.2 Hàm suy dẫn (thuần, có test)

| Hàm | Đầu vào → đầu ra | Quy tắc |
|---|---|---|
| `stepsInRunOrder(run, modules)` | → 9 phần tử | Đi theo `modules` (thứ tự chạy); bước không có trong `run.steps` → `{status: "not_run"}` |
| `notableFinding(step)` | → finding \| null | §4.2 |
| `visibleFindings(step)` | → findings | Bỏ `*.SUMMARY` |
| `newFlagColumns(step)` | → string[] | `columns_added` bắt đầu `flag__` |
| `rowsOutLabel(step)` | → string | `blocked`/`failed`/`not_run` → `—`; còn lại `n_rows_out` |
| `funnelPoints(run)` | → 10 điểm | `Vào` + 9 bước; delta = `n_rows_in − n_rows_out` chỉ với bước chạy thành công |
| `changedParams(step, defaults)` | → khóa[] | So từng khóa cấp một bằng JSON đã sắp khóa |
| `blockedReason(row, rules)` | → string | Luật đầu tiên khớp mọi điều kiện trong `when` |
| `explainCode(code, dict)` | → string | Khớp đúng mã; không có thì khớp hậu tố với mục `*.XXX` |
| `finalRowCount(run)` | → number \| null | `n_rows_out` của bước cuối cùng có status `ok`/`warning`; có `failed_step` → null |

---

## 13. Trạng thái đặc biệt

| Tình huống | Hiển thị |
|---|---|
| Kịch bản B — bước sau bước chặn | Node "Chưa chạy" (viền đứt, mờ), cạnh vào nét đứt Zinc, phễu viền đứt |
| Drawer của node "Chưa chạy" | Tab Vấn đề đầy đủ; tab Tham số hiện mặc định kèm ghi chú; tab Kết quả vô hiệu |
| Không có finding nào (trừ SUMMARY) | Tab Kết quả: "Không có phát hiện nào ở bước này." |
| Không có artifact | Ẩn hẳn mục Artifact trong tab Kết quả |
| `details._trimmed` | Ghi chú "Chi tiết lớn, đã rút gọn trong dữ liệu mẫu" |
| Tập L chưa có (P08 chưa chạy) | Panel L: trạng thái trống có lý do |
| Màn hình < 1024px | Thông báo toàn trang "Hãy mở trên màn hình rộng hơn" |

---

## 14. Tiêu chí nghiệm thu

**Tiết lộ dần**
- [ ] Mở trang: không có khối con nào trên canvas; panel trái đang gập; drawer đóng.
- [ ] Hover hai node liên tiếp: chỉ node đang hover ở Tầng 2.
- [ ] Click khối "Tham số" của P04 → drawer mở đúng tab Tham số của P04.

**Đúng dữ liệu**
- [ ] Đếm được đúng 9 node, đúng thứ tự P01→P02→P03→P04→P05→P07→P08→P06→P09 (cạnh dữ liệu và phím `→` đều theo thứ tự này).
- [ ] Kịch bản A: header `306 → 301 dòng`; phễu có `−2` ở P01 và `−3` ở P03.
- [ ] Kịch bản A: P07 **không** có màu đỏ ở bất cứ đâu; P03 node màu cam nhưng chip `P03.CONFLICTING_DUPLICATES` màu đỏ.
- [ ] Kịch bản A: P09 **không** hiện con số 64 ở bất kỳ đâu ngoài JSON gốc.
- [ ] Kịch bản B: banner hiện `P04.MAX_FLAG_RATE_EXCEEDED` và "6.3%"; P04 hiện `301 → —`; 5 node P05, P07, P08, P06, P09 "Chưa chạy"; panel L trống kèm lý do.
- [ ] Không finding `*.SUMMARY` nào xuất hiện trong danh sách phát hiện hay trong số đếm.
- [ ] Mọi con số khớp `MOCK_DATA.md`.

**Truy cập**
- [ ] Đi hết 9 node và mở drawer chỉ bằng bàn phím.
- [ ] Mọi trạng thái phân biệt được khi xem ở chế độ thang xám.
- [ ] URL `?scenario=B&node=P04&tab=result` mở đúng trạng thái.
