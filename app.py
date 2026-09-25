import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import zipfile
import os
import urllib.request

st.set_page_config(page_title="vTools Watermark Editor Perfect", layout="wide")
st.title("📷 Công cụ vTools: Xóa Sạch 100% & Bảo Toàn Nền Xi Măng Gốc")

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

st.subheader("2. Thông số vùng xử lý chuẩn xác")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Vùng quét xóa khối chữ vTools bên trái:**")
    # Tọa độ Y=1350 và H=500 để bao trùm toàn bộ từ dòng VN-2000 xuống hết dòng Hướng chụp
    clean_x = st.number_input("Tọa độ X góc trái:", value=30)
    clean_y = st.number_input("Tọa độ Y góc trên:", value=1350)
    clean_w = st.number_input("Chiều rộng vùng quét (px):", value=480)
    clean_h = st.number_input("Chiều cao vùng quét (px):", value=500)

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
        # Vẽ khung đỏ xem trước vùng sẽ xóa
        cv2.rectangle(
            preview_img, 
            (int(clean_x), int(clean_y)), 
            (int(clean_x + clean_w), int(clean_y + clean_h)), 
            (0, 0, 255), 3
        )
        # Vẽ khung xanh xem trước vị trí chữ mới
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
            caption="⚠️ ĐẢM BẢO KHUNG ĐỎ BAO TRÙM HOÀN TOÀN TẤT CẢ CÁC DÒNG CHỮ VTOOLS BÊN TRÁI", 
            use_container_width=True
        )

def patch_clean_texture_advanced(img, cx, cy, cw, ch):
    """
    Kỹ thuật ghép mảng nền thật (Patch Cloning & Feather Blending)
    Giúp xóa 100% chữ mà giữ nguyên độ nét, hạt xi măng gốc, KHÔNG BỊ NHÒE MỜ.
    """
    h_img, w_img, _ = img.shape
    x1, x2 = max(0, int(cx)), min(w_img, int(cx + cw))
    y1, y2 = max(0, int(cy)), min(h_img, int(cy + ch))
    
    box_h = y2 - y1
    box_w = x2 - x1

    if box_h <= 0 or box_w <= 0:
        return img

    # 1. Ưu tiên lấy mảng nền sạch ngay bên phải vùng chữ
    src_x1 = x2 + 20
    src_x2 = src_x1 + box_w
    src_y1 = y1
    src_y2 = y2

    # Nếu bên phải bị tràn viền ảnh, lấy mẫu mảng nền phía trên
    if src_x2 > w_img:
        src_x1 = x1
        src_x2 = x2
        src_y1 = max(0, y1 - box_h - 20)
        src_y2 = src_y1 + box_h

    sample_patch = img[src_y1:src_y2, src_x1:src_x2]

    # Kiểm tra mảng nền lấy mẫu đủ kích thước
    if sample_patch.shape[0] == box_h and sample_patch.shape[1] == box_w:
        # Tạo mặt nạ hòa trộn viền mượt (Feather Mask)
        mask = np.zeros((box_h, box_w), dtype=np.float32)
        cv2.rectangle(mask, (10, 10), (box_w - 10, box_h - 10), 1.0, -1)
        mask = cv2.GaussianBlur(mask, (21, 21), 0)
        mask_3ch = cv2.merge([mask, mask, mask])

        target_roi = img[y1:y2, x1:x2].astype(np.float32)
        patch_float = sample_patch.astype(np.float32)

        # Trộn mảng nền sạch với ảnh gốc theo độ mượt của viền
        blended = patch_float * mask_3ch + target_roi * (1.0 - mask_3ch)
        img[y1:y2, x1:x2] = np.clip(blended, 0, 255).astype(np.uint8)
    else:
        # Phương pháp dự phòng
        gray_roi = cv2.cvtColor(img[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
        _, mask_binary = cv2.threshold(gray_roi, 130, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        mask_binary = cv2.dilate(mask_binary, kernel, iterations=2)
        img[y1:y2, x1:x2] = cv2.inpaint(img[y1:y2, x1:x2], mask_binary, inpaintRadius=3, flags=cv2.INPAINT_TELEA)

    return img

def process_perfect_vtools(img, cx, cy, cw, ch, l1_str, l2_str, f_size, l_spacing, m_right, m_bottom):
    h_img, w_img, _ = img.shape

    # 1. Xóa sạch chữ cũ bằng mảng nền thật
    img = patch_clean_texture_advanced(img, cx, cy, cw, ch)

    # 2. Ghép chữ mới sang góc dưới bên phải
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

    # Bóng chữ
    shadow_layer = Image.new("RGBA", pil_img.size, (0, 0, 0, 0))
    draw_shadow = ImageDraw.Draw(shadow_layer)

    if l1_str:
        draw_shadow.text((x_l1 + 1, y_l1 + 1), l1_str, fill=(0, 0, 0, 220), font=font)
    if l2_str:
        draw_shadow.text((x_l2 + 1, y_l2 + 1), l2_str, fill=(0, 0, 0, 220), font=font)

    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=0.8))

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

            final_img = process_perfect_vtools(
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

    st.success("✅ Đã xử lý xong! Bạn hãy tải về kiểm tra độ sắc nét của nền.")
    st.download_button(
        label="📥 Tải về file ZIP kết quả",
        data=zip_buffer.getvalue(),
        file_name="vtools_sach_triet_de.zip",
        mime="application/zip"
    )
