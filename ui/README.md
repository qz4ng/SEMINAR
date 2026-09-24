# Run Viewer — giao diện xem lượt chạy tiền xử lý

Ứng dụng web chạy trên máy (React + Vite) gồm hai trang:

| Trang | Để làm gì |
|---|---|
| **01 · Lượt chạy** | Sơ đồ 9 bước P01 → P09 theo thứ tự chạy, số dòng qua từng bước. Nhấn một bước để xem *vấn đề nó giải quyết*, *tham số* (mỗi tham số nhận giá trị nào, mỗi giá trị xử lý dữ liệu ra sao) và *kết quả* (phát hiện, số liệu tóm tắt, artifact). |
| **02 · Bối cảnh dữ liệu** | Bài toán và dữ liệu mẫu; **DAG v0 gán xuống từng cột**, có "lăng kính" P01…P09 để thấy mỗi bước làm gì với từng cột; hành trình của các lỗi được cài vào mock; từ điển 31 cột. |

Giao diện dùng **dữ liệu mẫu đóng gói sẵn** (một lượt chạy thật trên `data/raw/dirty.csv`), không cần Python hay backend để mở. Nó chưa tự đọc `data/out/` — muốn xem lượt chạy khác, xem [§7](#7-dữ-liệu-mẫu-và-cách-cập-nhật).

**Mở nhanh** (khi đã có Node.js 20/22):

```bash
cd ui/run-viewer
npm ci
npm run dev        # rồi mở http://localhost:5173
```

---

## 1. Yêu cầu

| Thành phần | Phiên bản | Ghi chú |
|---|---|---|
| Node.js | **22 LTS** (khuyến nghị, có file `.nvmrc`) hoặc **20 LTS** | Tối thiểu 18.18 (Vite 5 yêu cầu `^18.0.0 \|\| >=20.0.0`) |
| npm | đi kèm Node (≥ 9) | Dùng `npm ci` để cài đúng phiên bản trong `package-lock.json` |
| Trình duyệt | Chrome, Edge, Firefox, Safari bản gần đây | |
| Màn hình | rộng ≥ 1024 px | Hẹp hơn, trang chỉ hiện dòng "Hãy mở trên màn hình rộng hơn" |
| Python | *không cần để mở giao diện* | Chỉ cần khi cập nhật dữ liệu mẫu (§7) |

Font (IBM Plex Sans/Mono, Be Vietnam Pro) được cài qua npm và đóng gói cùng ứng dụng, nên mở không cần mạng.

---

## 2. Cài Node.js

Kiểm tra sau khi cài: `node -v` phải in `v20.x` hoặc `v22.x` (bản mới hơn cũng chạy được).

### macOS

Chọn một cách:

```bash
# Cách 1 — nvm (đổi được phiên bản, đọc .nvmrc)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
# mở lại Terminal, rồi trong thư mục ui/run-viewer:
nvm install        # cài đúng bản ghi trong .nvmrc (22)
nvm use

# Cách 2 — Homebrew (node@22 không tự vào PATH, thêm dòng thứ hai rồi mở lại Terminal)
brew install node@22
echo 'export PATH="$(brew --prefix node@22)/bin:$PATH"' >> ~/.zshrc
```

Hoặc tải bộ cài **LTS** (.pkg) ở nodejs.org — chạy được cho cả Mac chip Intel lẫn Apple.

### Windows

Chọn một cách, trong **PowerShell**:

```powershell
# Cách 1 — winget
winget install OpenJS.NodeJS.LTS

# Cách 2 — bộ cài .msi bản LTS từ nodejs.org (giữ tick "Add to PATH")

# Cách 3 — nvm-windows (không đọc .nvmrc, phải ghi rõ phiên bản)
nvm install 22
nvm use 22
```

Đóng và mở lại PowerShell sau khi cài để PATH có hiệu lực.

- PowerShell báo *"npm.ps1 cannot be loaded because running scripts is disabled"*: chạy một lần
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, hoặc gõ `npm.cmd` thay cho `npm`, hoặc dùng Command Prompt.

### Linux (Ubuntu/Debian, Fedora, WSL)

```bash
# Khuyến nghị — nvm (không cần sudo)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc
cd ui/run-viewer && nvm install && nvm use
```

- **Không dùng gói `nodejs` mặc định của Ubuntu 22.04** (bản 12.x, quá cũ). Ubuntu 24.04 có 18.19 — chạy được nhưng nên lên 22.
- Fedora 40+: `sudo dnf install nodejs` (bản 20) là đủ.
- **WSL**: cài Node **bên trong WSL** và để dự án trong `~/…`. Đừng chạy Node của Windows trên thư mục WSL, cũng đừng chạy Node của WSL trên `/mnt/c/…` (rất chậm và dễ lỗi thư viện, xem §5).

---

## 3. Cài thư viện và mở giao diện

Các lệnh giống nhau trên cả ba hệ điều hành (Windows: dấu `\` hay `/` trong đường dẫn đều được).

```bash
cd ui/run-viewer
npm ci             # cài đúng phiên bản trong package-lock.json (lần đầu, hoặc khi lock thay đổi)
npm run dev        # server phát triển, tự tải lại khi sửa code
```

Mở trình duyệt tại **http://localhost:5173**. Dừng bằng `Ctrl + C` trong terminal.

**Bản build tĩnh** (nhẹ hơn, giống bản sẽ đưa lên web):

```bash
npm run build      # kiểm tra kiểu TypeScript rồi đóng gói vào dist/
npm run preview    # phục vụ dist/ tại http://localhost:4173
```

Không mở thẳng file `dist/index.html` bằng trình duyệt: trang sẽ trắng vì trình duyệt chặn script module qua `file://`. Luôn dùng `npm run preview` hoặc một web server.

**Mở từ máy khác trong mạng LAN / từ Windows vào WSL**: thêm `-- --host`, rồi dùng địa chỉ *Network* mà Vite in ra.

```bash
npm run dev -- --host
```

### Chia sẻ bằng link (GitHub Pages)

Workflow [`.github/workflows/deploy-ui.yml`](../.github/workflows/deploy-ui.yml) tự build và đăng giao diện mỗi khi push thay đổi trong `ui/run-viewer/` lên nhánh `main`.

1. Bật một lần: trên GitHub → **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. Push; xem tiến trình ở tab **Actions** (khoảng 1–2 phút).
3. Link: `https://<tên-tài-khoản>.github.io/<tên-repo>/`, vd `https://qz4ng.github.io/SEMINAR/`. Thêm `?view=context` để mở thẳng trang Bối cảnh dữ liệu.

Repo **private** chỉ đăng được Pages với tài khoản GitHub trả phí; tài khoản miễn phí cần để repo public. Build cho Pages dùng biến `VITE_BASE=/<tên-repo>/` (đặt sẵn trong workflow); chạy trên máy không cần.

---

## 4. Dùng giao diện

### Mở thẳng một chỗ bằng URL

| URL | Mở |
|---|---|
| `/` | Trang Lượt chạy |
| `/?node=P04&tab=params` | Bước P04, tab Tham số (`tab` = `problem` · `params` · `result`) |
| `/?view=context` | Trang Bối cảnh dữ liệu |
| `/?view=context&lens=P08` | Bối cảnh dữ liệu, DAG nhìn qua lăng kính P08 |

### Phím tắt

| Phím | Tác dụng |
|---|---|
| `←` `→` | Bước trước / sau (khi đang mở một bước) |
| `1` `2` `3` | Tab Vấn đề / Tham số / Kết quả |
| `Esc` | Đóng bảng chi tiết |
| `/` | Mở từ điển mã (tra `P04.MAX_FLAG_RATE_EXCEEDED`…) |

Nút mặt trăng/mặt trời góc phải đổi nền sáng/tối; lựa chọn được nhớ trong trình duyệt.

---

## 5. Sự cố thường gặp

| Triệu chứng | Nguyên nhân | Sửa |
|---|---|---|
| `vite: not found` / `'vite' is not recognized…` | Chưa cài thư viện | `npm ci` |
| `Cannot find module @rollup/rollup-…`, hoặc esbuild báo *"You installed esbuild for another platform"* | `node_modules` được chép từ máy/hệ điều hành khác (vd giữa Windows và WSL, Mac và Linux). Thư viện đóng gói có phần nhị phân riêng cho từng hệ điều hành | Xóa `node_modules` rồi `npm ci` lại. macOS/Linux: `rm -rf node_modules` · Windows: `Remove-Item -Recurse -Force node_modules` |
| `npm ci` báo lock không khớp `package.json` | Ai đó sửa `package.json` mà chưa cập nhật lock | `npm install` một lần (sẽ cập nhật `package-lock.json`) |
| `Port 5173 is in use` | Cổng đang bận | `npm run dev -- --port 5174` |
| `SyntaxError` lạ khi chạy Vite, hoặc báo cần Node 18+ | Node quá cũ | Cài Node 20/22 (§2) |
| Trang trắng khi mở `dist/index.html` | Mở qua `file://` | `npm run preview` |
| Trình duyệt Windows không vào được `localhost:5173` khi server chạy trong WSL | Mạng WSL | `npm run dev -- --host`, dùng địa chỉ *Network* |
| Chỉ thấy "Hãy mở trên màn hình rộng hơn" | Cửa sổ hẹp hơn 1024 px | Phóng to cửa sổ / giảm zoom trình duyệt |
| VSCode tô đỏ `tsconfig.json` hoặc file `.tsx` dù `npm run build` vẫn qua | VSCode dùng TypeScript riêng (bản 6.x), khắt khe hơn bản 5.9 của dự án. Cấu hình hiện tại đã sửa cho cả hai | `Ctrl/Cmd + Shift + P` → **TypeScript: Restart TS Server**, hoặc **Developer: Reload Window**. Muốn VSCode dùng đúng bản của dự án: mở một file `.ts` → **TypeScript: Select TypeScript Version** → *Use Workspace Version* |
| VSCode gạch vàng `@tailwind`, `@apply` trong `index.css` | Bộ kiểm tra CSS của VSCode không biết cú pháp Tailwind | Thêm `"css.lint.unknownAtRules": "ignore"` vào `.vscode/settings.json` (đã có sẵn ở thư mục Seminar) |
| Sơ đồ quá nhỏ hoặc lệch | Khung nhìn chưa khớp | Nút ⤢ (fit) ở góc sơ đồ, hoặc tải lại trang |

---

## 6. Kiểm tra

```bash
npm test           # 6 test cho các hàm suy dữ liệu (src/data/derive.test.ts)
npm run build      # kiểm tra kiểu TypeScript + đóng gói; phải kết thúc bằng "✓ built"
```

---

## 7. Dữ liệu mẫu và cách cập nhật

### Các file dữ liệu

| File | Nguồn | Cập nhật bằng |
|---|---|---|
| `src/mock/runs.json` | `run_report.json` của lượt chạy mẫu | `scripts/import_run.py` |
| `src/mock/variable_roles.json` | `data_dictionary.csv` (artifact của P08) | `scripts/import_run.py` |
| `src/mock/data_profile.json` | CSV thô + `after_P09.parquet` — phân phối từng cột trước/sau tiền xử lý | `scripts/build_data_profile.py` |
| `src/mock/params.json` | Giá trị mặc định và giá trị cho phép của từng tham số | sửa tay theo `configs/preprocess.yaml` |
| `src/content/param_guide.json` | Mỗi giá trị tham số xử lý ra sao (viết theo code P01–P09) | `scripts/build_param_guide.py` |
| `src/content/dataContext.ts` | Nhóm DAG, mũi tên, ý nghĩa cột, lăng kính module, hành trình lỗi | sửa tay |
| `src/content/modules.json`, `error_codes.json` | Mô tả module và mã lỗi | sửa tay |

### Nạp một lượt chạy khác

1. Chạy pipeline ở thư mục gốc (xem [README gốc](../README.md) §3), ví dụ `--output data/out`.
2. Lấy `run_id` = tên thư mục mới trong `data/out/interim/`.
3. Trong `ui/run-viewer`, dùng Python của dự án (`.venv` ở thư mục gốc, cần pandas + pyarrow cho bước thứ hai):

   **macOS / Linux**
   ```bash
   ../../.venv/bin/python scripts/import_run.py --run-dir ../../data/out --run-id <run_id>
   ../../.venv/bin/python scripts/build_data_profile.py \
       --raw ../../data/raw/dirty.csv \
       --final ../../data/out/interim/<run_id>/after_P09.parquet \
       --schema ../../configs/schema/canonical.yaml --out src/mock/data_profile.json
   ```

   **Windows (PowerShell)**
   ```powershell
   ..\..\.venv\Scripts\python scripts\import_run.py --run-dir ..\..\data\out --run-id <run_id>
   ..\..\.venv\Scripts\python scripts\build_data_profile.py `
       --raw ..\..\data\raw\dirty.csv `
       --final ..\..\data\out\interim\<run_id>\after_P09.parquet `
       --schema ..\..\configs\schema\canonical.yaml --out src\mock\data_profile.json
   ```
   Thay `<run_id>` bằng mã thật (PowerShell báo lỗi nếu để nguyên dấu `<` `>`).
4. `npm run dev` (hoặc tải lại trang) để xem.

Giới hạn cần biết:
- Phần **"Lỗi được cài vào mock"** và vài câu trong lăng kính (vd "451 và 491 t/ha", "149 → 118 dòng") trong `dataContext.ts` được viết cho `dirty.csv`. Đổi sang dữ liệu khác thì phải sửa tay phần này. Các con số gắn với finding (`{P04.OUTLIERS_FLAGGED@yield_t_ha}`…) tự lấy từ lượt chạy.
- Giao diện đọc đúng một lượt chạy (khóa `"A"` trong `runs.json`); lượt bị chặn giữa chừng vẫn hiển thị được (bước chưa chạy có nét đứt, banner đỏ báo dừng ở đâu).

### Khi sửa code P01–P09

Nếu thêm/bớt tham số hoặc đổi cách một giá trị xử lý dữ liệu: sửa nội dung trong `scripts/build_param_guide.py`, cập nhật `src/mock/params.json`, rồi chạy (Python nào cũng được, không cần thư viện ngoài):

```bash
python3 scripts/build_param_guide.py src/mock/params.json src/content/param_guide.json     # macOS / Linux
py scripts\build_param_guide.py src\mock\params.json src\content\param_guide.json          # Windows
```

Script dừng và báo lỗi nếu có tham số thiếu hướng dẫn hoặc danh sách giá trị lệch với `params.json`.

### ⚠ Không chạy `parse_mock.py` ở thư mục gốc

Script đó (do agent Antigravity tạo lúc dựng bản đầu) chép lại dữ liệu từ `docs/ui/MOCK_DATA.md`, bản cũ hơn hiện tại. Chạy nó sẽ **ghi đè** `runs.json`, `variable_roles.json`, `modules.json`… và tạo lại `param_docs.json` đã bỏ: tình huống B quay lại, số liệu tóm tắt của P04/P06/P07 bị rút gọn.

---

## 8. Cấu trúc mã

```
ui/run-viewer/
├── index.html                  # áp theme sáng/tối trước khi React chạy
├── tailwind.config.js          # màu = biến CSS (bảng màu của Atlas_Nhan_qua_RA.html)
├── scripts/                    # import_run.py · build_data_profile.py · build_param_guide.py
└── src/
    ├── App.tsx                 # khung trang, chuyển giữa hai trang
    ├── index.css               # biến màu sáng/tối, font, style React Flow
    ├── store/uiStore.ts        # trạng thái giao diện + đồng bộ URL (?view, ?node, ?tab, ?lens)
    ├── data/                   # suy dữ liệu (derive.ts + test), đọc lượt chạy, màu theme cho SVG
    ├── content/                # nội dung viết tay: module, mã lỗi, hướng dẫn tham số, bối cảnh DAG
    ├── mock/                   # dữ liệu mẫu (xem §7)
    └── components/
        ├── RunHeader.tsx       # tiêu đề, số tổng, tab 01/02, chú giải
        ├── RowFunnel.tsx       # số dòng sau mỗi bước
        ├── canvas/             # sơ đồ pipeline (React Flow)
        ├── drawer/             # bảng chi tiết: Vấn đề · Tham số · Kết quả
        ├── context/            # trang Bối cảnh dữ liệu: DAG, lăng kính, inspector, hành trình lỗi
        ├── panels/             # Tập L, Artifact, Từ điển mã
        └── common/             # nhãn trạng thái, nhãn tác động, bảng chi tiết finding
```

Thư viện chính: React 18, Vite 5, TypeScript, Tailwind CSS 3, @xyflow/react (sơ đồ), Radix UI (tab, tooltip, hộp thoại), lucide-react (icon), shiki (tô màu YAML), zustand (trạng thái).
