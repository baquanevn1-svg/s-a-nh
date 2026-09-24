import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile
import urllib.request
import os

st.title("📷 Công cụ Sửa Ngày Tháng Ảnh Khảo Sát")

# 1. Tự động tải phông chữ nét mảnh chuẩn nếu chưa có sẵn
FONT_FILE = "Roboto-Regular.ttf"
if not os.path.exists(FONT_FILE):
    try:
        font_url = "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Regular.ttf"
        urllib.request.urlretrieve(font_url, FONT_FILE)
    except Exception:
        pass

uploaded_files = st.file_uploader("Tải lên danh sách ảnh (JPG, PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

new_date = st.text_input("Ngày tháng năm mới mong muốn:", "2026/09/23 16:22:53")

st.subheader("Cấu hình vị trí văn bản (Góc dưới bên trái)")
col1, col2 = st.columns(2)
with col1:
    crop_x = st.number_input("Tọa độ X góc trái chữ:", value=15)
    crop_y = st.number_input("Tọa độ Y góc trên chữ:", value=965)
    font_size = st.number_input("Kích thước phông chữ:", value=22)
with col2:
    crop_w = st.number_input("Chiều rộng vùng xóa:", value=250)
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

            # Xử lý vùng xóa chữ cũ
            y1, y2 = max(0, int(crop_y)), min(h, int(crop_y + crop_h))
            x1, x2 = max(0, int(crop_x)), min(w, int(crop_x + crop_w))
            roi = img[y1:y2, x1:x2]

            if roi.size > 0:
                gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                _, text_mask = cv2.threshold(gray_roi, 160, 255, cv2.THRESH_BINARY)
                
                kernel = np.ones((2, 2), np.uint8)
                text_mask = cv2.dilate(text_mask, kernel, iterations=1)

                cleaned_roi = cv2.inpaint(roi, text_mask, inpaintRadius=1, flags=cv2.INPAINT_TELEA)
                img[y1:y2, x1:x2] = cleaned_roi

            # Viết chữ mới bằng Pillow với phông chữ Roboto
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)
            draw = ImageDraw.Draw(pil_img)

            # Khởi tạo phông chữ
            if os.path.exists(FONT_FILE):
                font = ImageFont.truetype(FONT_FILE, int(font_size))
            else:
                font = ImageFont.load_default()

            # Viết chữ màu trắng kèm viền đổ bóng nhẹ nét mảnh
            draw.text((int(crop_x) + 1, int(crop_y) + 1), new_date, fill=(60, 60, 60), font=font)
            draw.text((int(crop_x), int(crop_y)), new_date, fill=(255, 255, 255), font=font)

            # Lưu file ảnh
            final_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            _, encoded_img = cv2.imencode(".jpg", final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 98])
            zip_file.writestr(f"edited_{uploaded_file.name}", encoded_img.tobytes())

    st.success("✅ Hoàn tất xử lý!")
    st.download_button(
        label="📥 Tải về file ZIP tất cả ảnh đã sửa",
        data=zip_buffer.getvalue(),
        file_name="danh_sach_anh_da_sua.zip",
        mime="application/zip"
    )
