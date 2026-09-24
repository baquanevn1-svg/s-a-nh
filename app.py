import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile

st.title("📷 Công cụ Sửa Ngày Tháng Ảnh Khảo Sát")

uploaded_files = st.file_uploader("Tải lên danh sách ảnh (JPG, PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

new_date = st.text_input("Ngày tháng năm mới mong muốn:", "2026/09/23 16:22:53")

st.subheader("Cấu hình vị trí văn bản (Góc dưới bên trái)")
col1, col2 = st.columns(2)
with col1:
    crop_x = st.number_input("Tọa độ X góc trái chữ:", value=12)
    crop_y = st.number_input("Tọa độ Y góc trên chữ:", value=1390)
    font_size = st.number_input("Kích thước chữ mới:", value=40)
with col2:
    crop_w = st.number_input("Chiều rộng vùng xóa:", value=350)
    crop_h = st.number_input("Chiều cao vùng xóa:", value=50)

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
            y1, y2 = max(0, crop_y), min(h, crop_y + crop_h)
            x1, x2 = max(0, crop_x), min(w, crop_x + crop_w)
            roi = img[y1:y2, x1:x2]

            if roi.size > 0:
                # 1. Chuyển sang ảnh xám để tìm nét chữ màu sáng (trắng/xám)
                gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                
                # 2. Ngưỡng lọc lấy riêng nét chữ
                _, text_mask = cv2.threshold(gray_roi, 170, 255, cv2.THRESH_BINARY)
                
                # Nở nhẹ mask 1 pixel để bao trọn viền chữ
                kernel = np.ones((2, 2), np.uint8)
                text_mask = cv2.dilate(text_mask, kernel, iterations=1)

                # 3. Chỉ inpaint đúng các điểm ảnh thuộc nét chữ (không làm mờ mảng gạch xung quanh)
                cleaned_roi = cv2.inpaint(roi, text_mask, inpaintRadius=1, flags=cv2.INPAINT_TELEA)
                img[y1:y2, x1:x2] = cleaned_roi

            # 4. Viết chữ ngày tháng mới
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)
            draw = ImageDraw.Draw(pil_img)

            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()

            # Viết chữ trắng sắc nét
            draw.text((crop_x + 2, crop_y + 2), new_date, fill=(255, 255, 255), font=font)

            out_img = io.BytesIO()
            pil_img.save(out_img, format="JPEG", quality=98)
            zip_file.writestr(f"edited_{uploaded_file.name}", out_img.getvalue())

    st.success("✅ Hoàn tất xử lý!")
    st.download_button(
        label="📥 Tải về file ZIP tất cả ảnh đã sửa",
        data=zip_buffer.getvalue(),
        file_name="danh_sach_anh_da_sua.zip",
        mime="application/zip"
    )
