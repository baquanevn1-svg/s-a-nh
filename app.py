import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile
import os
import urllib.request

st.set_page_config(page_title="vTools Auto Font Scale", layout="wide")
st.title("📷 vTools Pro: Tự Động Tỷ Lệ Kích Thước Chữ (Không Bị Nhỏ Xíu)")

@st.cache_resource
def load_vtools_font(font_size):
    # Tải phông chữ Roboto Condensed chuẩn nguyên mẫu vTools
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

st.subheader("2. Điều chỉnh kích thước & Vị trí chữ")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Căn chỉnh tỷ lệ phông chữ:**")
    # Tỷ lệ phần trăm phông chữ so với chiều cao ảnh (mặc định ~2.3% giúp chữ vừa vặn như gốc)
    font_scale_pct = st.slider("Tỷ lệ kích thước chữ (% chiều cao ảnh):", min_value=1.0, max_value=5.0, value=2.3, step=0.1)
    stroke_scale_pct = st.slider("Độ dày viền bóng đen ôm chữ:", min_value=1, max_value=4, value=2, step=1)

with col2:
    st.markdown("**Vị trí dòng ngày tháng năm:**")
    margin_left_pct = st.number_input("Cách lề trái (% chiều rộng ảnh):", value=2.5)
    margin_bottom_pct = st.number_input("Khoảng cách dòng ngày so với đáy (% chiều cao ảnh):", value=6.5)

if uploaded_files:
    first_file = uploaded_files[0]
    file_bytes = np.asarray(bytearray(first_file.read()), dtype=np.uint8)
    first_file.seek(0)
    preview_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
    if preview_img is not None:
        p_h, p_w, _ = preview_img.shape
        
        # Tính toán thông số kích thước thực tế dựa trên độ phân giải ảnh
        calc_font_size = int(p_h * (font_scale_pct / 100.0))
        calc_m_left = int(p_w * (margin_left_pct / 100.0))
        calc_m_bottom = int(p_h * (margin_bottom_pct / 100.0))
        
        y_l1 = p_h - calc_m_bottom - calc_font_size
        box_y1 = int(y_l1 - 10)
        box_y2 = int(y_l1 + calc_font_size + 10)
        clean_w = int(p_w * 0.45) # Quét 45% chiều rộng ảnh
        
        cv2.rectangle(
            preview_img, 
            (calc_m_left, box_y1), 
            (calc_m_left + clean_w, box_y2), 
            (0, 0, 255), 2
        )
        st.image(
            cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB), 
            caption=f"📌 Xem trước: Kích thước phông chữ tự tính toán là {calc_font_size}px (Khung đỏ thể hiện vùng xóa dòng ngày tháng cũ).", 
            use_container_width=True
        )

def process_vtools_auto_scale(img, l1_str, f_scale, m_left_p, m_bottom_p, s_width):
    h_img, w_img, _ = img.shape

    # Tự động tính toán kích thước pixel theo độ phân giải của từng tấm ảnh
    f_size = max(12, int(h_img * (f_scale / 100.0)))
    m_left = int(w_img * (m_left_p / 100.0))
    m_bottom = int(h_img * (m_bottom_p / 100.0))
    c_w = int(w_img * 0.48)

    y_l1 = int(h_img - m_bottom - f_size)

    x1 = int(m_left)
    x2 = int(m_left + c_w)
    y1 = int(y_l1 - int(f_size * 0.3))
    y2 = int(y_l1 + f_size + int(f_size * 0.3))

    x1, x2 = max(0, x1), min(w_img, x2)
    y1, y2 = max(0, y1), min(h_img, y2)

    # BƯỚC 1: XÓA SẠCH DÒNG CHỮ NGÀY THÁNG CỦ (GIỮ NỀN NGUYÊN BẢN)
    roi = img[y1:y2, x1:x2]
    if roi.size > 0:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
        _, mask1 = cv2.threshold(tophat, 20, 255, cv2.THRESH_BINARY)
        _, mask2 = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)
        
        combined_mask = cv2.bitwise_or(mask1, mask2)
        dilated_mask = cv2.dilate(combined_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2)), iterations=1)

        img[y1:y2, x1:x2] = cv2.inpaint(roi, dilated_mask, inpaintRadius=2, flags=cv2.INPAINT_TELEA)

    # BƯỚC 2: IN DÒNG NGÀY THÁNG MỚI VỚI TỶ LỆ CHUẨN ĐẸP
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    base_pil = Image.fromarray(img_rgb).convert("RGBA")

    font = load_vtools_font(int(f_size))

    text_layer = Image.new("RGBA", base_pil.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)

    if l1_str:
        text_pos = (x1, y_l1)
        
        # Viền bóng đen tỷ lệ theo kích thước chữ
        draw.text(
            text_pos, 
            l1_str, 
            font=font, 
            fill=(255, 255, 255, 255), 
            stroke_width=int(s_width), 
            stroke_fill=(0, 0, 0, 220)
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

            final_img = process_vtools_auto_scale(
                img, 
                line1, 
                font_scale_pct, 
                margin_left_pct, 
                margin_bottom_pct, 
                stroke_scale_pct
            )

            _, encoded_img = cv2.imencode(".jpg", final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 99])
            zip_file.writestr(f"edited_{uploaded_file.name}", encoded_img.tobytes())

    st.success("✅ Đã hoàn tất! Kích thước chữ tự động căn chỉnh đồng đều và vừa vặn trên mọi bức ảnh.")
    st.download_button(
        label="📥 Tải về file ZIP kết quả",
        data=zip_buffer.getvalue(),
        file_name="vtools_auto_scale_result.zip",
        mime="application/zip"
    )
