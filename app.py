import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile
import os
import urllib.request

st.set_page_config(page_title="vTools Watermark Editor", layout="wide")
st.title("📷 Công cụ Sửa Ngày Tháng vTools (Thật 100% Như Ảnh Gốc)")

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

st.subheader("1. Nội dung thay thế")
line1 = st.text_input("Dòng áp chót (Ngày tháng):", "Thứ Bảy, 22 tháng 2 2026")
line2 = st.text_input("Dòng cuối cùng (Giờ & GMT):", "09:52:23 GMT+07:00")

st.subheader("2. Vị trí & Thông số (Đã căn chuẩn theo vTools)")
col1, col2 = st.columns(2)
with col1:
    crop_x = st.number_input("Tọa độ X (Góc trái chữ):", value=37)
    crop_y = st.number_input("Tọa độ Y (Dòng ngày tháng):", value=1865)
    font_size = st.number_input("Kích thước phông chữ:", value=27)
    line_spacing = st.number_input("Khoảng cách 2 dòng:", value=33)
with col2:
    overlay_padding_x = st.number_input("Mở rộng lề xám bên trái/phải (px):", value=15)
    overlay_opacity = st.slider("Độ đậm nền xám vTools (0.0 - 1.0):", min_value=0.1, max_value=0.9, value=0.45, step=0.05)

if uploaded_files:
    first_file = uploaded_files[0]
    file_bytes = np.asarray(bytearray(first_file.read()), dtype=np.uint8)
    first_file.seek(0)
    preview_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
    if preview_img is not None:
        p_h, p_w, _ = preview_img.shape
        # Khung viền xem trước vùng ngày tháng
        cv2.rectangle(
            preview_img, 
            (int(crop_x), int(crop_y)), 
            (int(crop_x + 400), int(crop_y + 80)), 
            (0, 0, 255), 2
        )
        st.image(
            cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB), 
            caption=f"Khung đỏ vị trí dòng Ngày Tháng (Kích thước ảnh gốc: {p_w}x{p_h})", 
            use_container_width=True
        )

def process_vtools_watermark(img, x, y, line1_str, line2_str, f_size, l_spacing, opacity, pad_x):
    """
    Tái tạo watermark chuẩn vTools:
    1. Phủ dải xám mờ trong suốt (Semi-transparent overlay) chuẩn tông vTools để ẩn hoàn toàn chữ cũ.
    2. Vẽ dòng chữ trắng sắc nét + bóng mờ tự nhiên chuẩn vTools.
    """
    h_img, w_img, _ = img.shape
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb).convert("RGBA")

    font = load_custom_font(int(f_size))
    if font is None:
        font = ImageFont.load_default()

    # Tạo layer mờ trong suốt
    overlay = Image.new("RGBA", pil_img.size, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)

    # 1. Tính toán vùng nền xám mờ cần che chữ cũ
    y1 = max(0, int(y) - 6)
    y2 = min(h_img, int(y) + int(l_spacing) + int(f_size) + 10)
    x1 = max(0, int(x) - int(pad_x))
    x2 = min(w_img, int(x) + 450)

    # Vẽ dải xám mờ vTools (màu xám tối đục nhẹ, không làm nhòe ảnh gốc)
    alpha_val = int(opacity * 255)
    draw_overlay.rectangle([x1, y1, x2, y2], fill=(20, 24, 30, alpha_val))

    # Ghép dải nền xám mờ lên ảnh gốc
    composed = Image.alpha_composite(pil_img, overlay)
    draw = ImageDraw.Draw(composed)

    # 2. Vẽ chữ mới chuẩn vTools (Chữ trắng + bóng mờ mềm)
    y_line1 = int(y)
    y_line2 = int(y) + int(l_spacing)

    def draw_vtools_text_item(draw_obj, text_pos, text, font_item):
        tx, ty = text_pos
        # Bóng đổ mờ phía dưới chuẩn vTools
        draw_obj.text((tx + 1, ty + 1), text, fill=(0, 0, 0, 220), font=font_item)
        draw_obj.text((tx + 2, ty + 2), text, fill=(0, 0, 0, 120), font=font_item)
        # Chữ chính màu trắng tinh
        draw_obj.text((tx, ty), text, fill=(255, 255, 255, 255), font=font_item)

    if line1_str:
        draw_vtools_text_item(draw, (int(x), y_line1), line1_str, font)
    if line2_str:
        draw_vtools_text_item(draw, (int(x), y_line2), line2_str, font)

    # Chuyển về RGB và xuất BGR cho OpenCV
    res_rgb = composed.convert("RGB")
    return cv2.cvtColor(np.array(res_rgb), cv2.COLOR_RGB2BGR)

if uploaded_files and st.button("🚀 Bắt Đầu Xử Lý (Thật 100% Chuẩn vTools)"):
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for idx, uploaded_file in enumerate(uploaded_files):
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None:
                continue

            final_img = process_vtools_watermark(
                img, 
                crop_x, 
                crop_y, 
                line1, 
                line2, 
                font_size, 
                line_spacing, 
                overlay_opacity, 
                overlay_padding_x
            )

            # Xuất chất lượng JPEG cao nhất 98%
            _, encoded_img = cv2.imencode(".jpg", final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 98])
            zip_file.writestr(f"edited_{uploaded_file.name}", encoded_img.tobytes())

    st.success("✅ Đã xử lý xong! Ảnh nét căng, dải nền xám mờ hòa quyện tự nhiên như ảnh gốc vTools.")
    st.download_button(
        label="📥 Tải về file ZIP tất cả ảnh đã xử lý",
        data=zip_buffer.getvalue(),
        file_name="danh_sach_anh_da_sua.zip",
        mime="application/zip"
    )
