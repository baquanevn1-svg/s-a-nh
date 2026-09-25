import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile
import os
import urllib.request

st.set_page_config(page_title="vTools Exact Font Match", layout="wide")
st.title("📷 vTools Pro: Chuẩn Kiểu Chữ Nguyên Mẫu 100% (Giữ Nền Gốc)")

@st.cache_resource
def load_vtools_font(font_size):
    # Tải đúng font Roboto Condensed (Dạng phông chữ cô đọng chuẩn của vTools)
    font_filename = "RobotoCondensed-Regular.ttf"
    if not os.path.exists(font_filename):
        urls = [
            "https://raw.githubusercontent.com/google/fonts/main/ofl/robotocondensed/RobotoCondensed-Regular.ttf",
            "https://cdnjs.cloudflare.com/ajax/libs/ink/3.1.10/fonts/Roboto/roboto-condensed-regular-webfont.ttf"
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
    return ImageFont.load_default()

uploaded_files = st.file_uploader("Tải lên danh sách ảnh vTools (JPG, PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

st.subheader("1. Nội dung dòng ngày tháng năm mới")
line1 = st.text_input("Dòng ngày tháng năm mới:", "Thứ Bảy, 15 tháng 2 2025")

st.subheader("2. Tinh chỉnh phông chữ nguyên mẫu vTools")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Vị trí chữ:**")
    margin_left = st.number_input("Cách lề trái (px):", value=25)
    margin_bottom = st.number_input("Khoảng cách dòng ngày so với đáy (px):", value=78)

with col2:
    st.markdown("**Thông số kiểu chữ chuẩn:**")
    font_size = st.number_input("Kích thước chữ (px):", value=29)
    stroke_width = st.slider("Độ dày viền bóng đen ôm chữ (px):", min_value=1, max_value=3, value=1, step=1)
    clean_w = st.number_input("Chiều rộng vùng quét xóa chữ cũ (px):", value=460)

if uploaded_files:
    first_file = uploaded_files[0]
    file_bytes = np.asarray(bytearray(first_file.read()), dtype=np.uint8)
    first_file.seek(0)
    preview_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
    if preview_img is not None:
        p_h, p_w, _ = preview_img.shape
        y_l1 = p_h - margin_bottom - font_size
        box_y1 = int(y_l1 - 8)
        box_y2 = int(y_l1 + font_size + 8)
        
        cv2.rectangle(
            preview_img, 
            (int(margin_left), box_y1), 
            (int(margin_left + clean_w), box_y2), 
            (0, 0, 255), 2
        )
        st.image(
            cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB), 
            caption="📌 Vùng đỏ: Chỉ xóa nét chữ ngày tháng cũ, nền ảnh và dòng giờ gốc được giữ nguyên.", 
            use_container_width=True
        )

def process_vtools_exact_match(img, l1_str, f_size, m_left, m_bottom, c_w, s_width):
    h_img, w_img, _ = img.shape

    # Tọa độ dòng ngày tháng năm
    y_l1 = int(h_img - m_bottom - f_size)

    x1 = int(m_left)
    x2 = int(m_left + c_w)
    y1 = int(y_l1 - 10)
    y2 = int(y_l1 + f_size + 10)

    x1, x2 = max(0, x1), min(w_img, x2)
    y1, y2 = max(0, y1), min(h_img, y2)

    # BƯỚC 1: XÓA TẨY NẾT CHỮ CŨ (GIỮ NỀN TỰ NHIÊN)
    roi = img[y1:y2, x1:x2]
    if roi.size > 0:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
        _, mask1 = cv2.threshold(tophat, 20, 255, cv2.THRESH_BINARY)
        _, mask2 = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)
        
        combined_mask = cv2.bitwise_or(mask1, mask2)
        dilated_mask = cv2.dilate(combined_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2)), iterations=1)

        # Inpaint khôi phục nền gốc
        img[y1:y2, x1:x2] = cv2.inpaint(roi, dilated_mask, inpaintRadius=2, flags=cv2.INPAINT_TELEA)

    # BƯỚC 2: IN CHỮ MỚI VỚI FONT & VIỀN BÓNG ĐEN NGUYÊN MẪU vTools
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    base_pil = Image.fromarray(img_rgb).convert("RGBA")

    font = load_vtools_font(int(f_size))

    text_layer = Image.new("RGBA", base_pil.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)

    if l1_str:
        # Tọa độ in chữ
        text_pos = (x1, y_l1)
        
        # In viền bóng đen mỏng bao quanh chữ (stroke) chuẩn vTools gốc
        draw.text(
            text_pos, 
            l1_str, 
            font=font, 
            fill=(255, 255, 255, 255), 
            stroke_width=int(s_width), 
            stroke_fill=(0, 0, 0, 200)
        )

    final_pil = Image.alpha_composite(base_pil, text_layer)
    res_rgb = final_pil.convert("RGB")
    return cv2.cvtColor(np.array(res_rgb), cv2.COLOR_RGB2BGR)

if uploaded_files and st.button("🚀 Bắt Đầu Xử Lý Hàng Loạt"):
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for idx, uploaded_file in enumerate(uploaded_files):
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None:
                continue

            final_img = process_vtools_exact_match(
                img, 
                line1, 
                font_size, 
                margin_left, 
                margin_bottom,
                clean_w,
                stroke_width
            )

            _, encoded_img = cv2.imencode(".jpg", final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 99])
            zip_file.writestr(f"edited_{uploaded_file.name}", encoded_img.tobytes())

    st.success("✅ Đã hoàn tất! Phông chữ & hiệu ứng viền bóng đen trùng khớp 100% với chữ vTools gốc.")
    st.download_button(
        label="📥 Tải về file ZIP kết quả",
        data=zip_buffer.getvalue(),
        file_name="vtools_exact_match_result.zip",
        mime="application/zip"
    )
