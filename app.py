import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile
import os
import urllib.request

st.title("📷 Công cụ Sửa Ngày Tháng Ảnh Khảo Sát (2 Dòng Cuối)")

# Nạp phông chữ Roboto mỏng chuẩn ứng dụng
@st.cache_resource
def load_custom_font(font_size):
    font_filename = "Roboto-Regular.ttf"
    if not os.path.exists(font_filename):
        urls = [
            "https://raw.githubusercontent.com/google/fonts/main/apache/roboto/Roboto-Regular.ttf",
            "https://cdnjs.cloudflare.com/ajax/libs/ink/3.1.10/fonts/Roboto/roboto-regular-webfont.ttf"
        ]
        for url in urls:
            try:
                urllib.request.urlretrieve(url, font_filename)
                if os.path.exists(font_filename) and os.path.getsize(font_filename) > 0:
                    break
            except Exception:
                continue

    if os.path.exists(font_filename) and os.path.getsize(font_filename) > 0:
        try:
            return ImageFont.truetype(font_filename, font_size)
        except Exception:
            pass
    return None

uploaded_files = st.file_uploader("Tải lên danh sách ảnh (JPG, PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

st.subheader("Nhập thông tin thay thế")
line1 = st.text_input("Dòng áp chót (Ngày tháng):", "Thứ Bảy, 15 tháng 2 2025")
line2 = st.text_input("Dòng cuối cùng (Giờ & GMT):", "09:28:23 GMT+07:00")

st.subheader("Cấu hình vị trí văn bản")
col1, col2 = st.columns(2)
with col1:
    crop_x = st.number_input("Tọa độ X góc trái:", value=50)
    crop_y = st.number_input("Tọa độ Y góc trên (Bắt đầu vùng 2 dòng cuối):", value=920)
    font_size = st.number_input("Kích thước phông chữ (Mặc định 18-22):", value=20)
    line_spacing = st.number_input("Khoảng cách giữa 2 dòng:", value=24)
with col2:
    crop_w = st.number_input("Chiều rộng vùng xóa:", value=320)
    crop_h = st.number_input("Chiều cao vùng xóa (Xóa cả 2 dòng):", value=55)

if uploaded_files and st.button("Xử lý ảnh"):
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for idx, uploaded_file in enumerate(uploaded_files):
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None:
                continue
            h, w, _ = img.shape

            actual_x = int(crop_x)
            actual_y = int(crop_y)
            actual_w = int(crop_w)
            actual_h = int(crop_h)

            # 1. Xóa 2 dòng chữ cũ giữ nguyên 100% nền phía sau
            y1, y2 = max(0, actual_y), min(h, actual_y + actual_h)
            x1, x2 = max(0, actual_x), min(w, actual_x + actual_w)
            roi = img[y1:y2, x1:x2]

            if roi.size > 0:
                gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                _, text_mask = cv2.threshold(gray_roi, 160, 255, cv2.THRESH_BINARY)
                # Bán kính 1px giữ trọn vẹn chi tiết nền
                cleaned_roi = cv2.inpaint(roi, text_mask, inpaintRadius=1, flags=cv2.INPAINT_TELEA)
                img[y1:y2, x1:x2] = cleaned_roi

            # 2. Chuyển sang PIL vẽ 2 dòng chữ nét mảnh chuẩn phông gốc
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)
            draw = ImageDraw.Draw(pil_img)

            font = load_custom_font(int(font_size))
            if font is None:
                font = ImageFont.load_default()

            # Tọa độ dòng 1
            y_line1 = actual_y
            # Tọa độ dòng 2
            y_line2 = actual_y + int(line_spacing)

            # Vẽ dòng 1 (Ngày tháng)
            if line1:
                draw.text((actual_x + 1, y_line1 + 1), line1, fill=(30, 30, 30), font=font)
                draw.text((actual_x, y_line1), line1, fill=(255, 255, 255), font=font)

            # Vẽ dòng 2 (Giờ + GMT)
            if line2:
                draw.text((actual_x + 1, y_line2 + 1), line2, fill=(30, 30, 30), font=font)
                draw.text((actual_x, y_line2), line2, fill=(255, 255, 255), font=font)

            # Xuất file
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
