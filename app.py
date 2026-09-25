import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import zipfile
import os
import urllib.request

st.set_page_config(page_title="vTools Watermark Editor Sharp Text", layout="wide")
st.title("📷 vTools Pro: Mảng Xám Mờ Nhẹ & Chữ Trắng Sắc Nét")

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

st.subheader("2. Tùy chỉnh độ mờ mảng xám & Vị trí chữ")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Mảng xám nền (Gợi ý: 0.10 để mảng xám cực mờ, thấy rõ cảnh vật):**")
    shadow_opacity = st.slider("Độ đục mảng xám nền:", min_value=0.0, max_value=0.4, value=0.10, step=0.01)
    
    st.markdown("**Vùng xóa chữ cũ:**")
    clean_x = st.number_input("Tọa độ X (Góc trái):", value=20)
    clean_y = st.number_input("Tọa độ Y (Sát dưới Hướng chụp):", value=1350)
    clean_w = st.number_input("Chiều rộng vùng che (px):", value=450)
    clean_h = st.number_input("Chiều cao vùng che (px):", value=120)

with col2:
    st.markdown("**Định dạng chữ vTools sắc nét:**")
    font_size = st.number_input("Kích thước phông chữ (px):", value=28)
    line_spacing = st.number_input("Khoảng cách giữa 2 dòng (px):", value=36)
    text_offset_x = st.number_input("Thụt lề chữ X (px):", value=25)
    text_offset_y = st.number_input("Vị trí dòng 1 Y (px):", value=1355)

if uploaded_files:
    first_file = uploaded_files[0]
    file_bytes = np.asarray(bytearray(first_file.read()), dtype=np.uint8)
    first_file.seek(0)
    preview_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
    if preview_img is not None:
        p_h, p_w, _ = preview_img.shape
        cv2.rectangle(
            preview_img, 
            (int(clean_x), int(clean_y)), 
            (int(clean_x + clean_w), int(clean_y + clean_h)), 
            (0, 0, 255), 2
        )
        st.image(
            cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB), 
            caption="📌 Khung đỏ khoanh vùng xử lý.", 
            use_container_width=True
        )

def process_vtools_sharp_text(img, cx, cy, cw, ch, l1_str, l2_str, f_size, l_spacing, tx, ty, opacity):
    """
    1. Xóa chữ cũ bằng Inpainting.
    2. Phủ mảng xám mờ mỏng trên ảnh nền.
    3. Vẽ chữ mới nét căng 100% ở lớp riêng trên cùng.
    """
    h_img, w_img, _ = img.shape
    x1, x2 = max(0, int(cx)), min(w_img, int(cx + cw))
    y1, y2 = max(0, int(cy)), min(h_img, int(cy + ch))

    roi = img[y1:y2, x1:x2]
    if roi.size == 0:
        return img

    # BƯỚC 1: Xóa sạch 100% nét chữ cũ
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, mask_white = cv2.threshold(gray, 140, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    dilated_mask = cv2.dilate(mask_white, kernel, iterations=1)
    
    cleaned_roi = cv2.inpaint(roi, dilated_mask, inpaintRadius=2, flags=cv2.INPAINT_TELEA)
    img[y1:y2, x1:x2] = cleaned_roi

    # BƯỚC 2: Phủ mảng xám mờ rất mỏng (Chỉ tác động lên nền)
    if opacity > 0:
        overlay = img.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 0), -1)

        mask = np.zeros((h_img, w_img), dtype=np.float32)
        mask[y1:y2, x1:x2] = opacity
        mask = cv2.GaussianBlur(mask, (25, 25), 0)
        mask_3ch = cv2.merge([mask, mask, mask])

        img_blended = (overlay.astype(np.float32) * mask_3ch + img.astype(np.float32) * (1.0 - mask_3ch))
        img = np.clip(img_blended, 0, 255).astype(np.uint8)

    # BƯỚC 3: Vẽ chữ mới ở lớp trên cùng - Đảm bảo nét 100% không bị mờ
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb).convert("RGBA")

    font = load_custom_font(int(f_size))
    if font is None:
        font = ImageFont.load_default()

    y_line1 = int(ty)
    y_line2 = int(ty + l_spacing)

    # Viền bóng đổ đen sắc (Shadow Layer) giúp nổi chữ trắng
    shadow_layer = Image.new("RGBA", pil_img.size, (0, 0, 0, 0))
    draw_shadow = ImageDraw.Draw(shadow_layer)

    if l1_str:
        draw_shadow.text((int(tx) + 1, y_line1 + 1), l1_str, fill=(0, 0, 0, 230), font=font)
    if l2_str:
        draw_shadow.text((int(tx) + 1, y_line2 + 1), l2_str, fill=(0, 0, 0, 230), font=font)

    # Lớp chữ trắng siêu nét (Pure White Layer)
    text_layer = Image.new("RGBA", pil_img.size, (0, 0, 0, 0))
    draw_text = ImageDraw.Draw(text_layer)

    if l1_str:
        draw_text.text((int(tx), y_line1), l1_str, fill=(255, 255, 255, 255), font=font)
    if l2_str:
        draw_text.text((int(tx), y_line2), l2_str, fill=(255, 255, 255, 255), font=font)

    # Ghép 3 lớp: Ảnh nền mờ -> Bóng chữ -> Chữ trắng
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

            final_img = process_vtools_sharp_text(
                img, 
                clean_x, 
                clean_y, 
                clean_w, 
                clean_h, 
                line1, 
                line2, 
                font_size, 
                line_spacing, 
                text_offset_x, 
                text_offset_y,
                shadow_opacity
            )

            _, encoded_img = cv2.imencode(".jpg", final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 99])
            zip_file.writestr(f"edited_{uploaded_file.name}", encoded_img.tobytes())

    st.success("✅ Đã xử lý xong! Mảng xám nền mờ nhẹ tự nhiên, chữ trắng rõ nét 100%.")
    st.download_button(
        label="📥 Tải về file ZIP kết quả",
        data=zip_buffer.getvalue(),
        file_name="vtools_canh_ro_chu_sac_net.zip",
        mime="application/zip"
    )
