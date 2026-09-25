import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile
import os
import urllib.request

st.set_page_config(page_title="vTools Exact Style", layout="wide")
st.title("📷 vTools Pro: Chuẩn Phông Chữ Gốc & Giữ Nguyên Nền")

@st.cache_resource
def get_vtools_condensed_font(font_size):
    # Tải font Roboto Condensed Regular (đúng font dáng hẹp nhẹ của vTools)
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
            return ImageFont.truetype(font_filename, int(font_size))
        except Exception:
            pass
            
    # Dự phòng
    try:
        return ImageFont.truetype("arial.ttf", int(font_size))
    except Exception:
        return ImageFont.load_default()

uploaded_files = st.file_uploader("Tải lên danh sách ảnh vTools (JPG, PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

st.subheader("1. Nội dung dòng ngày tháng năm mới")
line1 = st.text_input("Dòng ngày tháng năm mới:", "Thứ Bảy, 15 tháng 2 2025")

st.subheader("2. Tinh chỉnh theo nét chữ vTools gốc")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Căn chỉnh phông chữ:**")
    # Chuẩn cỡ chữ vTools gốc so với chiều cao ảnh
    font_size_pct = st.slider("Cỡ chữ (% chiều cao ảnh) - Gốc vTools là 2.2%:", min_value=1.5, max_value=4.0, value=2.2, step=0.1)
    text_opacity = st.slider("Độ trong suốt/đậm nét chữ (Gốc vTools ~ 230):", min_value=150, max_value=255, value=230, step=5)

with col2:
    st.markdown("**Tọa độ vị trí dòng ngày:**")
    margin_left_pct = st.number_input("Cách lề trái (% chiều rộng ảnh):", value=2.2)
    margin_bottom_pct = st.number_input("Khoảng cách dòng ngày so với đáy (% chiều cao ảnh):", value=6.2)

if uploaded_files:
    first_file = uploaded_files[0]
    file_bytes = np.asarray(bytearray(first_file.read()), dtype=np.uint8)
    first_file.seek(0)
    preview_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
    if preview_img is not None:
        p_h, p_w, _ = preview_img.shape
        
        calc_f_size = int(p_h * (font_size_pct / 100.0))
        calc_m_left = int(p_w * (margin_left_pct / 100.0))
        calc_m_bottom = int(p_h * (margin_bottom_pct / 100.0))
        
        y_l1 = p_h - calc_m_bottom - calc_f_size
        
        # Khung quét xóa nhỏ gọn sát nét chữ cũ
        y1 = int(y_l1 - 2)
        y2 = int(y_l1 + calc_f_size + 4)
        clean_w = int(p_w * 0.50)
        
        cv2.rectangle(
            preview_img, 
            (calc_m_left, y1), 
            (calc_m_left + clean_w, y2), 
            (0, 0, 255), 2
        )
        st.image(
            cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB), 
            caption=f"📌 Khung đỏ: Vùng quét xóa chữ cũ (Cỡ chữ chuẩn vTools: {calc_f_size}px).", 
            use_container_width=True
        )

def process_vtools_exact_match(img, l1_str, f_pct, m_left_p, m_bottom_p, opacity):
    h_img, w_img, _ = img.shape

    # 1. TÍNH TOÁN KÍCH THƯỚC PHÔNG CHỮ CHUẨN VTOOLS
    f_size = max(14, int(h_img * (f_pct / 100.0)))
    m_left = int(w_img * (m_left_p / 100.0))
    m_bottom = int(h_img * (m_bottom_p / 100.0))
    c_w = int(w_img * 0.52)

    y_l1 = int(h_img - m_bottom - f_size)

    # Vùng quét xóa đúng sát nét chữ
    x1 = int(m_left)
    x2 = int(m_left + c_w)
    y1 = max(0, int(y_l1 - 3))
    y2 = min(h_img, int(y_l1 + f_size + 3))
    x1, x2 = max(0, x1), min(w_img, x2)

    # 2. XÓA NÉT CHỮ CỦ BẰNG INPAINT - KHÔNG LÀM THAY ĐỔI MÀU NỀN BÊN DƯỚI
    roi = img[y1:y2, x1:x2]
    if roi.size > 0:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Chỉ nhận diện đúng các điểm ảnh chữ màu sáng
        _, mask = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        
        # Mở rộng cực nhẹ 1px để không bị lem sang nền
        dilated_mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)), iterations=1)

        # Thay thế điểm ảnh chữ bằng họa tiết nền gốc xung quanh
        img[y1:y2, x1:x2] = cv2.inpaint(roi, dilated_mask, inpaintRadius=2, flags=cv2.INPAINT_TELEA)

    # 3. CHÈN CHỮ MỚI VỚI DẠNG CONDENSED & NÉT CHỮ MỜ NHẸ GIỐNG HỆT ẢNH GỐC
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    base_pil = Image.fromarray(img_rgb).convert("RGBA")

    font = get_vtools_condensed_font(f_size)

    text_layer = Image.new("RGBA", base_pil.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)

    if l1_str:
        text_pos = (x1, y_l1)
        
        # Viền bóng siêu mỏng 1px màu đen nhẹ để nổi chữ trên nền sáng
        draw.text(
            text_pos, 
            l1_str, 
            font=font, 
            fill=(255, 255, 255, opacity), 
            stroke_width=1, 
            stroke_fill=(0, 0, 0, 120)
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
                font_size_pct, 
                margin_left_pct, 
                margin_bottom_pct, 
                text_opacity
            )

            _, encoded_img = cv2.imencode(".jpg", final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 99])
            zip_file.writestr(f"edited_{uploaded_file.name}", encoded_img.tobytes())

    st.success("✅ Đã xử lý xong! Dáng chữ và kích thước hoàn toàn trùng khớp các dòng gốc vTools.")
    st.download_button(
        label="📥 Tải về file ZIP kết quả",
        data=zip_buffer.getvalue(),
        file_name="vtools_exact_style_result.zip",
        mime="application/zip"
    )
