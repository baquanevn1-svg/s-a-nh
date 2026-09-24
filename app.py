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
    font_scale = st.number_input("Độ phóng to chữ (Font Scale):", value=1.0, step=0.1)
    thickness = st.number_input("Độ nét / độ dày nét chữ:", value=2, min_value=1, max_value=5)

with col2:
    crop_w = st.number_input("Chiều rộng vùng xóa:", value=320)
    crop_h = st.number_input("Chiều cao vùng xóa:", value=45)

if uploaded_files and st.button("Xử lý ảnh"):
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for idx, uploaded_file in enumerate(uploaded_files):
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None:
                continue
            h, w, _ = img.shape

            # Lấy vùng ảnh cần xử lý
            y1, y2 = max(0, int(crop_y)), min(h, int(crop_y + crop_h))
            x1, x2 = max(0, int(crop_x)), min(w, int(crop_x + crop_w))
            roi = img[y1:y2, x1:x2]

            if roi.size > 0:
                # 1. Tách nét chữ sáng màu
                gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                _, text_mask = cv2.threshold(gray_roi, 170, 255, cv2.THRESH_BINARY)
                
                kernel = np.ones((2, 2), np.uint8)
                text_mask = cv2.dilate(text_mask, kernel, iterations=1)

                # 2. Xóa chữ mỏng bằng Inpaint (giữ nguyên vân gạch)
                cleaned_roi = cv2.inpaint(roi, text_mask, inpaintRadius=1, flags=cv2.INPAINT_TELEA)
                img[y1:y2, x1:x2] = cleaned_roi

            # 3. Viết chữ mới bằng OpenCV (Chắc chắn chỉnh to nhỏ được 100%)
            font_face = cv2.FONT_HERSHEY_SIMPLEX
            text_x = int(crop_x) + 2
            text_y = int(crop_y) + int(crop_h) - 10 # Căn dòng chữ nằm vừa khung

            # Vẽ lớp bóng mờ màu đen phía sau để chữ nổi bật trên nền gạch
            cv2.putText(img, new_date, (text_x + 1, text_y + 1), font_face, float(font_scale), (0, 0, 0), int(thickness) + 1, cv2.LINE_AA)
            # Vẽ chữ màu trắng phía trước
            cv2.putText(img, new_date, (text_x, text_y), font_face, float(font_scale), (255, 255, 255), int(thickness), cv2.LINE_AA)

            # Lưu ảnh ra file ZIP
            _, encoded_img = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 98])
            zip_file.writestr(f"edited_{uploaded_file.name}", encoded_img.tobytes())

    st.success("✅ Hoàn tất xử lý!")
    st.download_button(
        label="📥 Tải về file ZIP tất cả ảnh đã sửa",
        data=zip_buffer.getvalue(),
        file_name="danh_sach_anh_da_sua.zip",
        mime="application/zip"
    )
