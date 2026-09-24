# Prompt cho Antigravity — dựng `ra_causal` Run Viewer

Dán nguyên khối dưới đây vào Antigravity, mở ở thư mục gốc `ra_causal/`.

---

## Vai trò

Bạn là Senior Product Designer kiêm Frontend Engineer, chuyên dashboard kỹ thuật cho MLOps / Data Engineering / Causal Inference (tham chiếu thẩm mỹ: Dagster, Prefect, Langfuse, Linear). Bạn dựng giao diện **đúng dữ liệu** trước, rồi mới đẹp.

## Nhiệm vụ

Dựng một ứng dụng web **chỉ đọc** hiển thị một lần chạy của pipeline tiền xử lý `ra_causal` (9 module P01–P09, bài toán suy luận nhân quả: cover cropping → năng suất khoai tây).

**Đọc trước khi viết dòng code nào, theo thứ tự:**

1. `docs/ui/DESIGN_run_viewer.md` — bản thiết kế. Đây là **nguồn sự thật** về layout, trạng thái, tương tác, màu, chữ, quy tắc suy dẫn và tiêu chí nghiệm thu. Làm đúng từng mục; không tự thêm tính năng.
2. `docs/ui/MOCK_DATA.md` — dữ liệu mẫu lấy từ **hai lần chạy thật**. Chép nguyên văn 7 khối JSON ra file theo bảng ở đầu file đó. Đọc kỹ mục "Những điều về dữ liệu mà UI phải xử lý đúng" — có 8 cái bẫy thật trong dữ liệu.

## Phạm vi

**Làm:** một trang duy nhất gồm header, banner lỗi, canvas pipeline 3 làn, phễu dòng, panel trái gập được, drawer 3 tab, các dialog (bảng artifact, JSON gốc, từ điển mã); công tắc chuyển kịch bản A / B.

**Không làm:** nút chạy lại pipeline, sửa config, đăng nhập, backend, API, trang cài đặt, giao diện mobile, chế độ sáng.

## Công nghệ (chốt, không đổi)

| Việc | Dùng |
|---|---|
| Khung | Vite + React 18 + TypeScript (strict) |
| Canvas | `@xyflow/react` v12 — custom node `ModuleNode`, custom edge `ContextEdge`, group node cho làn |
| UI | Tailwind CSS + shadcn/ui: `Sheet`, `Tabs`, `Tooltip`, `HoverCard`, `Dialog`, `Accordion`, `Command`, `ToggleGroup`, `Badge`, `ScrollArea`, `Separator` |
| Icon | `lucide-react` (tên icon cụ thể có trong DESIGN §4.1, §5, §8) |
| Phễu dòng | `recharts` |
| JSON tree | `@uiw/react-json-view` (theme tối) |
| YAML | gói `yaml` (JSON → YAML) + `shiki` theme `github-dark-default`, nạp lười |
| Bảng artifact | `@tanstack/react-table` v8 |
| Chuyển động | `motion` |
| Trạng thái | `zustand` + đồng bộ URL (`?scenario=&node=&tab=`) |
| Font | `@fontsource-variable/inter`, `@fontsource/jetbrains-mono` |
| Test | `vitest` |

Cấu hình token màu của DESIGN §10.1 vào `tailwind.config` (tên token đúng như bảng). Dark mode là mặc định duy nhất.

## Cấu trúc thư mục

Tạo ứng dụng ở `ui/run-viewer/` (bên cạnh `src/` Python, **không** đặt vào trong gói Python):

```
ui/run-viewer/
├── src/
│   ├── mock/          runs.json · params.json · variable_roles.json · artifacts_preview.json
│   ├── content/       modules.json · error_codes.json · param_docs.json
│   ├── data/
│   │   ├── loadRun.ts     getRun(scenario) — lớp trừu tượng để sau này đọc run_report.json thật
│   │   ├── derive.ts      các hàm suy dẫn thuần của DESIGN §12.2
│   │   └── derive.test.ts
│   ├── store/uiStore.ts   scenario · selectedNodeId · hoveredNodeId · drawerTab · leftPanel
│   ├── components/
│   │   ├── RunHeader.tsx  ErrorBanner.tsx  ScenarioSwitch.tsx
│   │   ├── canvas/        PipelineCanvas.tsx  ModuleNode.tsx  ContextEdge.tsx  LaneGroup.tsx
│   │   ├── RowFunnel.tsx
│   │   ├── drawer/        DetailDrawer.tsx  ProblemTab.tsx  ParamsTab.tsx  ResultTab.tsx
│   │   ├── panels/        LeftPanel.tsx  AdjustmentSetPanel.tsx  ArtifactsPanel.tsx  CodeDictionary.tsx
│   │   └── common/        StatusBadge.tsx  SeverityDot.tsx  CodeTooltip.tsx  ArtifactDialog.tsx  JsonDialog.tsx
│   ├── App.tsx  main.tsx  index.css
└── README.md          cách chạy, cách thay dữ liệu mẫu bằng run_report.json thật
```

