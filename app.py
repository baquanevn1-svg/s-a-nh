import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import zipfile
import os
import urllib.request

st.set_page_config(page_title="vTools Watermark Editor", layout="wide")
st.title("📷 Công cụ Sửa Ngày Tháng vTools (Chân Thật 100% Theo Ảnh Mẫu)")

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
line1 = st.text_input("Dòng áp chót (Ngày tháng):", "Thứ Sáu, 22 tháng 8 2025")
line2 = st.text_input("Dòng cuối cùng (Giờ & GMT):", "09:15:37 GMT+07:00")

st.subheader("2. Thông số vị trí (Căn chỉnh chuẩn theo ảnh mẫu)")
col1, col2 = st.columns(2)
with col1:
    crop_x = st.number_input("Tọa độ X (Góc trái chữ):", value=35)
    crop_y = st.number_input("Tọa độ Y (Dòng ngày tháng):", value=1865)
with col2:
    font_size = st.number_input("Kích thước phông chữ:", value=25)
    line_spacing = st.number_input("Khoảng cách 2 dòng:", value=30)

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
            (int(crop_x + 400), int(crop_y + int(line_spacing) + int(font_size) + 10)), 
            (0, 0, 255), 2
        )
        st.image(
            cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB), 
            caption=f"Vùng căn chỉnh chữ mới (Độ phân giải: {p_w}x{p_h})", 
            use_container_width=True
        )

def process_vtools_exact_sample(img, x, y, line1_str, line2_str, f_size, l_spacing):
    h_img, w_img, _ = img.shape
    
    # Tọa độ khung chữ cũ cần tẩy
    x1 = max(0, int(x) - 4)
    x2 = min(w_img, int(x) + 450)
    y1 = max(0, int(y) - 4)
    y2 = min(h_img, int(y) + int(l_spacing) + int(f_size) + 12)

    # 1. TẨY SẠCH CHỮ CŨ CHỈ BẰNG CÁCH LỌC PIXEL TRẮNG (GIỮ NỀN CẢNH NẾT 100%)
    roi = img[y1:y2, x1:x2]
    if roi.size > 0:
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        # Quét đúng nét chữ màu trắng sáng
        _, mask = cv2.threshold(gray_roi, 175, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask_dilated = cv2.dilate(mask, kernel, iterations=1)
        # Vá nhẹ điểm ảnh chữ cũ, hoàn toàn KHÔNG làm nhòe hay mờ cảnh quan xung quanh
        cleaned_roi = cv2.inpaint(roi, mask_dilated, inpaintRadius=2, flags=cv2.INPAINT_NS)
        img[y1:y2, x1:x2] = cleaned_roi

    # 2. VẼ CHỮ MỚI VỚI BÓNG ĐỔ TỎA MỜ TỰ NHIÊN (SOFT SHADOW GLOW) CHUẨN vTools
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb).convert("RGBA")

    font = load_custom_font(int(f_size))
    if font is None:
        font = ImageFont.load_default()

    # Layer vẽ bóng đen mờ tỏa
    shadow_layer = Image.new("RGBA", pil_img.size, (0, 0, 0, 0))
    draw_shadow = ImageDraw.Draw(shadow_layer)

    y_line1 = int(y)
    y_line2 = int(y) + int(l_spacing)

    # Vẽ nét bóng đen dày mờ
    if line1_str:
        draw_shadow.text((int(x) + 1, y_line1 + 1), line1_str, fill=(0, 0, 0, 220), font=font)
    if line2_str:
        draw_shadow.text((int(x) + 1, y_line2 + 1), line2_str, fill=(0, 0, 0, 220), font=font)

    # Làm mờ nhẹ bóng đổ tạo hiệu ứng tỏa tự nhiên chuẩn vTools
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=1.2))

    # Layer vẽ chữ trắng chính
    text_layer = Image.new("RGBA", pil_img.size, (0, 0, 0, 0))
    draw_text = ImageDraw.Draw(text_layer)

    if line1_str:
        draw_text.text((int(x), y_line1), line1_str, fill=(255, 255, 255, 255), font=font)
    if line2_str:
        draw_text.text((int(x), y_line2), line2_str, fill=(255, 255, 255, 255), font=font)

    # Ghép layer bóng mờ + layer chữ trắng lên nền ảnh gốc
    composed = Image.alpha_composite(pil_img, shadow_layer)
    composed = Image.alpha_composite(composed, text_layer)

    res_rgb = composed.convert("RGB")
    return cv2.cvtColor(np.array(res_rgb), cv2.COLOR_RGB2BGR)

if uploaded_files and st.button("🚀 Bắt Đầu Xử Lý (Giống Ảnh Mẫu 100%)"):
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for idx, uploaded_file in enumerate(uploaded_files):
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None:
                continue

            final_img = process_vtools_exact_sample(
                img, 
                crop_x, 
                crop_y, 
                line1, 
                line2, 
                font_size, 
                line_spacing
            )

            # Xuất chất lượng JPEG cao nhất 99%
            _, encoded_img = cv2.imencode(".jpg", final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 99])
            zip_file.writestr(f"edited_{uploaded_file.name}", encoded_img.tobytes())

    st.success("✅ Đã xử lý xong! Nền ảnh nguyên bản 100%, chữ mới có hiệu ứng bóng tỏa mờ đúng chuẩn vTools.")
    st.download_button(
        label="📥 Tải về file ZIP tất cả ảnh đã xử lý",
        data=zip_buffer.getvalue(),
        file_name="anh_vtools_hoan_thien.zip",
        mime="application/zip"
    )
