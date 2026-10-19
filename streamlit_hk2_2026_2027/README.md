# VAU Teacher Predictor – Streamlit HK2 2026–2027

Đây là **bản Streamlit độc lập**; không xóa hay sửa website FastAPI cũ. Chạy trực tiếp từ lịch sử đã xuất trong `model/retrained_history.csv`; **không cần chạy Colab, không cần database** để host.

## Vì sao cập nhật?

HK2 2025–2026 **đã nằm trong Train cũ** (195 ca trực tiếp, từ raw có 943 dòng lịch tuần, tên môn). Bản này bổ sung 2 chức năng:

1. Tận dụng **tên môn học HK2 năm trước** như tín hiệu phụ (nếu chọn một môn có lịch sử); không biết tên môn thì vẫn dự đoán bằng thứ/buổi/tiết/tòa/tầng/phòng.
2. Sau khi chọn trọng số với Validation HK3 2025–2026, ghép các kỳ **HK1, HK2, HK3 2025–2026 + HK1 2026–2027** thành lịch sử dùng để dự đoán tương lai HK2 2026–2027. Thông tin HK1 2026–2027 được lấy từ snapshot đã thu thập; không khẳng định đã đầy đủ cả kỳ.

Mã lớp học phần lịch sử gồm 12 chữ số; 10 chữ số đầu ánh xạ một-một tới tên môn trong `raw_bo_sung.csv` kiểm tra. Nếu không thể suy ra môn từ nguồn đã có, nhãn môn được giữ **trống**, không đoán.

**Không có dữ liệu thực tế về HK2 2026–2027**, do đó chưa thể công bố độ chính xác trên học kỳ mục tiêu. Điểm xếp hạng không phải xác suất hoặc xác nhận giảng viên.

## Chạy Streamlit ở máy cá nhân

Cài Python 3.11, mở terminal ở thư mục này:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Đường dẫn mặc định: `http://localhost:8501`.

## Host miễn phí trên Streamlit Community Cloud

1. Đưa toàn bộ nội dung thư mục này vào GitHub (nên đặt trong folder riêng `streamlit_hk2_2026_2027/` của repo hiện tại, không ghi đè FastAPI).
2. Truy cập https://share.streamlit.io/ → Create app → chọn repository, branch.
3. **Main file path:** `streamlit_hk2_2026_2027/streamlit_app.py` (hoặc `streamlit_app.py` nếu đặt tại root).
4. Chọn Python 3.11 trong Advanced settings nếu có; Deploy.
5. Nếu dùng folder con, cần bảo đảm package `model` và `requirements.txt` ở cùng folder với file app. Streamlit Cloud tự tìm dependency file theo folder của entrypoint nếu root không có bản ưu tiên khác. Theo hướng dẫn Streamlit Cloud, `requirements.txt` **đặt cạnh `streamlit_app.py` có ưu tiên hơn bản ở root**, vì vậy có thể giữ nguyên repository FastAPI cũ. Không cần tạo repository mới.

## Dữ liệu Bước 10.1

Ứng dụng dùng trực tiếp `model/retrained_history.csv` từ gói Bước 10.1: **758 ca**, gồm 18 ca tầng trệt tòa K (K01, K02, K04, K05, K06). `model/config.json` và `model/report.json` cùng phiên bản 10.1. Không cần và không thực hiện huấn luyện lại khi chạy website. Các dữ liệu cào thô và thư mục Colab không cần đưa lên GitHub.

## Đánh giá và cảnh báo

- Trọng số/mô hình được lựa chọn bằng **Validation HK3 2025–2026** (172 ca). Top 3 **41,86% là kết quả trước Bước 10.1**, chưa phải điểm đánh giá lại trên bộ lịch sử 758 ca. Nhóm ca có nhãn môn học chỉ 27 ca, vì vậy lựa chọn bonus môn học dễ quá khớp; cần học kỳ tương lai làm đánh giá độc lập.
- Test HK1 2026–2027 đã được kiểm tra nhiều lần trước đó, **không còn là tập Test độc lập**; bảng chẩn đoán trong `model/report.json` không đại diện HK2 2026–2027.
- Bộ lịch sử cuối chứa dữ liệu HK1 2026–2027, bao gồm **78 ca ở tòa K**, trong đó 18 ca tầng trệt. Lịch sử tầng trệt còn ít nên dự đoán K01/K02/K04/K05/K06 chỉ mang tính tham khảo.
- 89 ca Online từng bị loại được giữ thành ứng viên và thử trên Validation. Phiên bản được chọn chưa thêm chúng vào lịch sử chính vì kết quả Validation thấp hơn.
- Xem `model/report.json` để biết số liệu và giới hạn đánh giá của phiên bản này.

**Thời khóa biểu chính thức:** https://pdt.vau.edu.vn/tra-cuu-thoi-khoa-bieu
