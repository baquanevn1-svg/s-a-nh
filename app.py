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
    crop_x = st.number_input("Tọa độ X góc trái chữ:", value=15)
    crop_y = st.number_input("Tọa độ Y góc trên chữ:", value=1400)
    font_size = st.number_input("Kích thước chữ mới:", value=22)
with col2:
    crop_w = st.number_input("Chiều rộng vùng xóa:", value=240)
    crop_h = st.number_input("Chiều cao vùng xóa:", value=28)

if uploaded_files and st.button("Xử lý ảnh"):
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for idx, uploaded_file in enumerate(uploaded_files):
            # Đọc ảnh
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            h, w, _ = img.shape

            # 1. Tạo Mask vừa sát khít chữ
            mask = np.zeros((h, w), np.uint8)
            y1, y2 = max(0, crop_y), min(h, crop_y + crop_h)
            x1, x2 = max(0, crop_x), min(w, crop_x + crop_w)
            mask[y1:y2, x1:x2] = 255

            # 2. Xóa chữ mịn bằng Navier-Stokes (bán kính nhỏ = 1 để không mất vân gạch)
            inpainted = cv2.inpaint(img, mask, inpaintRadius=1, flags=cv2.INPAINT_NS)

            # 3. Chèn chữ mới sắc nét
            img_rgb = cv2.cvtColor(inpainted, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)
            draw = ImageDraw.Draw(pil_img)

            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()

            # Viết dòng chữ màu trắng
            draw.text((crop_x + 2, crop_y + 2), new_date, fill=(255, 255, 255), font=font)

            # Lưu vào bộ nhớ ZIP
            out_img = io.BytesIO()
            pil_img.save(out_img, format="JPEG", quality=95)
            zip_file.writestr(f"edited_{uploaded_file.name}", out_img.getvalue())

    st.success("✅ Hoàn tất xử lý!")
    st.download_button(
        label="📥 Tải về file ZIP tất cả ảnh đã sửa",
        data=zip_buffer.getvalue(),
        file_name="danh_sach_anh_da_sua.zip",
        mime="application/zip"
    )
