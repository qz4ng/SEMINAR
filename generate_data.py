"""Sinh hai file dữ liệu mẫu để chạy thử pipeline.

    python generate_data.py          # -> data/raw/clean.csv, data/raw/dirty.csv

Đây KHÔNG phải bộ mô phỏng nhân quả (thư mục simulate/ còn trống): chỉ là khung dữ liệu
đúng schema, cộng các lỗi chất lượng đã biết trước, dùng để thử luồng và viết test.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from tests.fixtures.make_frames import make_clean_frame, make_dirty_frame

os.makedirs("data/raw", exist_ok=True)

clean = make_clean_frame(200, 0)
clean.to_csv("data/raw/clean.csv", index=False)

dirty, truth = make_dirty_frame(300, 0)
dirty.to_csv("data/raw/dirty.csv", index=False)

print(f"data/raw/clean.csv : {len(clean)} dòng, không lỗi")
print(f"data/raw/dirty.csv : {len(dirty)} dòng, lỗi đã cài:")
for name, ids in truth.items():
    print(f"    {name:18s} {len(ids)} dòng")
