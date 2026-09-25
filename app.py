import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import zipfile
import os
import urllib.request

st.set_page_config(page_title="vTools Perfect Clean Edition", layout="wide")
st.title("📷 vTools Pro: Khôi Phục Cảnh Thật 100% & Không Còn Mảng Đen")

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

st.subheader("2. Căn chỉnh vị trí dòng chữ")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Vị trí chữ tính từ lề dưới ảnh:**")
    margin_bottom = st.number_input("Cách lề đáy ảnh (px):", value=45)
    margin_left = st.number_input("Cách lề trái (px):", value=25)
    stroke_width = st.slider("Độ đậm viền bóng chữ (px):", min_value=1, max_value=3, value=2)

with col2:
    st.markdown("**Định dạng phông chữ vTools:**")
    font_size = st.number_input("Kích thước phông chữ (px):", value=28)
    line_spacing = st.number_input("Khoảng cách giữa 2 dòng (px):", value=34)
    clean_w = st.number_input("Chiều rộng vùng chữ cũ cần xóa (px):", value=460)

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
            caption="📌 Xem trước vùng sẽ được làm sạch tuyệt đối (Không mảng đen).", 
            use_container_width=True
        )

def process_vtools_pure_background(img, l1_str, l2_str, f_size, l_spacing, m_left, m_bottom, c_w, s_width):
    """
    1. Lấy mẫu cảnh thực tế bên cạnh đè lấp chữ cũ (Texture Patch replacement).
    2. Không sử dụng bất kỳ mảng xám hay bóng đen đè nền nào.
    3. In chữ trắng với đường viền đen ôm sát (Stroke) giống hệt vTools chuẩn.
    """
    h_img, w_img, _ = img.shape

    # 1. Tính toán vị trí chữ
    y_l2 = int(h_img - m_bottom - f_size)
    y_l1 = int(y_l2 - l_spacing)

    x1 = int(m_left)
    x2 = int(m_left + c_w)
    y1 = int(y_l1 - 10)
    y2 = int(h_img - m_bottom + 10)

    x1, x2 = max(0, x1), min(w_img, x2)
    y1, y2 = max(0, y1), min(h_img, y2)
    box_w = x2 - x1
    box_h = y2 - y1

    # 2. XÓA SẠCH MẢNG ĐEN: Nhân bản nền thật từ vùng bên phải đè sang
    # Lấy mảng cảnh thật nằm ngay sát lề bên phải của khung chữ
    sample_x1 = min(w_img - box_w - 1, x2 + 5)
    sample_x2 = min(w_img - 1, sample_x1 + box_w)
    
    if sample_x2 - sample_x1 == box_w and box_w > 0 and box_h > 0:
        background_patch = img[y1:y2, sample_x1:sample_x2].copy()
        # Dùng Seamless Clone để hòa trộn cảnh cực kỳ tự nhiên không vết ghép
        mask = np.full(background_patch.shape, 255, dtype=np.uint8)
        center = (int(x1 + box_w / 2), int(y1 + box_h / 2))
        try:
            img = cv2.seamlessClone(background_patch, img, mask, center, cv2.NORMAL_CLONE)
        except Exception:
            img[y1:y2, x1:x2] = background_patch
    else:
        # Trong trường hợp ảnh quá hẹp, dùng thuật toán Telea làm sạch
        roi = img[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, mask_white = cv2.threshold(gray, 130, 255, cv2.THRESH_BINARY)
        cleaned_roi = cv2.inpaint(roi, mask_white, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
        img[y1:y2, x1:x2] = cleaned_roi

    # 3. VẼ CHỮ TRẮNG NỔI TRÊN NỀN THẬT (Stroke Outline)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb).convert("RGBA")

    font = load_custom_font(int(f_size))
    if font is None:
        font = ImageFont.load_default()

    # Lớp chữ với viền stroke sát nét
    text_layer = Image.new("RGBA", pil_img.size, (0, 0, 0, 0))
    draw_text = ImageDraw.Draw(text_layer)

    # In chữ kèm viền đen (stroke_fill) chuẩn vTools
    if l1_str:
        draw_text.text(
            (x1, y_l1), 
            l1_str, 
            fill=(255, 255, 255, 255), 
            font=font,
            stroke_width=int(s_width),
            stroke_fill=(0, 0, 0, 255)
        )
    if l2_str:
        draw_text.text(
            (x1, y_l2), 
            l2_str, 
            fill=(255, 255, 255, 255), 
            font=font,
            stroke_width=int(s_width),
            stroke_fill=(0, 0, 0, 255)
        )

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

            final_img = process_vtools_pure_background(
                img, 
                line1, 
                line2, 
                font_size, 
                line_spacing, 
                margin_left, 
                margin_bottom,
                clean_w,
                stroke_width
            )

            _, encoded_img = cv2.imencode(".jpg", final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 99])
            zip_file.writestr(f"edited_{uploaded_file.name}", encoded_img.tobytes())

    st.success("✅ Đã xử lý xong! Nền hoàn toàn là cảnh thật 100%, không còn mảng đen.")
    st.download_button(
        label="📥 Tải về file ZIP kết quả",
        data=zip_buffer.getvalue(),
        file_name="vtools_sach_nen_hoan_hao.zip",
        mime="application/zip"
    )
