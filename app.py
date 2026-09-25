import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import zipfile
import os
import urllib.request

st.set_page_config(page_title="vTools Clean & Replace", layout="wide")
st.title("📷 vTools Pro: Xóa Sạch Chữ Cũ Rồi Mới Thay Chữ Mới")

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

st.subheader("2. Tùy chỉnh vị trí và độ mờ nền")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Vị trí 2 dòng cuối (Góc lề trái dưới):**")
    margin_left = st.number_input("Cách lề trái (px):", value=25)
    margin_bottom = st.number_input("Cách lề đáy (px):", value=45)
    shadow_opacity = st.slider("Độ đậm bóng đen sau chữ mới:", min_value=0.0, max_value=0.30, value=0.12, step=0.01)

with col2:
    st.markdown("**Cấu hình chữ vTools:**")
    font_size = st.number_input("Kích thước phông chữ (px):", value=28)
    line_spacing = st.number_input("Khoảng cách giữa 2 dòng (px):", value=34)
    clean_w = st.number_input("Chiều rộng vùng xóa chữ cũ (px):", value=460)

if uploaded_files:
    first_file = uploaded_files[0]
    file_bytes = np.asarray(bytearray(first_file.read()), dtype=np.uint8)
    first_file.seek(0)
    preview_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
    if preview_img is not None:
        p_h, p_w, _ = preview_img.shape
        y_l2 = p_h - margin_bottom - font_size
        y_l1 = y_l2 - line_spacing
        box_y1 = int(y_l1 - 10)
        box_y2 = int(p_h - margin_bottom + 10)
        
        cv2.rectangle(
            preview_img, 
            (int(margin_left), box_y1), 
            (int(margin_left + clean_w), box_y2), 
            (0, 0, 255), 2
        )
        st.image(
            cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB), 
            caption="📌 Khung đỏ là vùng sẽ được XÓA SẠCH chữ cũ trước khi chèn chữ mới.", 
            use_container_width=True
        )

def clean_old_text_and_draw_new(img, l1_str, l2_str, f_size, l_spacing, m_left, m_bottom, c_w, opacity):
    h_img, w_img, _ = img.shape

    # Tọa độ vùng 2 dòng chữ cuối
    y_l2 = int(h_img - m_bottom - f_size)
    y_l1 = int(y_l2 - l_spacing)

    x1 = int(m_left)
    x2 = int(m_left + c_w)
    y1 = int(y_l1 - 12)
    y2 = int(h_img - m_bottom + 12)

    x1, x2 = max(0, x1), min(w_img, x2)
    y1, y2 = max(0, y1), min(h_img, y2)

    # BƯỚC 1: XÓA TẨY SẠCH NÉT CHỮ CŨ (Tự động nhận diện nét chữ trắng)
    roi = img[y1:y2, x1:x2]
    if roi.size > 0:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        # Quét lấy nét chữ màu trắng
        _, mask_text = cv2.threshold(gray, 130, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        dilated_mask = cv2.dilate(mask_text, kernel, iterations=1)
        
        # Dùng thuật toán Inpaint để tẩy sạch nét chữ trắng, trả lại cảnh gốc phía sau
        cleaned_roi = cv2.inpaint(roi, dilated_mask, inpaintRadius=2, flags=cv2.INPAINT_TELEA)
        img[y1:y2, x1:x2] = cleaned_roi

    # BƯỚC 2: TẠO BÓNG ĐEN MỜ NHẸ CHO CHỮ MỚI (NẾU CẦN)
    if opacity > 0:
        overlay = img.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 0), -1)

        mask = np.zeros((h_img, w_img), dtype=np.float32)
        mask[y1:y2, x1:x2] = opacity
        mask = cv2.GaussianBlur(mask, (21, 21), 0)
        mask_3ch = cv2.merge([mask, mask, mask])

        img_blended = (overlay.astype(np.float32) * mask_3ch + img.astype(np.float32) * (1.0 - mask_3ch))
        img = np.clip(img_blended, 0, 255).astype(np.uint8)

    # BƯỚC 3: IN CHỮ MỚI LÊN VÙNG ĐÃ XÓA SẠCH
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

if uploaded_files and st.button("🚀 Xóa Chữ Cũ & In Chữ Mới"):
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for idx, uploaded_file in enumerate(uploaded_files):
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None:
                continue

            final_img = clean_old_text_and_draw_new(
                img, 
                line1, 
                line2, 
                font_size, 
                line_spacing, 
                margin_left, 
                margin_bottom,
                clean_w,
                shadow_opacity
            )

            _, encoded_img = cv2.imencode(".jpg", final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 99])
            zip_file.writestr(f"edited_{uploaded_file.name}", encoded_img.tobytes())

    st.success("✅ Đã xử lý xong! Chữ cũ đã bị xóa hoàn toàn trước khi viết chữ mới.")
    st.download_button(
        label="📥 Tải về file ZIP kết quả",
        data=zip_buffer.getvalue(),
        file_name="vtools_xoa_sach_chu_cu.zip",
        mime="application/zip"
    )
