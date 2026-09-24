import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile
import os
import urllib.request

st.set_page_config(page_title="vTools Watermark Editor", layout="wide")
st.title("📷 Công cụ Sửa Ngày Tháng vTools (Giữ Nền Gốc 100%)")

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

st.subheader("2. Cài đặt thông số (Đã thiết lập chuẩn theo yêu cầu)")
col1, col2 = st.columns(2)
with col1:
    crop_x = st.number_input("Tọa độ X (Góc trái chữ):", value=35)
    crop_y = st.number_input("Tọa độ Y (Dòng ngày tháng):", value=1800)
with col2:
    font_size = st.number_input("Kích thước phông chữ:", value=30)
    line_spacing = st.number_input("Khoảng cách 2 dòng:", value=35)

if uploaded_files:
    first_file = uploaded_files[0]
    file_bytes = np.asarray(bytearray(first_file.read()), dtype=np.uint8)
    first_file.seek(0)
    preview_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
    if preview_img is not None:
        p_h, p_w, _ = preview_img.shape
        cv2.rectangle(
            preview_img, 
            (int(crop_x), int(crop_y)), 
            (int(crop_x + 450), int(crop_y + int(line_spacing) + int(font_size) + 10)), 
            (0, 0, 255), 2
        )
        st.image(
            cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB), 
            caption=f"Xem trước vùng chỉnh sửa (Độ phân giải: {p_w}x{p_h})", 
            use_container_width=True
        )

def process_vtools_exact(img, x, y, line1_str, line2_str, f_size, l_spacing):
    h_img, w_img, _ = img.shape
    
    x1 = max(0, int(x) - 5)
    x2 = min(w_img, int(x) + 480)
    y1 = max(0, int(y) - 5)
    y2 = min(h_img, int(y) + int(l_spacing) + int(f_size) + 15)

    # 1. XÓA NẾT CHỮ TRẮNG CỦ - GIỮ 100% NỀN CẢNH GỐC
    roi = img[y1:y2, x1:x2]
    if roi.size > 0:
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        # Chỉ chọn chính xác nét chữ trắng (threshold = 180)
        _, mask = cv2.threshold(gray_roi, 180, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        mask = cv2.dilate(mask, kernel, iterations=1)
        # Phôi phục nền cảnh gốc ngay bên dưới chữ
        cleaned_roi = cv2.inpaint(roi, mask, inpaintRadius=2, flags=cv2.INPAINT_TELEA)
        img[y1:y2, x1:x2] = cleaned_roi

    # 2. VẼ CHỮ MỚI CHUẨN CƠ CHỮ VÀ BÓNG MỜ TRÊN NỀN GỐC
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb).convert("RGBA")

    font = load_custom_font(int(f_size))
    if font is None:
        font = ImageFont.load_default()

    draw = ImageDraw.Draw(pil_img)
    y_line1 = int(y)
    y_line2 = int(y) + int(l_spacing)

    # Hàm vẽ chữ có đổ bóng mờ nhẹ vTools (Không tạo dải xám nền)
    def draw_vtools_text(draw_obj, pos, text_str, font_obj):
        tx, ty = pos
        # Đổ bóng viền xám đen nhẹ để chữ nổi bật trên nền cảnh sáng
        draw_obj.text((tx + 1, ty + 1), text_str, fill=(0, 0, 0, 180), font=font_obj)
        draw_obj.text((tx, ty + 1), text_str, fill=(0, 0, 0, 120), font=font_obj)
        # Chữ màu trắng chuẩn vTools
        draw_obj.text((tx, ty), text_str, fill=(255, 255, 255, 255), font=font_obj)

    if line1_str:
        draw_vtools_text(draw, (int(x), y_line1), line1_str, font)
    if line2_str:
        draw_vtools_text(draw, (int(x), y_line2), line2_str, font)

    res_rgb = pil_img.convert("RGB")
    return cv2.cvtColor(np.array(res_rgb), cv2.COLOR_RGB2BGR)

if uploaded_files and st.button("🚀 Bắt Đầu Xử Lý (Giữ Nền Gốc 100%)"):
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for idx, uploaded_file in enumerate(uploaded_files):
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None:
                continue

            final_img = process_vtools_exact(
                img, 
                crop_x, 
                crop_y, 
                line1, 
                line2, 
                font_size, 
                line_spacing
            )

            _, encoded_img = cv2.imencode(".jpg", final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 98])
            zip_file.writestr(f"edited_{uploaded_file.name}", encoded_img.tobytes())

    st.success("✅ Đã xử lý xong! Nền ảnh được giữ nguyên 100% so với ảnh gốc.")
    st.download_button(
        label="📥 Tải về file ZIP tất cả ảnh đã xử lý",
        data=zip_buffer.getvalue(),
        file_name="danh_sach_anh_da_sua.zip",
        mime="application/zip"
    )