## Thứ tự thi công (làm xong và tự kiểm từng bước mới sang bước sau)

1. **Dữ liệu.** Tạo 7 file JSON từ `MOCK_DATA.md`. Viết `derive.ts` với **đúng** các hàm ở DESIGN §12.2 và `derive.test.ts` kiểm tối thiểu:
   - `stepsInRunOrder` trả 9 phần tử theo thứ tự P01, P02, P03, P04, P05, P07, P08, P06, P09; kịch bản B có 5 phần tử `not_run`.
   - `notableFinding` của P04 (A) là `P04.SUSPECTED_UNIT_ERROR`; không bao giờ trả mã `*.SUMMARY`.
   - `rowsOutLabel` của P04 (B) là `—`.
   - `funnelPoints` (A) có delta −2 ở P01, −3 ở P03, còn lại 0.
   - `changedParams` trả mảng rỗng cho mọi bước (dữ liệu mẫu toàn mặc định) và trả đúng khóa khi thử sửa một tham số trong test.
   - `explainCode("P01.EXCESSIVE_ROW_LOSS")` rơi về mục `*.EXCESSIVE_ROW_LOSS`.
2. **Khung trang:** header, công tắc kịch bản, banner, vùng canvas, phễu dòng, panel trái gập — chưa cần tương tác sâu.
3. **Canvas:** 3 làn, 9 node Tầng 1 ở đúng vị trí DESIGN §3.1, cạnh dữ liệu `smoothstep` (cạnh chuyển làn đi từ đáy xuống đỉnh), trạng thái node, node "Chưa chạy".
4. **Tầng 2:** node nở ra 3 khối khi hover 250ms / khi chọn; chỉ một node nở; nở đè, không đẩy node khác; cạnh context hiện khi hover.
5. **Drawer:** 3 tab theo DESIGN §6; mở đúng tab theo khối được click; nút ‹ › theo thứ tự chạy.
6. **Dialog:** bảng artifact, JSON gốc, từ điển mã (`/`).
7. **Bàn phím, URL, reduced-motion** theo DESIGN §9.
8. **Tự nghiệm thu** toàn bộ checklist DESIGN §14 ở cả kịch bản A và B.

## Quy tắc bắt buộc

1. **Không bịa dữ liệu.** Mọi số trên màn hình lấy từ file mock qua `derive.ts`. Không có dữ liệu thì hiện `—` hoặc trạng thái trống có lý do; không thêm số minh họa, không lorem ipsum.
2. **Màu đỏ chỉ cho lỗi thật.** Chặn biến hậu can thiệp (`P07.BLOCKED_POST_TREATMENT`) là hành vi đúng, severity `info` — không bao giờ đỏ.
3. **Trạng thái node = `step.status`**, không phải severity lớn nhất của findings.
4. **Không hiển thị `rows_flagged`** như thành tích của bước (nó cộng dồn); dùng "Cột cờ mới".
5. **Không đếm, không liệt kê finding `*.SUMMARY`**; chúng chỉ nằm trong JSON gốc.
6. **Giữ nguyên văn** `message` của finding (có câu tiếng Anh); nghĩa tiếng Việt đi vào tooltip từ `error_codes`.
7. **Nhãn giao diện tiếng Việt**, còn mã module, mã lỗi, tên tham số, tên cột, tên trường JSON giữ tiếng Anh và dùng font mono.
8. **Màu không bao giờ đứng một mình:** mọi trạng thái có icon + chữ.
9. **Không thêm tính năng** ngoài DESIGN. Chỗ nào DESIGN không nói rõ: chọn phương án đơn giản nhất, ghi lại trong `ui/run-viewer/README.md` mục "Quyết định tự đưa ra".

## Bàn giao

- Lệnh chạy: `cd ui/run-viewer && npm install && npm run dev`, và `npm run test` xanh.
- `README.md` của ứng dụng gồm: cách chạy; cách thay mock bằng một file `run_report.json` thật (chỉ sửa `loadRun.ts`); danh sách "Quyết định tự đưa ra".
- Báo lại kết quả từng mục của checklist DESIGN §14 (đạt / chưa đạt + lý do), kèm ảnh chụp: kịch bản A lúc mở trang, A với P08 đang chọn và drawer tab Vấn đề, B với banner và P04 tab Kết quả.
