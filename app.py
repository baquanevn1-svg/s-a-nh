import streamlit as st
import cv2
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import io
import zipfile

st.set_page_config(page_title="Công cụ sửa ngày tháng ảnh", layout="wide")
st.title("📷 Công cụ Sửa Ngày Tháng Ảnh Khảo Sát")

uploaded_files = st.file_uploader("Tải lên danh sách ảnh (JPG, PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

col1, col2 = st.columns(2)

with col1:
    new_date_text = st.text_input("Ngày tháng năm mới mong muốn:", value="2024/07/20 09:15:00")
    
    st.subheader("Cấu hình vị trí văn bản (Góc dưới bên trái)")
    # Vị trí hộp xóa chữ cũ (x1, y1, x2, y2)
    crop_x = st.number_input("Tọa độ X góc trái chữ:", value=10)
    crop_y = st.number_input("Tọa độ Y góc trên chữ:", value=950)
    crop_w = st.number_input("Chiều rộng vùng xóa:", value=350)
    crop_h = st.number_input("Chiều cao vùng xóa:", value=60)
    
    font_size = st.number_input("Kích thước chữ mới:", value=22)

def process_image(file_bytes, date_text):
    # Đọc ảnh
    nparr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    h, w, _ = img.shape

    # 1. Xóa vùng chữ cũ bằng Inpainting (giữ nguyên nền)
    mask = np.zeros((h, w), np.uint8)
    # Giới hạn vùng mask tránh tràn biên ảnh
    y1, y2 = max(0, crop_y), min(h, crop_y + crop_h)
    x1, x2 = max(0, crop_x), min(w, crop_x + crop_w)
    mask[y1:y2, x1:x2] = 255
    
    # Kỹ thuật Telea tái tạo lại nền gạch/đường
    inpainted = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)
    
    # Chuyển sang PIL để ghi chữ nét đẹp
    img_rgb = cv2.cvtColor(inpainted, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil_img)
    
    # Ghi chữ mới (dùng phông mặc định hoặc tải phông nét mảnh)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
        
    draw.text((crop_x + 5, crop_y + 5), date_text, fill=(255, 255, 255), font=font)
    
    return pil_img

if uploaded_files:
    with col2:
        st.subheader("Xem trước ảnh đầu tiên")
        preview_img = process_image(uploaded_files[0].getvalue(), new_date_text)
        st.image(preview_img, use_container_width=True)

    if st.button("🚀 BẮT ĐẦU XỬ LÝ TOÀN BỘ ÁNH", type="primary"):
        progress_bar = st.progress(0)
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for idx, file in enumerate(uploaded_files):
                processed_pil = process_image(file.getvalue(), new_date_text)
                
                # Lưu vào file zip
                img_byte_arr = io.BytesIO()
                processed_pil.save(img_byte_arr, format='JPEG', quality=95)
                zip_file.writestr(f"edited_{file.name}", img_byte_arr.getvalue())
                
                # Cập nhật tiến độ
                progress_bar.progress((idx + 1) / len(uploaded_files))
                
        st.success("Đã xử lý xong!")
        st.download_button(
            label="📥 TẢI VỀ TẤT CẢ ÁNH (.ZIP)",
            data=zip_buffer.getvalue(),
            file_name="anh_da_sua_ngay_thang.zip",
            mime="application/zip"
        )
