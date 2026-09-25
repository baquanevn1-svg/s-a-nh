import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile
import os
import urllib.request

st.set_page_config(page_title="vTools Exact Match 100%", layout="wide")
st.title("📷 vTools Pro: Chuẩn 100% Kiểu Chữ Gốc & Giữ Nguyên Nền")

@st.cache_resource
def load_vtools_exact_font(font_size):
    """
    Tải trực tiếp font Roboto Condensed / DejaVu Sans Sans-Serif chuẩn.
    Đảm bảo TrueType Font luôn load thành công để thay đổi kích thước chữ mượt mà.
    """
    font_filename = "RobotoCondensed-Regular.ttf"
    
    # 1. Thử tải font chuẩn vTools từ Google Fonts CDN
    if not os.path.exists(font_filename) or os.path.getsize(font_filename) == 0:
        urls = [
            "https://github.com/google/fonts/raw/main/ofl/robotocondensed/RobotoCondensed-Regular.ttf",
            "https://raw.githubusercontent.com/google/fonts/main/ofl/robotocondensed/RobotoCondensed%5Bwght%5D.ttf",
            "https://cdnjs.cloudflare.com/ajax/libs/ink/3.1.10/fonts/Roboto/roboto-condensed-regular-webfont.ttf"
        ]
        for url in urls:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response, open(font_filename, 'wb') as out_file:
                    out_file.write(response.read())
                if os.path.exists(font_filename) and os.path.getsize(font_filename) > 0:
                    break
            except Exception:
                continue

    # 2. Sử dụng font đã tải
    if os.path.exists(font_filename) and os.path.getsize(font_filename) > 0:
        try:
            return ImageFont.truetype(font_filename, int(font_size))
        except Exception:
            pass

    # 3. Phao cứu sinh hệ thống (Đảm bảo luôn resize được chữ dù không có mạng)
    system_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "arial.ttf"
    ]
    for sys_f in system_fonts:
        if os.path.exists(sys_f):
            try:
                return ImageFont.truetype(sys_f, int(font_size))
            except Exception:
                continue

    return ImageFont.load_default()

uploaded_files = st.file_uploader("Tải lên danh sách ảnh vTools (JPG, PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

st.subheader("1. Nội dung dòng ngày tháng năm mới")
line1 = st.text_input("Dòng ngày tháng năm mới:", "Thứ Bảy, 15 tháng 2 2025")

st.subheader("2. Điều chỉnh kích thước chữ & Tọa độ")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Kích thước phông chữ thực tế:**")
    font_size_px = st.number_input("Chiều cao phông chữ (Pixel) - Mặc định chuẩn vTools:", min_value=10, max_value=120, value=38, step=1)
    stroke_w = st.slider("Độ mảnh viền bóng (px):", min_value=0, max_value=3, value=1, step=1)

with col2:
    st.markdown("**Vị trí dòng chữ & Độ rộng vùng xóa:**")
    margin_left = st.number_input("Lệch lề trái (Pixel):", value=28)
    margin_bottom = st.number_input("Khoảng cách dòng ngày so với đáy (Pixel):", value=82)
    clean_width_px = st.number_input("Chiều rộng vùng xóa viền đỏ (Pixel):", min_value=100, max_value=3000, value=750, step=10)

if uploaded_files:
    first_file = uploaded_files[0]
    file_bytes = np.asarray(bytearray(first_file.read()), dtype=np.uint8)
    first_file.seek(0)
    preview_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
    if preview_img is not None:
        p_h, p_w, _ = preview_img.shape
        
        y_l1 = p_h - margin_bottom - font_size_px
        
        # Khung quét xóa điều chỉnh theo kích thước nhập vào
        box_y1 = int(y_l1 - 4)
        box_y2 = int(y_l1 + font_size_px + 6)
        
        cv2.rectangle(
            preview_img, 
            (int(margin_left), box_y1), 
            (int(margin_left + clean_width_px), box_y2), 
            (0, 0, 255), 2
        )
        st.image(
            cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB), 
            caption=f"📌 Khung màu đỏ thể hiện vùng xóa chữ cũ (Độ rộng vùng xóa: {clean_width_px}px). Giữ nền 100%.", 
            use_container_width=True
        )

def process_vtools_exact(img, l1_str, f_size, m_left, m_bottom, s_width, clean_w):
    h_img, w_img, _ = img.shape

    y_l1 = int(h_img - m_bottom - f_size)

    # Vùng quét xóa đúng sát nét chữ theo độ rộng tinh chỉnh
    x1 = max(0, int(m_left))
    x2 = min(w_img, int(m_left + clean_w))
    y1 = max(0, int(y_l1 - 4))
    y2 = min(h_img, int(y_l1 + f_size + 6))

    # BƯỚC 1: XÓA NÉT CHỮ CỦ BẰNG THUẬT TOÁN INPAINT (GIỮ NỀN 100%)
    roi = img[y1:y2, x1:x2]
    if roi.size > 0:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Nhận diện chính xác pixel chữ màu trắng
        _, mask = cv2.threshold(gray, 170, 255, cv2.THRESH_BINARY)
        
        # Mở rộng 1px để bao trọn nét
        dilated_mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)), iterations=1)

        # Inpaint khôi phục họa tiết nền
        img[y1:y2, x1:x2] = cv2.inpaint(roi, dilated_mask, inpaintRadius=2, flags=cv2.INPAINT_TELEA)

    # BƯỚC 2: CHÈN CHỮ MỚI CHUẨN KÍCH THƯỚC VÀ PHÔNG CHỮ GỐC
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    base_pil = Image.fromarray(img_rgb).convert("RGBA")

    font = load_vtools_exact_font(f_size)

    text_layer = Image.new("RGBA", base_pil.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)

    if l1_str:
        text_pos = (x1, y_l1)
        
        # Vẽ chữ trắng mờ nhẹ + Viền bóng mỏng nét chuẩn vTools
        draw.text(
            text_pos, 
            l1_str, 
            font=font, 
            fill=(255, 255, 255, 240), 
            stroke_width=int(s_width), 
            stroke_fill=(0, 0, 0, 160)
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

            final_img = process_vtools_exact(
                img, 
                line1, 
                font_size_px, 
                margin_left, 
                margin_bottom, 
                stroke_w,
                clean_width_px
            )

            _, encoded_img = cv2.imencode(".jpg", final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 99])
            zip_file.writestr(f"edited_{uploaded_file.name}", encoded_img.tobytes())

    st.success("✅ Đã hoàn tất! Chữ mới đã chuẩn kích thước và điều chỉnh được độ rộng vùng xóa.")
    st.download_button(
        label="📥 Tải về file ZIP kết quả",
        data=zip_buffer.getvalue(),
        file_name="vtools_exact_custom_width_result.zip",
        mime="application/zip"
    )
