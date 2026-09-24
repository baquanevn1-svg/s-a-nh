import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile
import os
import urllib.request

st.title("📷 Công cụ Sửa Ngày Tháng Ảnh Khảo Sát")

# Hàm nạp phông chữ đảm bảo thành công 100%
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

new_date = st.text_input("Ngày tháng năm mới mong muốn:", "2026/09/23 16:22:53")

st.subheader("Cấu hình vị trí văn bản (Góc dưới bên trái)")
col1, col2 = st.columns(2)
with col1:
    crop_x = st.number_input("Tọa độ X góc trái chữ:", value=15)
    crop_y = st.number_input("Tọa độ Y góc trên chữ:", value=1400)
    font_size = st.number_input("Kích thước phông chữ:", value=22)
with col2:
    crop_w = st.number_input("Chiều rộng vùng xóa:", value=250)
    crop_h = st.number_input("Chiều cao vùng xóa:", value=35)

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

            # 1. Tách và xóa nét chữ cũ giữ nguyên 100% vân gạch
            y1, y2 = max(0, actual_y), min(h, actual_y + actual_h)
            x1, x2 = max(0, actual_x), min(w, actual_x + actual_w)
            roi = img[y1:y2, x1:x2]

            if roi.size > 0:
                gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                _, text_mask = cv2.threshold(gray_roi, 170, 255, cv2.THRESH_BINARY)
                cleaned_roi = cv2.inpaint(roi, text_mask, inpaintRadius=1, flags=cv2.INPAINT_TELEA)
                img[y1:y2, x1:x2] = cleaned_roi

            # 2. Tạo chữ mới chuẩn nét
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)
            
            font = load_custom_font(int(font_size))

            if font is not None:
                # Nếu nạp thành công phông Roboto
                draw = ImageDraw.Draw(pil_img)
                draw.text((actual_x + 1, actual_y + 1), new_date, fill=(40, 40, 40), font=font)
                draw.text((actual_x, actual_y), new_date, fill=(255, 255, 255), font=font)
            else:
                # Dự phòng nếu không có mạng: Ph phóng đại phông chữ chính xác theo font_size
                scale_factor = font_size / 10.0
                temp_font = ImageFont.load_default()
                
                # Tạo lớp chữ nét phóng đại
                txt_img = Image.new('RGBA', (300, 30), (0, 0, 0, 0))
                txt_draw = ImageDraw.Draw(txt_img)
                txt_draw.text((1, 1), new_date, fill=(40, 40, 40), font=temp_font)
                txt_draw.text((0, 0), new_date, fill=(255, 255, 255), font=temp_font)
                
                new_w = int(txt_img.width * scale_factor)
                new_h = int(txt_img.height * scale_factor)
                resized_txt = txt_img.resize((new_w, new_h), Image.NEAREST)
                pil_img.paste(resized_txt, (actual_x, actual_y), resized_txt)

            # Xuất file ảnh
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
