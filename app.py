import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import zipfile
import os
import urllib.request

st.set_page_config(page_title="vTools Replace Date Only", layout="wide")
st.title("📷 vTools Pro: Chỉ Thay Dòng Ngày Tháng (Giữ Nguyên Dòng Giờ Gốc)")

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

uploaded_files = st.file_uploader("Tải lên danh sách ảnh vTools (JPG, PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

st.subheader("1. Nội dung dòng ngày tháng năm mới")
line1 = st.text_input("Dòng ngày tháng năm mới:", "Thứ Bảy, 15 tháng 2 2025")

st.subheader("2. Điều chỉnh vị trí & Phông chữ")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Vị trí chữ:**")
    margin_left = st.number_input("Cách lề trái (px):", value=25)
    margin_bottom = st.number_input("Khoảng cách dòng ngày so với đáy (px):", value=79)
    shadow_alpha = st.slider("Độ mờ bóng chữ mới (0 = Không bóng, 100 = Rõ nhẹ):", min_value=0, max_value=150, value=60, step=10)

with col2:
    st.markdown("**Cấu hình phông chữ:**")
    font_size = st.number_input("Kích thước phông chữ (px):", value=28)
    clean_w = st.number_input("Chiều rộng vùng quét chữ cũ (px):", value=460)

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
            caption="📌 Khung đỏ: Vùng chỉ xóa duy nhất dòng ngày tháng năm (Dòng giờ gốc ở dưới được giữ nguyên 100%).", 
            use_container_width=True
        )

def process_vtools_date_only(img, l1_str, f_size, m_left, m_bottom, c_w, s_alpha):
    h_img, w_img, _ = img.shape

    # Tọa độ duy nhất cho dòng áp chót (ngày tháng năm)
    y_l1 = int(h_img - m_bottom - f_size)

    x1 = int(m_left)
    x2 = int(m_left + c_w)
    y1 = int(y_l1 - 10)
    y2 = int(y_l1 + f_size + 10)

    x1, x2 = max(0, x1), min(w_img, x2)
    y1, y2 = max(0, y1), min(h_img, y2)

    # 1. BƯỚC 1: CHỈ XÓA CHÍNH XÁC DÒNG CHỮ NGÀY THÁNG NĂM CỦ
    roi = img[y1:y2, x1:x2]
    if roi.size > 0:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Bóc tách chính xác nét chữ màu trắng dòng ngày tháng
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
        _, mask1 = cv2.threshold(tophat, 20, 255, cv2.THRESH_BINARY)
        _, mask2 = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)
        
        combined_mask = cv2.bitwise_or(mask1, mask2)
        dilated_mask = cv2.dilate(combined_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2)), iterations=1)

        # Tẩy sạch nét chữ cũ
        img[y1:y2, x1:x2] = cv2.inpaint(roi, dilated_mask, inpaintRadius=2, flags=cv2.INPAINT_TELEA)

    # 2. BƯỚC 2: IN DÒNG NGÀY THÁNG NĂM MỚI
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    base_pil = Image.fromarray(img_rgb).convert("RGBA")

    font = load_custom_font(int(f_size))
    if font is None:
        font = ImageFont.load_default()

    # Tạo bóng mờ nhẹ dưới dòng ngày tháng năm mới
    if s_alpha > 0 and l1_str:
        shadow_layer = Image.new("RGBA", base_pil.size, (0, 0, 0, 0))
        draw_shadow = ImageDraw.Draw(shadow_layer)
        draw_shadow.text((x1 + 1, y_l1 + 1), l1_str, fill=(0, 0, 0, int(s_alpha)), font=font)
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=0.8))
        base_pil = Image.alpha_composite(base_pil, shadow_layer)

    # In dòng chữ trắng mới
    if l1_str:
        text_layer = Image.new("RGBA", base_pil.size, (0, 0, 0, 0))
        draw_text = ImageDraw.Draw(text_layer)
        draw_text.text((x1, y_l1), l1_str, fill=(255, 255, 255, 255), font=font)
        base_pil = Image.alpha_composite(base_pil, text_layer)

    res_rgb = base_pil.convert("RGB")
    return cv2.cvtColor(np.array(res_rgb), cv2.COLOR_RGB2BGR)

if uploaded_files and st.button("🚀 Bắt Đầu Xử Lý Hàng Loạt"):
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for idx, uploaded_file in enumerate(uploaded_files):
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None:
                continue

            final_img = process_vtools_date_only(
                img, 
                line1, 
                font_size, 
                margin_left, 
                margin_bottom,
                clean_w,
                shadow_alpha
            )

            _, encoded_img = cv2.imencode(".jpg", final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 99])
            zip_file.writestr(f"edited_{uploaded_file.name}", encoded_img.tobytes())

    st.success("✅ Đã hoàn tất! Dòng ngày tháng năm đã được đổi mới, dòng giờ GMT gốc giữ nguyên 100%.")
    st.download_button(
        label="📥 Tải về file ZIP kết quả",
        data=zip_buffer.getvalue(),
        file_name="vtools_date_replaced.zip",
        mime="application/zip"
    )
