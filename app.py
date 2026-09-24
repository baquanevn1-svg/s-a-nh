import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile
import os
import urllib.request

st.set_page_config(page_title="vTools Watermark Editor", layout="wide")
st.title("📷 Công cụ Sửa Ngày Tháng vTools (Đã Căn Chuẩn Vị Trí)")

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

st.subheader("2. Cài đặt thông số (Đã cấu hình chuẩn theo yêu cầu)")
col1, col2 = st.columns(2)
with col1:
    crop_x = st.number_input("Tọa độ X (Góc trái chữ):", value=35)
    # Cấu hình Y = 1860 để vừa khít 2 dòng dưới cùng, không bị dính vào dòng "Hướng chụp"
    crop_y = st.number_input("Tọa độ Y (Dòng ngày tháng):", value=1860)
    font_size = st.number_input("Kích thước phông chữ:", value=30)
    line_spacing = st.number_input("Khoảng cách 2 dòng:", value=35)
with col2:
    overlay_padding_x = st.number_input("Mở rộng lề xám bên trái/phải (px):", value=15)
    overlay_opacity = st.slider("Độ đậm nền mờ vTools (0.0 - 1.0):", min_value=0.1, max_value=0.9, value=0.40, step=0.05)

if uploaded_files:
    first_file = uploaded_files[0]
    file_bytes = np.asarray(bytearray(first_file.read()), dtype=np.uint8)
    first_file.seek(0)
    preview_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
    if preview_img is not None:
        p_h, p_w, _ = preview_img.shape
        # Vẽ khung màu đỏ để bạn xem trước vị trí chữ mới sẽ đè lên
        cv2.rectangle(
            preview_img, 
            (int(crop_x), int(crop_y)), 
            (int(crop_x + 450), int(crop_y + 85)), 
            (0, 0, 255), 2
        )
        st.image(
            cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB), 
            caption=f"Khung đỏ đánh dấu vị trí 2 dòng ngày tháng (Kích thước ảnh: {p_w}x{p_h})", 
            use_container_width=True
        )

def process_vtools_image(img, x, y, line1_str, line2_str, f_size, l_spacing, opacity, pad_x):
    h_img, w_img, _ = img.shape
    
    # Tọa độ vùng chữ cần xóa
    x1 = max(0, int(x) - int(pad_x))
    x2 = min(w_img, int(x) + 460)
    y1 = max(0, int(y) - 6)
    y2 = min(h_img, int(y) + int(l_spacing) + int(f_size) + 12)

    # 1. Tẩy sạch các vệt chữ trắng cũ ở vùng 2 dòng cuối
    roi = img[y1:y2, x1:x2]
    if roi.size > 0:
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray_roi, 160, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        mask = cv2.dilate(mask, kernel, iterations=1)
        cleaned_roi = cv2.inpaint(roi, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
        img[y1:y2, x1:x2] = cleaned_roi

    # 2. Phủ dải bóng tối mờ nhẹ chuẩn tông vTools
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb).convert("RGBA")

    font = load_custom_font(int(f_size))
    if font is None:
        font = ImageFont.load_default()

    overlay = Image.new("RGBA", pil_img.size, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    alpha_val = int(opacity * 255)
    draw_overlay.rectangle([x1, y1, x2, y2], fill=(15, 18, 22, alpha_val))

    composed = Image.alpha_composite(pil_img, overlay)
    draw = ImageDraw.Draw(composed)

    # 3. Vẽ 2 dòng chữ trắng mới sắc nét
    y_line1 = int(y)
    y_line2 = int(y) + int(l_spacing)

    def draw_text_with_shadow(draw_obj, pos, text_str, font_obj):
        tx, ty = pos
        # Đổ bóng chữ viền mờ 1px
        draw_obj.text((tx + 1, ty + 1), text_str, fill=(0, 0, 0, 230), font=font_obj)
        # Chữ trắng tinh
        draw_obj.text((tx, ty), text_str, fill=(255, 255, 255, 255), font=font_obj)

    if line1_str:
        draw_text_with_shadow(draw, (int(x), y_line1), line1_str, font)
    if line2_str:
        draw_text_with_shadow(draw, (int(x), y_line2), line2_str, font)

    res_rgb = composed.convert("RGB")
    return cv2.cvtColor(np.array(res_rgb), cv2.COLOR_RGB2BGR)

if uploaded_files and st.button("🚀 Bắt Đầu Xử Lý (Sửa Lỗi Dính Chữ)"):
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for idx, uploaded_file in enumerate(uploaded_files):
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None:
                continue

            final_img = process_vtools_image(
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

            _, encoded_img = cv2.imencode(".jpg", final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 98])
            zip_file.writestr(f"edited_{uploaded_file.name}", encoded_img.tobytes())

    st.success("✅ Đã xử lý xong! Tọa độ Y đã được đặt về 1860, không còn bị dính vào dòng Hướng Chụp nữa.")
    st.download_button(
        label="📥 Tải về file ZIP tất cả ảnh đã xử lý",
        data=zip_buffer.getvalue(),
        file_name="danh_sach_anh_da_sua.zip",
        mime="application/zip"
    )
