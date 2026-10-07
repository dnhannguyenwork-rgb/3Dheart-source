# Báo cáo tổng quan và hướng dẫn sử dụng

## 1. Dự án này làm gì?

Dự án đọc một bộ ảnh MRI tim 3D cùng với một tệp nhãn phân đoạn tương ứng, sau đó chuẩn bị ảnh lát cắt, mô hình bề mặt 3D và các số đo để xem trên trình duyệt. Có thể hình dung tệp MRI là ảnh chụp ban đầu, còn tệp nhãn giống như một bản đồ tô màu cho biết voxel (một phần tử nhỏ trong ảnh 3D) thuộc cấu trúc nào.

Điểm cần phân biệt: chương trình **không tự tìm hoặc phân đoạn cấu trúc tim từ MRI**. Tệp nhãn phân đoạn phải được tạo từ trước, chẳng hạn bởi một quy trình chuyên môn khác hoặc có sẵn trong bộ dữ liệu. Phần web chủ yếu giúp quan sát và đo đạc từ MRI cùng nhãn đã có.

## 2. Đầu vào

Mỗi ca cần một cặp tệp định dạng NIfTI (`.nii.gz`):

| Tệp | Ý nghĩa |
|---|---|
| `pat1_cropped_norm.nii.gz` | Ảnh MRI 3D đã cắt vùng quan tâm và chuẩn hóa cường độ sáng. |
| `pat1_cropped_seg.nii.gz` | Ảnh nhãn 3D cùng kích thước, mỗi voxel mang một mã cấu trúc. |

Tên `pat1` chỉ là mã ca ví dụ; hai tệp trong một cặp phải có cùng mã. Giá trị nhãn `0` là nền; các giá trị từ `1` đến `8` lần lượt biểu thị:

| Mã | Cấu trúc |
|---:|---|
| 1 | Thất trái |
| 2 | Thất phải |
| 3 | Tâm nhĩ trái |
| 4 | Tâm nhĩ phải |
| 5 | Động mạch chủ |
| 6 | Động mạch phổi |
| 7 | Tĩnh mạch chủ trên |
| 8 | Tĩnh mạch chủ dưới |

Ngoài kích thước, hai tệp cần cùng hướng và cùng tọa độ không gian. Công cụ kiểm tra kích thước, ma trận định hướng và giá trị nhãn; nếu không khớp, ca đó sẽ không được xử lý thành công. Thông tin khoảng cách giữa các voxel trong NIfTI được dùng để quy đổi số voxel sang kích thước thực.

## 3. Quá trình xử lý

Quy trình chính nằm trong [`prepare_case.py`](prepare_case.py):

1. Đọc MRI và nhãn, đưa chúng về hướng chuẩn gần nhất, rồi kiểm tra dữ liệu có tương ứng với nhau.
2. Chuẩn hóa cường độ MRI về ảnh mức xám để trình duyệt hiển thị rõ.
3. Tạo ảnh tổng hợp (atlas) cho từng mặt phẳng axial, coronal và sagittal. Mỗi ảnh tổng hợp chứa nhiều lát cắt; trình duyệt chọn lát cần xem từ đó.
4. Với từng mã cấu trúc có trong nhãn, đếm voxel, tính thể tích dựa trên kích thước voxel, rồi trích bề mặt tam giác 3D bằng thuật toán marching cubes.
5. Ghi ảnh lát cắt, ảnh nhãn, cùng thông tin và hình học 3D thành các tệp trong thư mục dữ liệu của ca.

Để xử lý nhiều ca, [`prepare_all_case.py`](prepare_all_case.py) tìm các cặp tệp trong thư mục nguồn, gọi quy trình trên cho từng cặp và cập nhật danh mục `web/cases.json`.

## 4. Sản phẩm đầu ra

Mỗi ca được chuẩn bị trong `web/cases/<mã-ca>/data/`, thường gồm:

| Đầu ra | Dùng để làm gì? |
|---|---|
| `axial.png`, `coronal.png`, `sagittal.png` | Các lát MRI đã xếp thành ảnh tổng hợp để xem nhanh. |
| `*_labels.png` | Các lát nhãn phân đoạn, dùng để phủ màu cấu trúc lên MRI. |
| `case.json` | Mô tả ca, kích thước ảnh, thông tin lát cắt, số đo và dữ liệu lưới 3D. |
| `cases.json` ở thư mục `web` | Danh sách ca để điền vào bộ chọn ca và biểu đồ so sánh. |

Thể tích được tính từ số voxel của cấu trúc nhân với thể tích một voxel, sau đó đổi từ mm³ sang mL. Kích thước và thể tích vì vậy phụ thuộc vào thông tin không gian trong tệp NIfTI và độ chính xác của nhãn đầu vào.

## 5. Chạy trang web

Mở PowerShell tại thư mục `code_web` rồi chạy:

```powershell
python server.py
```

