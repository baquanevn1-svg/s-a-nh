import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile
import os
import urllib.request

st.set_page_config(page_title=&quot;Công cụ Sửa Ngày Tháng Ảnh Khảo Sát&quot;, layout=&quot;wide&quot;)
st.title(&quot;�� Công cụ Sửa 2 Dòng Ngày/Giờ Ảnh Khảo Sát&quot;)

# =========================
# LOAD FONT
# =========================
@st.cache_resource
def load_custom_font(font_size):
font_filename = &quot;Roboto-Regular.ttf&quot;

if not os.path.exists(font_filename):
urls = [
&quot;https://raw.githubusercontent.com/google/fonts/main/apache/roboto/Roboto-Regular.ttf&quot;,
&quot;https://cdnjs.cloudflare.com/ajax/libs/ink/3.1.10/fonts/Roboto/roboto-regular-webfont.ttf&quot;,
]
for url in urls:
try:
urllib.request.urlretrieve(url, font_filename)
if os.path.exists(font_filename) and os.path.getsize(font_filename) &gt; 0:
break
except Exception:
continue

if os.path.exists(font_filename) and os.path.getsize(font_filename) &gt; 0:
try:
return ImageFont.truetype(font_filename, int(font_size))
except Exception:
pass

return ImageFont.load_default()

# =========================
# TẠO MASK CHỈ CHO CHỮ TRONG ROI
# =========================
def auto_text_mask(roi_bgr):
&quot;&quot;&quot;
Phát hiện vùng chữ trắng/sáng trong ROI để chỉ xóa text,
hạn chế ăn lan ra nền.
&quot;&quot;&quot;
gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)

h, s, v = cv2.split(hsv)

# Điều kiện chữ sáng/trắng
mask_bright = (v &gt; 170).astype(np.uint8) * 255
mask_low_sat = (s &lt; 110).astype(np.uint8) * 255

# Tăng độ chắc chắn bằng tương phản cục bộ
blur = cv2.GaussianBlur(gray, (0, 0), 3)
local_contrast = (gray &gt; (blur + 18)).astype(np.uint8) * 255

mask = cv2.bitwise_and(mask_bright, mask_low_sat)
mask = cv2.bitwise_and(mask, local_contrast)

# Làm sạch mask
kernel = np.ones((2, 2), np.uint8)
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

# Lọc component nhiễu nhỏ
num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
filtered = np.zeros_like(mask)

for i in range(1, num_labels):
x, y, w, h, area = stats[i]
if 6 &lt;= area &lt;= 5000 and h &lt;= 80 and w &lt;= roi_bgr.shape[1]:
filtered[labels == i] = 255

# Nở rất nhẹ để phủ hết viền chữ + shadow cũ
filtered = cv2.dilate(filtered, np.ones((2, 2), np.uint8), iterations=1)
return filtered

# =========================
# TẠO MASK THEO TEMPLATE CHỮ CŨ
# =========================
def template_text_mask(roi_shape, old_lines, font, line_gap=4):
&quot;&quot;&quot;
Tạo mask từ chính nội dung chữ cũ.
ROI được hiểu là vùng chỉ chứa 2 dòng cuối.
&quot;&quot;&quot;
h, w = roi_shape[:2]

mask_img = Image.new(&quot;L&quot;, (w, h), 0)
draw = ImageDraw.Draw(mask_img)

# chiều cao dòng
bbox = font.getbbox(&quot;Ag&quot;)
line_h = bbox[3] - bbox[1]

y = 0
for line in old_lines:
if not line.strip():
continue
# vẽ text chính
draw.text((0, y), line, fill=255, font=font)
# vẽ thêm shadow lệch 1px để phủ luôn phần bóng cũ
draw.text((1, y + 1), line, fill=255, font=font)
y += line_h + line_gap

mask = np.array(mask_img)

# nở nhẹ để phủ đủ viền anti-alias
mask = cv2.dilate(mask, np.ones((2, 2), np.uint8), iterations=1)
return mask

# =========================
# VẼ CHỮ MỚI GIỐNG STYLE ẢNH GỐC
# =========================
def draw_survey_text(base_pil, x, y, new_lines, font, line_gap=4):
&quot;&quot;&quot;
Vẽ chữ trắng + shadow xám đậm, mềm, đồng đều hơn.
&quot;&quot;&quot;

base_rgba = base_pil.convert(&quot;RGBA&quot;)
overlay = Image.new(&quot;RGBA&quot;, base_rgba.size, (0, 0, 0, 0))
draw = ImageDraw.Draw(overlay)

bbox = font.getbbox(&quot;Ag&quot;)
line_h = bbox[3] - bbox[1]

current_y = y
for line in new_lines:
if not line.strip():
current_y += line_h + line_gap
continue

# Shadow mỏng giống app khảo sát
draw.text((x + 1, current_y + 1), line, font=font, fill=(35, 35, 35, 150))
# Text trắng
draw.text((x, current_y), line, font=font, fill=(255, 255, 255, 235))

current_y += line_h + line_gap

result = Image.alpha_composite(base_rgba, overlay)
return result.convert(&quot;RGB&quot;)

