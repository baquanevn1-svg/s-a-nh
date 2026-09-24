import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import zipfile
import os
import urllib.request

st.title("📷 Công cụ Sửa Ngày Tháng Ảnh Khảo Sát (vTools Survey)")

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

st.subheader("1. Nội dung thay thế")
line1 = st.text_input("Dòng áp chót (Ngày tháng):", "Thứ Bảy, 22 tháng 2 2026")
line2 = st.text_input("Dòng cuối cùng (Giờ & GMT):", "09:52:23 GMT+07:00")

st.subheader("2. Thông số vị trí & Cỡ chữ")
col1, col2 = st.columns(2)
with col1:
    crop_x = st.number_input("Tọa độ X góc trái:", value=37)
    crop_y = st.number_input("Tọa độ Y góc trên:", value=1800)
    font_size = st.number_input("Kích thước phông chữ:", value=30)
    line_spacing = st.number_input("Khoảng cách 2 dòng:", value=36)
with col2:
    crop_w = st.number_input("Chiều rộng vùng xóa:", value=380)
    crop_h = st.number_input("Chiều cao vùng xóa:", value=80)

if uploaded_files:
    first_file = uploaded_files[0]
    file_bytes = np.asarray(bytearray(first_file.read()), dtype=np.uint8)
    first_file.seek(0)
    preview_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
    if preview_img is not None:
        p_h, p_w, _ = preview_img.shape
        cv2.rectangle(
            preview_img, 
            (int(crop_x), int(crop_y)), 
            (int(crop_x + crop_w), int(crop_y + crop_h)), 
            (0, 0, 255), 2
        )
        st.image(
            cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB), 
            caption=f"Khung đỏ vị trí xử lý (Kích thước ảnh: {p_w}x{p_h})", 
            use_container_width=True
        )

if uploaded_files and st.button("🚀 Bắt đầu Thay Thế (Xử lý đồng bộ nền ảnh sáng & tối)"):
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

            y1, y2 = max(0, actual_y), min(h, actual_y + actual_h)
            x1, x2 = max(0, actual_x), min(w, actual_x + actual_w)
            roi = img[y1:y2, x1:x2]

            # 1. BƯỚC XÓA CHỮ NGUYÊN BẢN (KHÔNG ĐỂ LẠI MẢNG HỘP XÁM CẮT NGANG)
            if roi.size > 0:
                gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                # Nhận diện chính xác nét chữ cũ
                _, text_mask = cv2.threshold(gray_roi, 160, 255, cv2.THRESH_BINARY)
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                text_mask = cv2.dilate(text_mask, kernel, iterations=1)
                
                # Trám lại bằng thuật toán Navier-Stokes giúp hòa tan đường biên
                cleaned_roi = cv2.inpaint(roi, text_mask, inpaintRadius=2, flags=cv2.INPAINT_NS)
                img[y1:y2, x1:x2] = cleaned_roi

            # 2. XỬ LÝ LỚP NỀN MỜ GRADIENT ĐỒNG BỘ TỰ NHIÊN
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            base_pil = Image.fromarray(img_rgb).convert("RGBA")
            
            # Tạo lớp phủ mờ tự nhiên hòa quyện mềm mại (không bị góc vuông)
            overlay_layer = Image.new("RGBA", base_pil.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay_layer)

            # Mở rộng vùng mờ ra rộng hơn để viền nhòe mịn vào ảnh gốc
            pad_x1 = max(0, actual_x - 20)
            pad_y1 = max(0, actual_y - 12)
            pad_x2 = min(w, actual_x + actual_w + 40)
            pad_y2 = min(h, actual_y + actual_h + 15)

            # Phủ một lớp bóng mờ nhẹ 
            overlay_draw.rectangle([pad_x1, pad_y1, pad_x2, pad_y2], fill=(0, 0, 0, 90))
            
            # Làm nhòe viền (Gaussian Blur) với bán kính lớn để triệt tiêu hoàn toàn góc cạnh
            overlay_layer = overlay_layer.filter(ImageFilter.GaussianBlur(radius=18))

            # 3. VẼ CHỮ MỚI
            text_layer = Image.new("RGBA", base_pil.size, (0, 0, 0, 0))
            text_draw = ImageDraw.Draw(text_layer)

            font = load_custom_font(int(font_size))
            if font is None:
                font = ImageFont.load_default()

            y_line1 = actual_y + 4
            y_line2 = actual_y + 4 + int(line_spacing)

            if line1:
                # Viền đen mỏng xung quanh nét chữ
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    text_draw.text((actual_x + dx, y_line1 + dy), line1, fill=(0, 0, 0, 220), font=font)
                text_draw.text((actual_x, y_line1), line1, fill=(255, 255, 255, 255), font=font)

            if line2:
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    text_draw.text((actual_x + dx, y_line2 + dy), line2, fill=(0, 0, 0, 220), font=font)
                text_draw.text((actual_x, y_line2), line2, fill=(255, 255, 255, 255), font=font)

            # Ghép các lớp ảnh: Ảnh gốc -> Lớp mờ mịn mềm -> Dòng chữ trắng
            final_pil = Image.alpha_composite(base_pil, overlay_layer)
            final_pil = Image.alpha_composite(final_pil, text_layer).convert("RGB")

            # Xuất ảnh
            final_img = cv2.cvtColor(np.array(final_pil), cv2.COLOR_RGB2BGR)
            _, encoded_img = cv2.imencode(".jpg", final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 98])
            zip_file.writestr(f"edited_{uploaded_file.name}", encoded_img.tobytes())

    st.success("✅ Đã xử lý xong! Cả ảnh trời sáng và ảnh nền tối đều đồng bộ tự nhiên.")
    st.download_button(
        label="📥 Tải về file ZIP tất cả ảnh đã xử lý",
        data=zip_buffer.getvalue(),
        file_name="danh_sach_anh_da_sua.zip",
        mime="application/zip"
    )
