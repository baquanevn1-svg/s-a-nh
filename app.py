import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile
import os
import urllib.request

st.set_page_config(page_title="vTools Direct Replacement", layout="wide")
st.title("📷 vTools Pro: Thay Thế Trực Tiếp Tại Vị Trí Cũ (Góc Trái)")

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

st.subheader("1. Nội dung 2 dòng cuối cần thay thế")
line1 = st.text_input("Dòng áp chót (Thứ, ngày tháng năm):", "Thứ Bảy, 15 tháng 2 2025")
line2 = st.text_input("Dòng cuối cùng (Giờ & GMT):", "09:28:23 GMT+07:00")

st.subheader("2. Căn chỉnh vị trí góc dưới bên trái")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Vị trí đè chữ (Tính từ góc dưới lề trái):**")
    margin_left = st.number_input("Căn lề trái (px):", value=25)
    margin_bottom = st.number_input("Căn lề đáy (px):", value=45)
    overlay_opacity = st.slider("Độ mờ màn đen đè chữ cũ:", min_value=0.05, max_value=0.40, value=0.18, step=0.01)

with col2:
    st.markdown("**Cấu hình phông chữ:**")
    font_size = st.number_input("Kích thước phông chữ (px):", value=28)
    line_spacing = st.number_input("Khoảng cách giữa 2 dòng (px):", value=34)
    box_width = st.number_input("Chiều rộng mảng che (px):", value=460)

if uploaded_files:
    first_file = uploaded_files[0]
    file_bytes = np.asarray(bytearray(first_file.read()), dtype=np.uint8)
    first_file.seek(0)
    preview_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
    if preview_img is not None:
        p_h, p_w, _ = preview_img.shape
        y_l2 = p_h - margin_bottom - font_size
        y_l1 = y_l2 - line_spacing
        box_y1 = int(y_l1 - 8)
        box_y2 = int(p_h - margin_bottom + 8)
        
        # Khung đỏ xem trước vị trí thay thế trực tiếp
        cv2.rectangle(
            preview_img, 
            (int(margin_left), box_y1), 
            (int(margin_left + box_width), box_y2), 
            (0, 0, 255), 2
        )
        st.image(
            cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB), 
            caption="📌 Chữ mới sẽ được đè thẳng vào đúng vị trí khung đỏ ở góc trái.", 
            use_container_width=True
        )

def replace_text_directly_at_left(img, l1_str, l2_str, f_size, l_spacing, m_left, m_bottom, b_width, opacity):
    h_img, w_img, _ = img.shape

    # 1. Tọa độ chính xác ở góc dưới lề trái
    y_l2 = int(h_img - m_bottom - f_size)
    y_l1 = int(y_l2 - l_spacing)

    x1 = int(m_left)
    x2 = int(m_left + b_width)
    y1 = int(y_l1 - 10)
    y2 = int(h_img - m_bottom + 10)

    x1, x2 = max(0, x1), min(w_img, x2)
    y1, y2 = max(0, y1), min(h_img, y2)

    # 2. Phủ màn đen mờ che thẳng chữ cũ (Không cần xóa/Inpaint phức tạp)
    if opacity > 0:
        overlay = img.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 0), -1)

        mask = np.zeros((h_img, w_img), dtype=np.float32)
        mask[y1:y2, x1:x2] = opacity
        mask = cv2.GaussianBlur(mask, (21, 21), 0) # Mờ mềm mép màn đen
        mask_3ch = cv2.merge([mask, mask, mask])

        img_blended = (overlay.astype(np.float32) * mask_3ch + img.astype(np.float32) * (1.0 - mask_3ch))
        img = np.clip(img_blended, 0, 255).astype(np.uint8)

    # 3. Vẽ chữ trắng mới lên trên
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb).convert("RGBA")

    font = load_custom_font(int(f_size))
    if font is None:
        font = ImageFont.load_default()

    text_layer = Image.new("RGBA", pil_img.size, (0, 0, 0, 0))
    draw_text = ImageDraw.Draw(text_layer)

    if l1_str:
        draw_text.text((x1, y_l1), l1_str, fill=(255, 255, 255, 255), font=font)
    if l2_str:
        draw_text.text((x1, y_l2), l2_str, fill=(255, 255, 255, 255), font=font)

    composed = Image.alpha_composite(pil_img, text_layer)
    res_rgb = composed.convert("RGB")
    return cv2.cvtColor(np.array(res_rgb), cv2.COLOR_RGB2BGR)

if uploaded_files and st.button("🚀 Bắt Đầu Thay Thế Trực Tiếp Hàng Loạt"):
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for idx, uploaded_file in enumerate(uploaded_files):
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None:
                continue

            final_img = replace_text_directly_at_left(
                img, 
                line1, 
                line2, 
                font_size, 
                line_spacing, 
                margin_left, 
                margin_bottom,
                box_width,
                overlay_opacity
            )

            _, encoded_img = cv2.imencode(".jpg", final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 99])
            zip_file.writestr(f"edited_{uploaded_file.name}", encoded_img.tobytes())

    st.success("✅ Đã xử lý xong! Chữ mới đè chính xác vị trí góc trái, sạch sẽ và không lỗi nền.")
    st.download_button(
        label="📥 Tải về file ZIP kết quả",
        data=zip_buffer.getvalue(),
        file_name="vtools_thay_truc_tiep_goc_trai.zip",
        mime="application/zip"
    )