# =========================
# UI
# =========================
uploaded_files = st.file_uploader(
&quot;Tải lên danh sách ảnh (JPG, JPEG, PNG)&quot;,
type=[&quot;jpg&quot;, &quot;jpeg&quot;, &quot;png&quot;],
accept_multiple_files=True

)

st.markdown(&quot;### Nội dung 2 dòng cũ&quot;)
col_old1, col_old2 = st.columns(2)
with col_old1:
old_line1 = st.text_input(&quot;Dòng cũ 1&quot;, &quot;Thứ Bảy, 15 tháng 2 2025&quot;)
with col_old2:
old_line2 = st.text_input(&quot;Dòng cũ 2&quot;, &quot;09:31:23 GMT+07:00&quot;)

st.markdown(&quot;### Nội dung 2 dòng mới&quot;)
col_new1, col_new2 = st.columns(2)
with col_new1:
new_line1 = st.text_input(&quot;Dòng mới 1&quot;, &quot;Thứ Bảy, 22 tháng 2 2026&quot;)
with col_new2:
new_line2 = st.text_input(&quot;Dòng mới 2&quot;, &quot;09:52:23 GMT+07:00&quot;)

st.markdown(&quot;### Cấu hình vùng xử lý&quot;)
col1, col2, col3 = st.columns(3)

with col1:
crop_x = st.number_input(&quot;X vùng chữ&quot;, value=16, step=1)
crop_y = st.number_input(&quot;Y vùng chữ&quot;, value=1745, step=1)

with col2:
crop_w = st.number_input(&quot;Rộng vùng xử lý&quot;, value=360, step=1)
crop_h = st.number_input(&quot;Cao vùng xử lý&quot;, value=95, step=1)

with col3:
font_size = st.number_input(&quot;Cỡ chữ&quot;, value=22, step=1)
line_gap = st.number_input(&quot;Khoảng cách 2 dòng&quot;, value=4, step=1)

inpaint_radius = st.number_input(&quot;Mức làm sạch nền&quot;, value=2, min_value=1, max_value=5,
step=1)

st.markdown(&quot;### Tùy chọn nâng cao&quot;)
use_auto_mask = st.checkbox(&quot;Dùng mask tự động theo ảnh&quot;, value=True)
use_template_mask = st.checkbox(&quot;Dùng mask theo chữ cũ&quot;, value=True)

if uploaded_files and st.button(&quot;Xử lý ảnh&quot;):
zip_buffer = io.BytesIO()

font = load_custom_font(int(font_size))
old_lines = [old_line1, old_line2]
new_lines = [new_line1, new_line2]

with zipfile.ZipFile(zip_buffer, &quot;a&quot;, zipfile.ZIP_DEFLATED, False) as zip_file:
for uploaded_file in uploaded_files:
file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

if img is None:
continue

h, w, _ = img.shape

x1 = max(0, int(crop_x))
y1 = max(0, int(crop_y))
x2 = min(w, x1 + int(crop_w))
y2 = min(h, y1 + int(crop_h))

roi = img[y1:y2, x1:x2].copy()

if roi.size == 0:
continue

masks = []

if use_auto_mask:
mask_auto = auto_text_mask(roi)
masks.append(mask_auto)

if use_template_mask:
mask_tpl = template_text_mask(
roi.shape,
old_lines=old_lines,
font=font,
line_gap=int(line_gap)
)
masks.append(mask_tpl)

if len(masks) == 0:
final_mask = np.zeros(roi.shape[:2], dtype=np.uint8)
else:
final_mask = masks[0]
for m in masks[1:]:
final_mask = cv2.bitwise_or(final_mask, m)

# Inpaint chỉ phần chữ, không đụng cả nền hình chữ nhật
cleaned_roi = cv2.inpaint(
roi,
final_mask,
inpaintRadius=int(inpaint_radius),
flags=cv2.INPAINT_TELEA

)

img[y1:y2, x1:x2] = cleaned_roi

# Vẽ lại chữ mới
img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
pil_img = Image.fromarray(img_rgb)
pil_img = draw_survey_text(
pil_img,
x=x1,
y=y1,
new_lines=new_lines,
font=font,
line_gap=int(line_gap)
)

final_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

ext = os.path.splitext(uploaded_file.name)[1].lower()
if ext in [&quot;.jpg&quot;, &quot;.jpeg&quot;]:
success, encoded_img = cv2.imencode(
&quot;.jpg&quot;, final_img, [int(cv2.IMWRITE_JPEG_QUALITY), 98]
)
save_name = f&quot;edited_{os.path.splitext(uploaded_file.name)[0]}.jpg&quot;
else:
success, encoded_img = cv2.imencode(&quot;.png&quot;, final_img)
save_name = f&quot;edited_{os.path.splitext(uploaded_file.name)[0]}.png&quot;

if success:
zip_file.writestr(save_name, encoded_img.tobytes())

st.success(&quot;✅ Hoàn tất xử lý!&quot;)
st.download_button(
label=&quot;�� Tải về file ZIP tất cả ảnh đã sửa&quot;,
data=zip_buffer.getvalue(),
file_name=&quot;danh_sach_anh_da_sua.zip&quot;,
mime=&quot;application/zip&quot;
)
