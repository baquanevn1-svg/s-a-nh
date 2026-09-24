import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile

st.title("📷 Công cụ Sửa Ngày Tháng Ảnh Khảo Sát")

uploaded_files = st.file_uploader("Tải lên danh sách ảnh (JPG, PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

new_date = st.text_input("Ngày tháng năm mới mong muốn:", "2026/09/23 16:22:53")

st.subheader("Cấu hình vị trí văn bản (Góc dưới bên trái)")
col1, col2 = st.columns(2)
with col1:
    crop_x = st.number_input("Tọa độ X góc trái chữ:", value=12)
    crop_y = st.number_input("Tọa độ Y góc trên chữ:", value=1380)
    font_scale = st.number_input("Tỷ lệ phóng đại chữ (thay cho kích thước):", value=2.0, step=0.1) # Dùng font_scale thay vì font_size
with col2:
    crop_w = st.number_input("Chiều rộng vùng xóa:", value=400) # Tăng chiều rộng vùng xóa mặc định
    crop_h = st.number_input("Chiều cao vùng xóa:", value=70) # Tăng chiều cao vùng xóa mặc định

if uploaded_files and st.button("Xử lý ảnh"):
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for idx, uploaded_file in enumerate(uploaded_files):
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None:
                continue
            h, w, _ = img.shape

            # Lấy vùng ảnh cần xử lý
            y1, y2 = max(0, int(crop_y)), min(h, int(crop_y + crop_h))
            x1, x2 = max(0, int(crop_x)), min(w, int(crop_x + crop_w))
            roi = img[y1:y2, x1:x2]

            if roi.size > 0:
                # 1. Chuyển sang ảnh xám để tìm nét chữ màu sáng
                gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                _, text_mask = cv2.threshold(gray_roi, 170, 255, cv2.THRESH_BINARY)
                
                kernel = np.ones((2, 2), np.uint8)
                text_mask = cv2.dilate(text_mask, kernel, iterations=1)

                # 2. Xóa nét chữ mỏng bằng Inpaint
                cleaned_roi = cv2.inpaint(roi, text_mask, inpaintRadius=1, flags=cv2.INPAINT_TELEA)
                img[y1:y2, x1:x2] = cleaned_roi

            # 3. Viết chữ ngày tháng mới (Sử dụng kỹ thuật phóng đại phông mặc định)
            # Tạo một ảnh tạm thời lớn hơn để vẽ chữ
            scale_factor = float(font_scale)
            temp_font = ImageFont.load_default()
            
            # Ước tính kích thước văn bản
            text_width, text_height = temp_font.getsize(new_date)
            
            # Tạo ảnh tạm thời với nền trong suốt
            temp_img = Image.new('RGBA', (int(text_width * scale_factor * 1.1), int(text_height * scale_factor * 1.5)), (0, 0, 0, 0))
            temp_draw = ImageDraw.Draw(temp_img)
            
            # Vẽ văn bản lên ảnh tạm thời (phóng đại vị trí và kích thước nếu có thể, nhưng với load_default thì chủ yếu là vị trí)
            # Vì load_default không hỗ trợ kích thước, ta vẽ nó ở kích thước mặc định và sau đó phóng đại toàn bộ ảnh tạm thời.
            
            # Vẽ chữ màu trắng kèm viền xám mỏng nhẹ để rõ nét trên nền gạch
            temp_draw.text((2, 2), new_date, fill=(80, 80, 80), font=temp_font)
            temp_draw.text((0, 0), new_date, fill=(255, 255, 255), font=temp_font)
            
            # Phóng đại ảnh tạm thời
            resizing_method = Image.NEAREST # Dùng NEAREST để giữ nét sắc cạnh cho chữ bitmap
            resized_text_img = temp_img.resize((int(temp_img.width * scale_factor), int(temp_img.height * scale_factor)), resample=resizing_method)

            # Chuyển đổi ảnh gốc sang PIL để chèn chữ
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)
            
            # Chèn ảnh chữ đã phóng đại vào ảnh gốc
            pil_img.paste(resized_text_img, (int(crop_x), int(crop_y)), resized_text_img)

            # Chuyển đổi lại sang định dạng để lưu
            out_img = io.BytesIO()
            pil_img.save(out_img, format="JPEG", quality=98)
            zip_file.writestr(f"edited_{uploaded_file.name}", out_img.getvalue())

    st.success("✅ Hoàn tất xử lý!")
    st.download_button(
        label="📥 Tải về file ZIP tất cả ảnh đã sửa",
        data=zip_buffer.getvalue(),
        file_name="danh_sach_anh_da_sua.zip",
        mime="application/zip"
    )