Máy chủ chạy tại `http://127.0.0.1:8765` và chương trình sẽ thử mở địa chỉ này trong trình duyệt. Nếu trình duyệt không tự mở, nhập địa chỉ vào thanh địa chỉ. Dừng máy chủ bằng `Ctrl+C` trong cửa sổ PowerShell.

Máy chủ này chỉ phục vụ các tệp web đã tạo; để mở kết quả có sẵn, không cần chạy lại bước xử lý MRI. Nếu lệnh `python` chưa được nhận diện, cần cài Python và chọn Python trong PATH trước.

### Chuẩn bị hoặc cập nhật dữ liệu

Tệp `requirements.txt` liệt kê các thư viện Python cần cho bước xử lý. Với dữ liệu hiện có trong dự án, mở PowerShell tại `code_web` và chạy:

```powershell
python -m pip install -r requirements.txt
python prepare_all_case.py ".\cropped_norm\cropped_norm"
```

Lệnh xử lý tìm cặp `*_cropped_norm.nii.gz` và `*_cropped_seg.nii.gz`, ghi kết quả vào `web/cases/` và cập nhật `web/cases.json`. Chỉ chạy lại nếu muốn tạo mới hoặc cập nhật dữ liệu; thao tác này có thể ghi đè dữ liệu web đã tạo cho các ca trùng mã. Nếu dùng bộ dữ liệu khác, thay đường dẫn thư mục nguồn bằng thư mục chứa các cặp tệp đúng mẫu tên.

## 6. Hướng dẫn sử dụng giao diện

1. **Chọn ca:** dùng danh sách ở đầu trang. Mỗi lựa chọn tương ứng với một thư mục dữ liệu đã chuẩn bị.
2. **Chọn mặt phẳng:** nhấn `Axial`, `Coronal` hoặc `Sagittal` để đổi hướng xem.
3. **Di chuyển lát cắt:** kéo thanh trượt bên dưới ảnh MRI. Nhãn trên ảnh cho biết mã ca, số lát hiện tại và vị trí lát cắt theo mm.
4. **Phát hoặc tạm dừng:** nhấn `Play slices` để lần lượt xem các lát trong mặt phẳng hiện tại; nhấn `Pause` để dừng. Đây chỉ là chuyển lát cắt, không phải video tim đang đập.
5. **Hiện màu phân đoạn:** bật `Color labels` để phủ màu nhãn lên MRI. Màu giúp phân biệt các cấu trúc.
6. **Chọn cấu trúc:** nhấn tên cấu trúc trong danh sách hoặc một hàng trong bảng đo. Mô hình 3D sẽ tập trung vào cấu trúc đó; nếu `Color labels` đang bật, lớp màu trên MRI cũng chỉ làm nổi cấu trúc đã chọn. Nhấn lại hoặc `Show all` để xem tất cả.
7. **Xem mô hình 3D:** kéo trong vùng mô hình để xoay, cuộn để phóng to/thu nhỏ; nhấn `Reset view` để đặt lại góc nhìn.
8. **Đọc số đo:** bảng bên dưới liệt kê số voxel, thể tích (mL) và kích thước (mm) của từng cấu trúc trong ca đang chọn.
9. **So sánh ca:** chọn cấu trúc ở mục `Volume Comparison Across Cases`; biểu đồ hiển thị thể tích cấu trúc đó ở các ca có dữ liệu tương ứng.

## 7. Giới hạn và lưu ý

- Đây là công cụ trực quan hóa dữ liệu, không phải hệ thống chẩn đoán và không thay thế đánh giá của chuyên gia y tế.
- Mô hình 3D được dựng từ nhãn phân đoạn đầu vào. Nhãn sai hoặc thiếu sẽ làm hình dạng và số đo sai hoặc thiếu; phần mềm không tự sửa hay xác nhận nhãn.
- Ảnh được phát theo lát cắt không biểu diễn chu kỳ tim. Dữ liệu đầu vào hiện được xử lý như một thể tích MRI tĩnh.
- So sánh giữa các ca chỉ hữu ích khi dữ liệu, quy ước nhãn và cách đo tương thích. Biểu đồ không tự điều chỉnh khác biệt giữa các nguồn dữ liệu.
- Chỉ các cấu trúc có mã nhãn tương ứng từ `1` đến `8` được đưa vào danh sách và mô hình theo quy tắc hiện tại.

## 8. Tệp mã nguồn liên quan

- [`prepare_case.py`](prepare_case.py): xử lý một cặp MRI và nhãn.
- [`prepare_all_case.py`](prepare_all_case.py): tìm và xử lý nhiều ca.
- [`server.py`](server.py): chạy máy chủ web cục bộ.
- [`web/index.html`](web/index.html), [`web/app.js`](web/app.js), [`web/style.css`](web/style.css): cấu trúc, hành vi và giao diện trang xem.
- [`requirements.txt`](requirements.txt): các thư viện Python dùng cho bước chuẩn bị dữ liệu.