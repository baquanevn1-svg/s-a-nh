import streamlit as st
import cv2
import numpy as np
import io
import zipfile

st.title("📷 Công cụ Sửa Ngày Tháng Ảnh Khảo Sát")

uploaded_files = st.file_uploader("Tải lên danh sách ảnh (JPG, PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

new_date = st.text_input("Ngày tháng năm mới mong muốn:", "2026/09/23 16:22:53")

st.subheader("Cấu hình vị trí văn bản (Góc dưới bên trái)")
col1, col2 = st.columns(2)
with col1:
    crop_x = st.number_input("Tọa độ X góc trái chữ:", value=15)
    crop_y = st.number_input("Tọa độ Y góc trên chữ:", value=1400)
    font_scale = st.number_input("Kích thước chữ (Font Scale):", value=0.75, step=0.05)
    thickness = st.number_input("Độ nét / Độ dày chữ:", value=2, min_value=1, max_value=3)

with col2:
    crop_w = st.number_input("Chiều rộng vùng xóa:", value=240)
    crop_h = st.number_input("Chiều cao vùng xóa:", value=30)

if uploaded_files and st.button("Xử lý ảnh"):
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for idx, uploaded_file in enumerate(uploaded_files):
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None:
                continue
            h, w, _ = img.shape

            # 1. Tách chính xác vùng chứa dòng chữ cũ ở góc dưới
            actual_x = int(crop_x)
            actual_y = int(crop_y)
            actual_w = int(crop_w)
            actual_h = int(crop_h)

            y1, y2 = max(0, actual_y), min(h, actual_y + actual_h)
            x1, x2 = max(0, actual_x), min(w, actual_x + actual_w)
            roi = img[y1:y2, x1:x2]

            if roi.size > 0:
                # Tìm riêng các điểm ảnh màu sáng của chữ cũ
                gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                _, text_mask = cv2.threshold(gray_roi, 170, 255, cv2.THRESH_BINARY)
                
                # Bán kính cực mỏng (1px) để chỉ xóa nét chữ, giữ nguyên 100% vân gạch
                cleaned_roi = cv2.inpaint(roi, text_mask, inpaintRadius=1, flags=cv2.INPAINT_TELEA)
                img[y1:y2, x1:x2] = cleaned_roi

            # 2. Vẽ chữ mới trực tiếp bằng OpenCV (Chuẩn phông, chắc chắn chỉnh to/nhỏ chuẩn 100%)
            font_face = cv2.FONT_HERSHEY_SIMPLEX
            text_pos_x = actual_x + 2
            text_pos_y = actual_y + actual_h - 8

            # Lớp viền đen mỏng tạo độ tương phản
            cv2.putText(img, new_date, (text_pos_x + 1, text_pos_y + 1), font_face, float(font_scale), (0, 0, 0), int(thickness) + 1, cv2.LINE_AA)
            # Lớp chữ màu trắng
            cv2.putText(img, new_date, (text_pos_x, text_pos_y), font_face, float(font_scale), (255, 255, 255), int(thickness), cv2.LINE_AA)

            # Xuất file ra ZIP
            _, encoded_img = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 98])
            zip_file.writestr(f"edited_{uploaded_file.name}", encoded_img.tobytes())

    st.success("✅ Hoàn tất xử lý!")
    st.download_button(
        label="📥 Tải về file ZIP tất cả ảnh đã sửa",
        data=zip_buffer.getvalue(),
        file_name="danh_sach_anh_da_sua.zip",
        mime="application/zip"
    )
