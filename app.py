import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import zipfile
import os
import urllib.request

st.set_page_config(page_title="vTools Perfect Clean & Match", layout="wide")
st.title("📷 vTools Pro: Xóa Sạch & Giống Chữ Gốc 100% (Không Bệt Đen)")

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

st.subheader("2. Căn chỉnh vị trí & Phông chữ vTools chuẩn")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Vị trí chữ (Cố định góc trái):**")
    margin_left = st.number_input("Cách lề trái (px):", value=25)
    margin_bottom = st.number_input("Cách lề đáy (px):", value=45)

with col2:
    st.markdown("**Định dạng phông chữ chuẩn vTools:**")
    font_size = st.number_input("Kích thước chữ (px):", value=28)
    line_spacing = st.number_input("Khoảng cách 2 dòng (px):", value=34)
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
            caption="📌 Vùng đỏ: Xóa sạch nét chữ cũ mà KHÔNG dùng mảng che đen.", 
            use_container_width=True
        )

def process_vtools_perfect(img, l1_str, l2_str, f_size, l_spacing, m_left, m_bottom, c_w):
    h_img, w_img, _ = img.shape

    # Tọa độ 2 dòng chữ
    y_l2 = int(h_img - m_bottom - f_size)
    y_l1 = int(y_l2 - l_spacing)

    x1 = int(m_left)
    x2 = int(m_left + c_w)
    y1 = int(y_l1 - 12)
    y2 = int(h_img - m_bottom + 12)

    x1, x2 = max(0, x1), min(w_img, x2)
    y1, y2 = max(0, y1), min(h_img, y2)

    # BƯỚC 1: XÓA CHỮ CŨ CHÍNH XÁC (TẨY SẠCH NÉT CHỮ TRẮNG MÀ KHÔNG LÀM ĐEN NỀN)
    roi = img[y1:y2, x1:x2]
    if roi.size > 0:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Bóc tách nét chữ trắng bằng giải pháp đa tầng (Top-Hat + Phân ngưỡng linh hoạt)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
        tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
        _, mask1 = cv2.threshold(tophat, 18, 255, cv2.THRESH_BINARY)
        _, mask2 = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        combined_mask = cv2.bitwise_or(mask1, mask2)
        dilated_mask = cv2.dilate(combined_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)), iterations=1)

        # Inpaint tẩy sạch vết chữ trắng
        img[y1:y2, x1:x2] = cv2.inpaint(roi, dilated_mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)

    # BƯỚC 2: IN CHỮ MỚI VỚI BÓNG ĐỔ MỀM TỰ NHIÊN (CHUẨN KIỂU CHỮ vTools GỐC)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    base_pil = Image.fromarray(img_rgb).convert("RGBA")

    font = load_custom_font(int(f_size))
    if font is None:
        font = ImageFont.load_default()

    # Lớp bóng đổ mờ (Drop Shadow) màu đen nhạt phía dưới
    shadow_layer = Image.new("RGBA", base_pil.size, (0, 0, 0, 0))
    draw_shadow = ImageDraw.Draw(shadow_layer)
    
    # Độ lệch bóng nhẹ 1.5px để tạo chiều sâu giống chữ vTools
    if l1_str:
        draw_shadow.text((x1 + 1, y_l1 + 1), l1_str, fill=(0, 0, 0, 180), font=font)
    if l2_str:
        draw_shadow.text((x1 + 1, y_l2 + 1), l2_str, fill=(0, 0, 0, 180), font=font)

    # Làm mờ nhẹ phần bóng để hòa vào nền tự nhiên, không bị vệt đen cứng
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=1.2))

    # Lớp chữ trắng sắc nét phía trên
    text_layer = Image.new("RGBA", base_pil.size, (0, 0, 0, 0))
    draw_text = ImageDraw.Draw(text_layer)

    if l1_str:
        draw_text.text((x1, y_l1), l1_str, fill=(255, 255, 255, 255), font=font)
    if l2_str:
        draw_text.text((x1, y_l2), l2_str, fill=(255, 255, 255, 255), font=font)

    # Ghép các lớp lại với nhau
    final_pil = Image.alpha_composite(base_pil, shadow_layer)
    final_pil = Image.alpha_composite(final_pil, text_layer)

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

            final_img = process_vtools_perfect(
                img, 
                line1, 
                line2, 
                font_size, 
                line_spacing, 
                margin_left, 
                margin_bottom,
                clean_w
            )

            _, encoded_img = cv2.imencode(".jpg", final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 99])
            zip_file.writestr(f"edited_{uploaded_file.name}", encoded_img.tobytes())

    st.success("✅ Đã xử lý thành công! Nền ảnh được giữ nguyên độ tự nhiên và kiểu chữ khớp 100%.")
    st.download_button(
        label="📥 Tải về file ZIP kết quả",
        data=zip_buffer.getvalue(),
        file_name="vtools_perfect_result.zip",
        mime="application/zip"
    )
