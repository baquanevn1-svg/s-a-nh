import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile
import os

st.title("📷 Công cụ Sửa Ngày Tháng Ảnh Khảo Sát")

uploaded_files = st.file_uploader("Tải lên danh sách ảnh (JPG, PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

new_date = st.text_input("Ngày tháng năm mới mong muốn:", "2026/09/23 16:22:53")

st.subheader("Cấu hình vị trí văn bản (Góc dưới bên trái)")
col1, col2 = st.columns(2)
with col1:
    crop_x = st.number_input("Tọa độ X góc trái chữ:", value=10)
    crop_y = st.number_input("Tọa độ Y góc trên chữ:", value=965)
    font_size = st.number_input("Kích thước phông chữ:", value=15)
with col2:
    crop_w = st.number_input("Chiều rộng vùng xóa:", value=220)
    crop_h = st.number_input("Chiều cao vùng xóa:", value=25)

if uploaded_files and st.button("Xử lý ảnh"):
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for idx, uploaded_file in enumerate(uploaded_files):
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None:
                continue
            h, w, _ = img.shape

            # Lấy vị trí vùng xóa (tự động điều chỉnh theo tỉ lệ kích thước ảnh gốc)
            # Tỉ lệ tính theo ảnh mẫu chuẩn (1000x1000)
            scale_ratio = h / 1000.0
            actual_x = int(crop_x * scale_ratio)
            actual_y = int(crop_y * scale_ratio)
            actual_w = int(crop_w * scale_ratio)
            actual_h = int(crop_h * scale_ratio)
            actual_font_size = int(font_size * scale_ratio)

            # 1. Tách nét chữ sáng màu
            y1, y2 = max(0, actual_y), min(h, actual_y + actual_h)
            x1, x2 = max(0, actual_x), min(w, actual_x + actual_w)
            roi = img[y1:y2, x1:x2]

            if roi.size > 0:
                gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                _, text_mask = cv2.threshold(gray_roi, 160, 255, cv2.THRESH_BINARY)
                
                kernel = np.ones((2, 2), np.uint8)
                text_mask = cv2.dilate(text_mask, kernel, iterations=1)

                cleaned_roi = cv2.inpaint(roi, text_mask, inpaintRadius=1, flags=cv2.INPAINT_TELEA)
                img[y1:y2, x1:x2] = cleaned_roi

            # 2. Chuyển sang PIL để viết chữ chuẩn phông nét mảnh
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)
            draw = ImageDraw.Draw(pil_img)

            # Nạp font Sans-Serif chuẩn hệ thống Linux Server
            font = None
            font_paths = [
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "LiberationSans-Regular.ttf",
                "DejaVuSans.ttf"
            ]
            for path in font_paths:
                if os.path.exists(path):
                    try:
                        font = ImageFont.truetype(path, actual_font_size)
                        break
                    except:
                        pass
            
            if font is None:
                font = ImageFont.load_default()

            # Viết chữ màu trắng nét mảnh kèm bóng đổ nhẹ chuẩn như ảnh gốc
            draw.text((actual_x + 1, actual_y + 1), new_date, fill=(50, 50, 50), font=font)
            draw.text((actual_x, actual_y), new_date, fill=(255, 255, 255), font=font)

            # Chuyển ngược lại để xuất file
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
