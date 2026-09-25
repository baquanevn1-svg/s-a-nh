import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import zipfile
import os
import urllib.request

st.set_page_config(page_title="vTools Text Outline Edition", layout="wide")
st.title("📷 vTools Pro: Giữ Nền Tự Nhiên 100% & Tạo Viền Nổi Chữ")

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

st.subheader("2. Căn chỉnh vị trí chữ & Độ đậm viền bóng")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Vị trí tính từ lề đáy ảnh:**")
    margin_bottom = st.number_input("Cách lề đáy ảnh (px):", value=45)
    margin_left = st.number_input("Cách lề trái (px):", value=25)
    shadow_radius = st.slider("Độ tỏa bóng viền chữ (px):", min_value=1, max_value=5, value=2)

with col2:
    st.markdown("**Định dạng phông chữ vTools:**")
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
        
        box_y1 = int(y_l1 - 8)
        box_y2 = int(p_h - margin_bottom + 8)
        
        cv2.rectangle(
            preview_img, 
            (int(margin_left), box_y1), 
            (int(margin_left + clean_w), box_y2), 
            (0, 0, 255), 2
        )
        st.image(
            cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB), 
            caption="📌 Xem trước vị trí thay thế (Sẽ không tạo mảng xám đè lên).", 
            use_container_width=True
        )

def process_vtools_no_box(img, l1_str, l2_str, f_size, l_spacing, m_left, m_bottom, c_w, s_radius):
    """
    1. Xóa 100% vết chữ cũ và khôi phục cảnh gốc.
    2. Không dùng bất kỳ mảng xám đè nào.
    3. Vẽ chữ trắng với lớp bóng đen viền ôm sát (Text Glow/Outline) chuẩn vTools.
    """
    h_img, w_img, _ = img.shape

    # 1. Tọa độ chính xác
    y_l2 = int(h_img - m_bottom - f_size)
    y_l1 = int(y_l2 - l_spacing)

    x1 = int(m_left)
    x2 = int(m_left + c_w)
    y1 = int(y_l1 - 8)
    y2 = int(h_img - m_bottom + 8)

    x1, x2 = max(0, x1), min(w_img, x2)
    y1, y2 = max(0, y1), min(h_img, y2)

    # 2. Xóa chữ cũ, trả lại nền cảnh thật 100%
    roi = img[y1:y2, x1:x2]
    if roi.size > 0:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, mask_white = cv2.threshold(gray, 135, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        dilated_mask = cv2.dilate(mask_white, kernel, iterations=1)
        cleaned_roi = cv2.inpaint(roi, dilated_mask, inpaintRadius=2, flags=cv2.INPAINT_TELEA)
        img[y1:y2, x1:x2] = cleaned_roi

    # 3. Chuyển sang PIL để vẽ chữ trắng kèm bóng viền đen ôm sát
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb).convert("RGBA")

    font = load_custom_font(int(f_size))
    if font is None:
        font = ImageFont.load_default()

    # Lớp bóng đen bao quanh chữ (Outer Outline/Shadow)
    shadow_layer = Image.new("RGBA", pil_img.size, (0, 0, 0, 0))
    draw_shadow = ImageDraw.Draw(shadow_layer)

    # Tạo hiệu ứng bóng tỏa 8 hướng ôm sát nét chữ
    offsets = [
        (-1, -1), (0, -1), (1, -1),
        (-1,  0),          (1,  0),
        (-1,  1), (0,  1), (1,  1),
        (0,  2),  (1,  2)
    ]

    for dx, dy in offsets:
        if l1_str:
            draw_shadow.text((x1 + dx, y_l1 + dy), l1_str, fill=(0, 0, 0, 240), font=font)
        if l2_str:
            draw_shadow.text((x1 + dx, y_l2 + dy), l2_str, fill=(0, 0, 0, 240), font=font)

    # Làm mềm bóng viền nhẹ theo thông số slider
    if s_radius > 0:
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=s_radius * 0.5))

    # Lớp chữ trắng sắc nét ở trên cùng
    text_layer = Image.new("RGBA", pil_img.size, (0, 0, 0, 0))
    draw_text = ImageDraw.Draw(text_layer)

    if l1_str:
        draw_text.text((x1, y_l1), l1_str, fill=(255, 255, 255, 255), font=font)
    if l2_str:
        draw_text.text((x1, y_l2), l2_str, fill=(255, 255, 255, 255), font=font)

    # Ghép các lớp lại
    composed = Image.alpha_composite(pil_img, shadow_layer)
    composed = Image.alpha_composite(composed, text_layer)

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

            final_img = process_vtools_no_box(
                img, 
                line1, 
                line2, 
                font_size, 
                line_spacing, 
                margin_left, 
                margin_bottom,
                clean_w,
                shadow_radius
            )

            _, encoded_img = cv2.imencode(".jpg", final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 99])
            zip_file.writestr(f"edited_{uploaded_file.name}", encoded_img.tobytes())

    st.success("✅ Đã xử lý xong! Nền giữ nguyên cảnh thật 100%, chữ trắng có viền nổi chuẩn vTools.")
    st.download_button(
        label="📥 Tải về file ZIP kết quả",
        data=zip_buffer.getvalue(),
        file_name="vtools_chu_noi_khong_mang_xam.zip",
        mime="application/zip"
    )
