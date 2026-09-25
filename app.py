import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import zipfile
import os
import urllib.request

st.set_page_config(page_title="vTools Clean & Replace (Anti-Glare)", layout="wide")
st.title("📷 vTools Pro: Giữ Nguyên Cấu Trúc + Tối Ưu Ảnh Chói Nắng / Đường Bê Tông")

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

st.subheader("2. Tùy chỉnh vị trí & Chế độ xử lý chói nắng")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Vị trí 2 dòng cuối (Cố định góc trái):**")
    margin_left = st.number_input("Cách lề trái (px):", value=25)
    margin_bottom = st.number_input("Cách lề đáy (px):", value=45)
    shadow_opacity = st.slider("Độ đậm bóng mờ nền đen:", min_value=0.0, max_value=0.40, value=0.15, step=0.01)

with col2:
    st.markdown("**Cấu hình chữ & Xử lý chói nắng:**")
    font_size = st.number_input("Kích thước phông chữ (px):", value=28)
    line_spacing = st.number_input("Khoảng cách giữa 2 dòng (px):", value=34)
    clean_w = st.number_input("Chiều rộng vùng xóa chữ cũ (px):", value=460)
    
    st.markdown("---")
    st.markdown("**☀️ Tùy chọn xử lý Nền Chói Nắng / Bê Tông / Mái Tôn:**")
    enable_bright_mode = st.checkbox("Bật chế độ quét sâu cho ảnh chói nắng", value=True, help="Tự động bóc tách nét chữ trắng chính xác khi nền bị sáng chói hoặc đốm nắng")
    enable_text_stroke = st.checkbox("Tạo viền đen quanh chữ mới (Đọc rõ 100% trên nền chói)", value=True)

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
            caption="📌 Vùng khung đỏ sẽ được quét xóa sạch chữ cũ kể cả khi bị chói nắng.", 
            use_container_width=True
        )

def process_vtools_advanced(img, l1_str, l2_str, f_size, l_spacing, m_left, m_bottom, c_w, opacity, is_bright_mode, has_stroke):
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

    # 1. BƯỚC 1: XÓA CHỮ CŨ (TỰ ĐỘNG THÍCH ỨNG THEO ĐỘ SÁNG NỀN)
    roi = img[y1:y2, x1:x2]
    if roi.size > 0:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)

        # Nếu nền bị chói nắng (hoặc bật chế độ chói nắng)
        if is_bright_mode or mean_brightness > 130:
            # Thuật toán Morphological Top-Hat bóc tách nét chữ trắng khỏi nền sáng chói
            kernel_tophat = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
            tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel_tophat)
            _, mask_text = cv2.threshold(tophat, 25, 255, cv2.THRESH_BINARY)
            
            # Kết hợp thêm Canny edge để bắt sạch viền chữ
            edges = cv2.Canny(gray, 100, 200)
            mask_text = cv2.bitwise_or(mask_text, edges)
        else:
            # Phân ngưỡng tiêu chuẩn cho ảnh tối / nền sẫm
            _, mask_text = cv2.threshold(gray, 140, 255, cv2.THRESH_BINARY)

        # Nở nhẹ vùng mặt nạ để bao phủ cả phần mờ nhòe quanh chữ
        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        dilated_mask = cv2.dilate(mask_text, kernel_dilate, iterations=1)

        # Inpaint tẩy sạch nét chữ
        cleaned_roi = cv2.inpaint(roi, dilated_mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
        img[y1:y2, x1:x2] = cleaned_roi

    # 2. BƯỚC 2: PHỦ MÀN ĐEN MỜ NHẸ (TÙY CHỈNH OPACITY)
    if opacity > 0:
        overlay = img.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 0), -1)

        mask = np.zeros((h_img, w_img), dtype=np.float32)
        mask[y1:y2, x1:x2] = opacity
        mask = cv2.GaussianBlur(mask, (21, 21), 0)
        mask_3ch = cv2.merge([mask, mask, mask])

        img_blended = (overlay.astype(np.float32) * mask_3ch + img.astype(np.float32) * (1.0 - mask_3ch))
        img = np.clip(img_blended, 0, 255).astype(np.uint8)

    # 3. BƯỚC 3: IN CHỮ MỚI (CÓ VIỀN ĐEN NẾU NỀN CHÓI)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb).convert("RGBA")

    font = load_custom_font(int(f_size))
    if font is None:
        font = ImageFont.load_default()

    # Lớp vẽ chữ
    text_layer = Image.new("RGBA", pil_img.size, (0, 0, 0, 0))
    draw_text = ImageDraw.Draw(text_layer)

    # Nếu bật viền chữ (Đặc biệt hiệu quả cho nền chói)
    if has_stroke:
        stroke_w = 2
        stroke_color = (0, 0, 0, 255) # Viền đen nét
        if l1_str:
            draw_text.text((x1, y_l1), l1_str, fill=(255, 255, 255, 255), font=font, stroke_width=stroke_w, stroke_fill=stroke_color)
        if l2_str:
            draw_text.text((x1, y_l2), l2_str, fill=(255, 255, 255, 255), font=font, stroke_width=stroke_w, stroke_fill=stroke_color)
    else:
        if l1_str:
            draw_text.text((x1, y_l1), l1_str, fill=(255, 255, 255, 255), font=font)
        if l2_str:
            draw_text.text((x1, y_l2), l2_str, fill=(255, 255, 255, 255), font=font)

    composed = Image.alpha_composite(pil_img, text_layer)
    res_rgb = composed.convert("RGB")
    return cv2.cvtColor(np.array(res_rgb), cv2.COLOR_RGB2BGR)

if uploaded_files and st.button("🚀 Bắt Đầu Xử Lý Hàng Loạt"):
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for idx, uploaded_file in enumerate(uploaded_files):
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None:
                continue

            final_img = process_vtools_advanced(
                img, 
                line1, 
                line2, 
                font_size, 
                line_spacing, 
                margin_left, 
                margin_bottom,
                clean_w,
                shadow_opacity,
                enable_bright_mode,
                enable_text_stroke
            )

            _, encoded_img = cv2.imencode(".jpg", final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 99])
            zip_file.writestr(f"edited_{uploaded_file.name}", encoded_img.tobytes())

    st.success("✅ Đã xử lý hoàn tất! Ảnh nền sẫm hay chói nắng đều sạch sẽ và sắc nét.")
    st.download_button(
        label="📥 Tải về file ZIP kết quả",
        data=zip_buffer.getvalue(),
        file_name="vtools_anti_glare_result.zip",
        mime="application/zip"
    )
