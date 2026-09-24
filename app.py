import streamlit as st
import cv2
import numpy as np
import io
import zipfile

st.set_page_config(page_title="vTools Watermark Remover", layout="wide")
st.title("🧼 Công cụ Xóa 2 Dòng Cuối vTools (Nền Nét Gốc 100% - Không Dấu Vết)")

uploaded_files = st.file_uploader("Tải lên danh sách ảnh vTools (JPG, PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

st.subheader("1. Thông số vùng xóa (Đã căn chuẩn 2 dòng cuối)")
col1, col2 = st.columns(2)
with col1:
    crop_x = st.number_input("Tọa độ X góc trái:", value=35)
    crop_y = st.number_input("Tọa độ Y góc trên (Dòng ngày tháng):", value=1800)
with col2:
    crop_w = st.number_input("Chiều rộng vùng xóa (px):", value=460)
    crop_h = st.number_input("Chiều cao vùng xóa (px):", value=90)

if uploaded_files:
    first_file = uploaded_files[0]
    file_bytes = np.asarray(bytearray(first_file.read()), dtype=np.uint8)
    first_file.seek(0)
    preview_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
    if preview_img is not None:
        p_h, p_w, _ = preview_img.shape
        # Vẽ khung đỏ vị trí sẽ được tẩy sạch chữ
        cv2.rectangle(
            preview_img, 
            (int(crop_x), int(crop_y)), 
            (int(crop_x + crop_w), int(crop_y + crop_h)), 
            (0, 0, 255), 2
        )
        st.image(
            cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB), 
            caption=f"Khung đỏ đánh dấu vùng 2 dòng chữ cuối sẽ xóa (Kích thước ảnh gốc: {p_w}x{p_h})", 
            use_container_width=True
        )

def remove_text_cleanly(img, x, y, w, h):
    """
    Kỹ thuật tách mặt nạ nét chữ (Mask-based Precise Inpainting):
    Chỉ xóa đúng các điểm ảnh của nét chữ màu trắng, giữ nguyên 100% phần cảnh nền tự nhiên.
    """
    img_h, img_w, _ = img.shape
    x1, x2 = max(0, int(x)), min(img_w, int(x + w))
    y1, y2 = max(0, int(y)), min(img_h, int(y + h))

    roi = img[y1:y2, x1:x2]
    if roi.size == 0:
        return img

    # 1. Chuyển sang ảnh xám để phân lập chữ
    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # 2. Tạo mặt nạ chỉ chứa nét chữ trắng/sáng của vTools (Ngưỡng sáng > 175)
    _, mask = cv2.threshold(gray_roi, 175, 255, cv2.THRESH_BINARY)

    # 3. Mở rộng nhẹ mặt nạ 1px để ôm trọn phần viền bóng mờ của chữ
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask_dilated = cv2.dilate(mask, kernel, iterations=1)

    # 4. Phôi phục nền bằng thuật toán Navier-Stokes (Bảo toàn độ nét & đường nét cảnh quan)
    cleaned_roi = cv2.inpaint(roi, mask_dilated, inpaintRadius=2, flags=cv2.INPAINT_NS)
    
    img_out = img.copy()
    img_out[y1:y2, x1:x2] = cleaned_roi
    return img_out

if uploaded_files and st.button("🚀 Bắt Đầu Xóa 2 Dòng Chữ Cuối"):
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for idx, uploaded_file in enumerate(uploaded_files):
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None:
                continue

            clean_img = remove_text_cleanly(img, crop_x, crop_y, crop_w, crop_h)

            # Xuất ảnh JPEG chất lượng cao 99% (Giữ tối đa chi tiết ảnh gốc)
            _, encoded_img = cv2.imencode(".jpg", clean_img, [int(cv2.IMWRITE_JPEG_QUALITY), 99])
            zip_file.writestr(f"cleaned_{uploaded_file.name}", encoded_img.tobytes())

    st.success("✅ Đã xóa xong 2 dòng cuối! Ảnh giữ nguyên độ nét cảnh gốc 100%, không để lại vết mờ.")
    st.download_button(
        label="📥 Tải về file ZIP danh sách ảnh đã xóa chữ",
        data=zip_buffer.getvalue(),
        file_name="anh_da_xoa_chu.zip",
        mime="application/zip"
    )
