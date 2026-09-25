import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import zipfile
import os
import urllib.request

st.set_page_config(page_title="vTools Watermark Editor Ultimate", layout="wide")
st.title("📷 Công cụ vTools: Xóa Sạch 100% Mọi Loại Nền (Không Nhòe - Không Vệt)")

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

st.subheader("2. Cấu hình xử lý cho mọi trường hợp nền")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Vùng quét xóa chữ cũ (Góc dưới bên trái):**")
    clean_x = st.number_input("Tọa độ X góc trái:", value=30)
    clean_y = st.number_input("Tọa độ Y góc trên:", value=1830)
    clean_w = st.number_input("Chiều rộng vùng quét (px):", value=490)
    clean_h = st.number_input("Chiều cao vùng quét (px):", value=150)
    
    clean_method = st.selectbox(
        "Chế độ tẩy xóa tối ưu:",
        [
            "Tự động đa tầng (Tối ưu nhất cho mọi ảnh)",
            "Nền xi măng / Sân đất / Đường xá (Chống nhòe 100%)",
            "Nền chói sáng / Biển hiệu phức tạp / Nền tối"
        ]
    )

with col2:
    st.markdown("**Vị trí chữ mới (Góc dưới bên phải):**")
    font_size = st.number_input("Kích thước phông chữ:", value=25)
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
        cv2.rectangle(
            preview_img, 
            (int(clean_x), int(clean_y)), 
            (int(clean_x + clean_w), int(clean_y + clean_h)), 
            (0, 0, 255), 2
        )
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
            caption="Khung đỏ = Vùng quét xóa | Khung xanh = Vị trí chữ mới góc phải", 
            use_container_width=True
        )

def remove_vtools_ultimate(img, cx, cy, cw, ch, method):
    h_img, w_img, _ = img.shape
    x1, x2 = max(0, int(cx)), min(w_img, int(cx + cw))
    y1, y2 = max(0, int(cy)), min(h_img, int(cy + ch))

    roi = img[y1:y2, x1:x2]
    if roi.size == 0:
        return img

    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    if method == "Nền xi măng / Sân đất / Đường xá (Chống nhòe 100%)":
        # Dùng kỹ thuật Bilateral Blend bảo tồn hạt nền phẳng, bù màu chuẩn
        filtered_roi = cv2.bilateralFilter(roi, d=9, sigmaColor=50, sigmaSpace=50)
        img[y1:y2, x1:x2] = filtered_roi

    elif method == "Nền chói sáng / Biển hiệu phức tạp / Nền tối":
        # Tạo mặt nạ quét siêu chi tiết bao gồm cả bóng chìm xám và màu chói
        thresh_low = cv2.threshold(gray_roi, 130, 255, cv2.THRESH_BINARY)[1]
        
        # Phát hiện góc cạnh nét chữ mờ
        edges = cv2.Canny(gray_roi, 30, 100)
        
        combined_mask = cv2.bitwise_or(thresh_low, edges)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated_mask = cv2.dilate(combined_mask, kernel, iterations=2)
        
        cleaned_roi = cv2.inpaint(roi, dilated_mask, inpaintRadius=2, flags=cv2.INPAINT_NS)
        img[y1:y2, x1:x2] = cleaned_roi

    else:
        # Phương pháp TỰ ĐỘNG ĐA TẦNG (Tối ưu nhất)
        # 1. Mặt nạ chữ sáng
        mask1 = cv2.threshold(gray_roi, 145, 255, cv2.THRESH_BINARY)[1]
        # 2. Mặt nạ tương phản (Bóng mờ trên nền xe/nền tối)
        grad_x = cv2.Sobel(gray_roi, cv2.CV_8U, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray_roi, cv2.CV_8U, 0, 1, ksize=3)
        grad = cv2.addWeighted(grad_x, 0.5, grad_y, 0.5, 0)
        mask2 = cv2.threshold(grad, 15, 255, cv2.THRESH_BINARY)[1]

        final_mask = cv2.bitwise_or(mask1, mask2)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        final_mask = cv2.dilate(final_mask, kernel, iterations=1)

        # Xóa theo thuật toán Navier-Stokes mượt hạt
        cleaned_roi = cv2.inpaint(roi, final_mask, inpaintRadius=2, flags=cv2.INPAINT_NS)

        # Kiểm tra nếu là nền đồng nhất/mặt đường thì khử nhẹ vệt bóng
        if np.std(gray_roi) < 40:
            cleaned_roi = cv2.bilateralFilter(cleaned_roi, d=5, sigmaColor=25, sigmaSpace=25)

        img[y1:y2, x1:x2] = cleaned_roi

    return img

def process_full_image(img, cx, cy, cw, ch, l1_str, l2_str, f_size, l_spacing, m_right, m_bottom, method):
    h_img, w_img, _ = img.shape

    # 1. Xóa chữ cũ
    img = remove_vtools_ultimate(img, cx, cy, cw, ch, method)

    # 2. Chèn chữ mới góc dưới bên phải
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

    # Bóng mờ mềm
    shadow_layer = Image.new("RGBA", pil_img.size, (0, 0, 0, 0))
    draw_shadow = ImageDraw.Draw(shadow_layer)

    if l1_str:
        draw_shadow.text((x_l1 + 1, y_l1 + 1), l1_str, fill=(0, 0, 0, 220), font=font)
    if l2_str:
        draw_shadow.text((x_l2 + 1, y_l2 + 1), l2_str, fill=(0, 0, 0, 220), font=font)

    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=1.0))

    # Chữ trắng
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

            final_img = process_full_image(
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
                margin_bottom,
                clean_method
            )

            _, encoded_img = cv2.imencode(".jpg", final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 99])
            zip_file.writestr(f"edited_{uploaded_file.name}", encoded_img.tobytes())

    st.success("✅ Đã xử lý xong! Hãy tải về kiểm tra độ chân thực của từng bức ảnh.")
    st.download_button(
        label="📥 Tải về file ZIP kết quả",
        data=zip_buffer.getvalue(),
        file_name="vtools_chuan_xac_100.zip",
        mime="application/zip"
    )
