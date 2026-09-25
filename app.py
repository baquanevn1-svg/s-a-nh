import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import zipfile
import os
import urllib.request

st.set_page_config(page_title="vTools Precise Watermark Remover", layout="wide")
st.title("📷 vTools Pro: Xóa Từng Nét Chữ & Thích Ứng Độ Sáng Cục Bộ")

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

st.subheader("1. Nội dung thay thế góc phải")
line1 = st.text_input("Dòng áp chót (Ngày tháng):", "Thứ Sáu, 22 tháng 8 2025")
line2 = st.text_input("Dòng cuối cùng (Giờ & GMT):", "09:15:37 GMT+07:00")

st.subheader("2. Vùng chứa khối chữ vTools bên trái")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Khung khoanh vùng chứa chữ (Không cắt ghép nền):**")
    clean_x = st.number_input("Tọa độ X góc trái:", value=30)
    clean_y = st.number_input("Tọa độ Y góc trên:", value=1300)
    clean_w = st.number_input("Chiều rộng vùng chữ (px):", value=480)
    clean_h = st.number_input("Chiều cao vùng chữ (px):", value=550)

with col2:
    st.markdown("**Vị trí chữ mới góc dưới bên phải:**")
    font_size = st.number_input("Kích thước phông chữ:", value=30)
    line_spacing = st.number_input("Khoảng cách 2 dòng:", value=30)
    margin_right = st.number_input("Khoảng cách lề phải (px):", value=35)
    margin_bottom = st.number_input("Khoảng cách lề dưới (px):", value=60)

if uploaded_files:
    first_file = uploaded_files[0]
    file_bytes = np.asarray(bytearray(first_file.read()), dtype=np.uint8)
    first_file.seek(0)
    preview_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
    if preview_img is not None:
        p_h, p_w, _ = preview_img.shape
        # Khung đỏ xem trước vùng bao quanh khối chữ
        cv2.rectangle(
            preview_img, 
            (int(clean_x), int(clean_y)), 
            (int(clean_x + clean_w), int(clean_y + clean_h)), 
            (0, 0, 255), 2
        )
        # Khung xanh xem trước chữ mới
        right_box_x = p_w - margin_right - 420
        right_box_y = p_h - margin_bottom - (line_spacing + font_size)
        cv2.rectangle(
            preview_img, 
            (int(right_box_x), int(right_box_y)), 
            (int(p_w - margin_right), int(right_box_y + line_spacing + font_size + 10)), 
            (0, 255, 0), 2
        )
        st.image(
            cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB), 
            caption="📌 Khung đỏ khoanh vùng khối chữ. Thuật toán sẽ xóa từng nét chữ bên trong khung này.", 
            use_container_width=True
        )

def remove_text_letter_by_letter(img, cx, cy, cw, ch):
    """
    Thuật toán xóa từng nét chữ theo tọa độ điểm ảnh và điều chỉnh độ sáng cục bộ.
    """
    h_img, w_img, _ = img.shape
    x1, x2 = max(0, int(cx)), min(w_img, int(cx + cw))
    y1, y2 = max(0, int(cy)), min(h_img, int(cy + ch))

    roi = img[y1:y2, x1:x2]
    if roi.size == 0:
        return img

    # 1. Chuyển sang hệ màu xám để phân tích nét
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # 2. Tạo mặt nạ lọc nét chữ sáng/trắng trên nhiều loại nền (Xi măng, Bầu trời, Bảng hiệu)
    # Lọc phân ngưỡng thích ứng theo vùng cục bộ
    thresh_adaptive = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, -4
    )

    # Lọc các điểm ảnh có độ sáng cao (chữ vTools thường màu trắng)
    _, thresh_bright = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

    # Lọc viền chữ sắc nét (Sobel Gradient)
    grad_x = cv2.Sobel(gray, cv2.CV_8U, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_8U, 0, 1, ksize=3)
    grad = cv2.addWeighted(grad_x, 0.5, grad_y, 0.5, 0)
    _, thresh_grad = cv2.threshold(grad, 25, 255, cv2.THRESH_BINARY)

    # Gộp các mặt nạ để lấy chính xác 100% nét chữ
    letter_mask = cv2.bitwise_or(thresh_bright, thresh_adaptive)
    letter_mask = cv2.bitwise_or(letter_mask, thresh_grad)

    # 3. Mở rộng nhẹ viền nét chữ (1-2px) để ôm hết phần bóng mờ nhòe viền chữ
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    dilated_mask = cv2.dilate(letter_mask, kernel, iterations=1)

    # 4. Phục hồi nền dựa trên độ sáng & màu sắc xung quanh từng nét chữ (Navier-Stokes Inpainting)
    cleaned_roi = cv2.inpaint(roi, dilated_mask, inpaintRadius=3, flags=cv2.INPAINT_NS)

    # Ghép vùng đã xử lý nét chữ trở lại ảnh gốc
    img[y1:y2, x1:x2] = cleaned_roi
    return img

def process_vtools_precise(img, cx, cy, cw, ch, l1_str, l2_str, f_size, l_spacing, m_right, m_bottom):
    h_img, w_img, _ = img.shape

    # 1. Xóa từng nét chữ
    img = remove_text_letter_by_letter(img, cx, cy, cw, ch)

    # 2. Thêm chữ mới ở góc dưới bên phải
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb).convert("RGBA")

    font = load_custom_font(int(f_size))
    if font is None:
        font = ImageFont.load_default()

    draw_dummy = ImageDraw.Draw(pil_img)

    w_l1 = draw_dummy.textlength(l1_str, font=font) if l1_str else 0
    w_l2 = draw_dummy.textlength(l2_str, font=font) if l2_str else 0

    x_l1 = int(w_img - m_right - w_l1)
    x_l2 = int(w_img - m_right - w_l2)

    y_l2 = int(h_img - m_bottom - f_size)
    y_l1 = int(y_l2 - l_spacing)

    # Bóng mờ cho chữ mới
    shadow_layer = Image.new("RGBA", pil_img.size, (0, 0, 0, 0))
    draw_shadow = ImageDraw.Draw(shadow_layer)

    if l1_str:
        draw_shadow.text((x_l1 + 1, y_l1 + 1), l1_str, fill=(0, 0, 0, 220), font=font)
    if l2_str:
        draw_shadow.text((x_l2 + 1, y_l2 + 1), l2_str, fill=(0, 0, 0, 220), font=font)

    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=0.8))

    # Chữ trắng mới
    text_layer = Image.new("RGBA", pil_img.size, (0, 0, 0, 0))
    draw_text = ImageDraw.Draw(text_layer)

    if l1_str:
        draw_text.text((x_l1, y_l1), l1_str, fill=(255, 255, 255, 255), font=font)
    if l2_str:
        draw_text.text((x_l2, y_l2), l2_str, fill=(255, 255, 255, 255), font=font)

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

            final_img = process_vtools_precise(
                img, 
                clean_x, 
                clean_y, 
                clean_w, 
                clean_h, 
                line1, 
                line2, 
                font_size, 
                line_spacing, 
                margin_right, 
                margin_bottom
            )

            _, encoded_img = cv2.imencode(".jpg", final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 99])
            zip_file.writestr(f"edited_{uploaded_file.name}", encoded_img.tobytes())

    st.success("✅ Đã xử lý xong! Nét chữ được xóa sạch tự nhiên theo đúng độ sáng gốc.")
    st.download_button(
        label="📥 Tải về file ZIP kết quả",
        data=zip_buffer.getvalue(),
        file_name="vtools_xoa_tung_net_chu.zip",
        mime="application/zip"
    )
