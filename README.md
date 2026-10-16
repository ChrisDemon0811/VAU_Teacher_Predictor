# VAU Teacher Predictor

Website dự đoán Top 3 giảng viên dựa trên thói quen lịch sử giảng dạy. Phiên bản hiện tại dùng trực tiếp thuật toán Historical Matching **Bước 9.1** trong `VAU_Buoc9_1_SuaToaK_ColdStart.zip`, có cơ chế cold-start cho tòa K và các tòa chưa có lịch sử. Hệ thống không huấn luyện lại và không dùng tên hoặc mã môn học làm đặc trưng.

> Kết quả chỉ mang tính tham khảo, không phải thông tin phân công giảng viên chính thức. Điểm Historical Matching là điểm xếp hạng, không phải xác suất phần trăm.

## Yêu cầu hệ thống

- Windows 10/11.
- Python 3.11 hoặc phiên bản tương thích.
- Kết nối Internet chỉ cần khi cài thư viện lần đầu. Website chạy cục bộ và không gọi Google Colab hay dịch vụ AI bên ngoài.

## Cài đặt lần đầu

Mở PowerShell hoặc Command Prompt tại thư mục dự án, sau đó chạy:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Nếu máy có nhiều phiên bản Python, có thể dùng `py -3.11` thay cho `python` ở lệnh đầu tiên.

## Khởi chạy

Cách đơn giản nhất: nhấp đúp file `start.bat`.

Hoặc chạy bằng PowerShell:

```powershell
.venv\Scripts\activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Sau đó mở trình duyệt tại:

- Website: <http://127.0.0.1:8000>
- Tài liệu API: <http://127.0.0.1:8000/docs>

Nếu cổng 8000 đang được ứng dụng khác sử dụng, có thể chọn cổng khác mà không sửa file:

```powershell
$env:VAU_PORT = 8001
.\start.bat
```

## API

- `GET /api/health`: kiểm tra server.
- `GET /api/metadata`: thông tin mô hình, Validation, Test tham khảo và danh sách phòng gợi ý.
- `POST /api/predict`: dự đoán Top 3 giảng viên.

Ví dụ dữ liệu gửi lên:

```json
{
  "thu": 5,
  "buoi": "Sáng",
  "phong": "G502",
  "tiet_bat_dau": null,
  "tiet_ket_thuc": null
}
```

Khi bỏ trống cả hai trường tiết, API dùng mô hình cơ bản. Khi nhập đủ tiết bắt đầu và tiết kết thúc, API dùng mô hình nâng cao. API không tự suy đoán tiết học.

Với tòa đã xuất hiện trong Train, ví dụ tòa G, hệ thống tiếp tục dùng tín hiệu thứ, buổi và vị trí. Với tòa K hoặc một tòa mới khác, hệ thống bỏ hoàn toàn trọng số tòa, tầng, phòng và chỉ dùng thứ, buổi, cùng khoảng tiết nếu được nhập. `G501` và `K501` luôn được hiểu là hai tòa khác nhau. Phòng Online không có tầng vật lý.

Nếu có hơn ba giảng viên đồng điểm cao nhất, API trả thêm:

- `so_giang_vien_dong_diem_cao_nhat`.
- `giang_vien_dong_diem_cao_nhat`: danh sách đầy đủ, không chỉ Top 3.
- `che_do` và `toa_moi_chua_co_lich_su`: cho biết cơ chế dự đoán đang dùng.

## Chạy kiểm thử

```powershell
.venv\Scripts\activate
python -m pytest -q
```

Bộ kiểm thử bao gồm các trường hợp bắt buộc: G502 giữ kết quả gốc, K502 cold-start với tám giảng viên đồng điểm, K501 tiết 1–5, Online18, tòa mới khác K, thiếu phòng, thiếu một đầu tiết, phòng sai định dạng và tiết không hợp lệ. Kết quả API được so sánh trực tiếp với `model.predict_9_1.predict()`.

## Cấu trúc chính

```text
app/                 FastAPI, giao diện HTML/CSS/JavaScript
model/               Mã và dữ liệu Bước 9.1
backup_buoc9/        Bản sao các file Bước 9 trước khi nâng cấp
tests/               Kiểm thử API và đối chiếu hàm dự đoán gốc
requirements.txt     Danh sách thư viện
start.bat             Khởi động nhanh trên Windows
```

## Ghi chú đánh giá

Validation được dùng để đánh giá cấu hình đã chọn. Test chỉ là phép kiểm tra tham khảo vì dữ liệu Test đã được xem trong các bước thử nghiệm trước đây; cần dữ liệu của một học kỳ hoàn toàn mới để kiểm chứng cuối cùng.

Tòa K chỉ mới được đưa vào sử dụng từ HK1 năm 2026–2027 và có `0` ca trong Train. Dữ liệu Test HK1 2026–2027 không được đưa vào Train. Vì vậy, dự đoán tòa K là cold-start và chưa phải bằng chứng về thói quen phòng/tầng của giảng viên.

Thời khóa biểu chính thức: <https://pdt.vau.edu.vn/tra-cuu-thoi-khoa-bieu>
