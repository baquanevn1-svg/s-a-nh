import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile
import os
import urllib.request


# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="vTools Image Editor",
    page_icon="📷",
    layout="wide"
)

st.title("📷 vTools Image Editor")
st.caption(
    "Thay đổi nội dung hiển thị mà không dùng vùng inpaint làm biến dạng nền ảnh."
)


# ============================================================
# FONT
# ============================================================

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
                urllib.request.urlretrieve(
                    url,
                    font_filename
                )

                if (
                    os.path.exists(font_filename)
                    and os.path.getsize(font_filename) > 0
                ):
                    break

            except Exception:
                continue

    if os.path.exists(font_filename):

        try:
            return ImageFont.truetype(
                font_filename,
                int(font_size)
            )
        except Exception:
            pass

    return ImageFont.load_default()


# ============================================================
# DRAW TEXT
# ============================================================

def draw_metadata(
    img,
    line1,
    line2,
    font_size,
    line_spacing,
    margin_left,
    margin_bottom,
    add_label=True
):

    """
    Không sử dụng cv2.inpaint().
    Không sửa pixel nền cũ.
    Chỉ vẽ lớp chữ mới lên ảnh.
    """

    # OpenCV BGR -> PIL RGB
    rgb = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2RGB
    )

    pil_img = Image.fromarray(
        rgb
    ).convert("RGBA")

    draw = ImageDraw.Draw(
        pil_img
    )

    font = load_custom_font(
        font_size
    )

    h, w = img.shape[:2]

    # --------------------------------------------------------
    # Tọa độ
    # --------------------------------------------------------

    y2 = h - margin_bottom - font_size
    y1 = y2 - line_spacing

    x = margin_left

    # --------------------------------------------------------
    # Text mới
    # --------------------------------------------------------

    if line1:

        draw.text(
            (x, y1),
            line1,
            font=font,
            fill=(255, 255, 255, 255),

            # viền mảnh để chữ dễ đọc
            stroke_width=1,
            stroke_fill=(0, 0, 0, 170)
        )

    if line2:

        draw.text(
            (x, y2),
            line2,
            font=font,
            fill=(255, 255, 255, 255),

            stroke_width=1,
            stroke_fill=(0, 0, 0, 170)
        )

    # --------------------------------------------------------
    # Nhãn minh bạch
    # --------------------------------------------------------

    if add_label:

        label_font_size = max(
            14,
            int(font_size * 0.65)
        )

        label_font = load_custom_font(
            label_font_size
        )

        label = "ĐÃ CHỈNH SỬA"

        label_y = y1 - label_font_size - 8

        draw.text(
            (x, label_y),
            label,
            font=label_font,
            fill=(255, 220, 0, 255),
            stroke_width=1,
            stroke_fill=(0, 0, 0, 200)
        )

    # --------------------------------------------------------
    # PIL -> OpenCV
    # --------------------------------------------------------

    result = np.array(
        pil_img.convert("RGB")
    )

    return cv2.cvtColor(
        result,
        cv2.COLOR_RGB2BGR
    )


# ============================================================
# FILE UPLOAD
# ============================================================

uploaded_files = st.file_uploader(
    "Tải lên ảnh vTools",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)


# ============================================================
# SETTINGS
# ============================================================

st.subheader("1. Nội dung hiển thị")

line1 = st.text_input(
    "Dòng ngày:",
    "Thứ Bảy, 15 tháng 2 2025"
)

line2 = st.text_input(
    "Dòng giờ:",
    "09:28:23 GMT+07:00"
)


st.subheader("2. Căn chỉnh")

col1, col2 = st.columns(2)

with col1:

    margin_bottom = st.number_input(
        "Khoảng cách từ đáy ảnh (px)",
        min_value=0,
        max_value=500,
        value=45
    )

    margin_left = st.number_input(
        "Khoảng cách từ trái (px)",
        min_value=0,
        max_value=500,
        value=25
    )


with col2:

    font_size = st.number_input(
        "Kích thước chữ (px)",
        min_value=8,
        max_value=100,
        value=28
    )

    line_spacing = st.number_input(
        "Khoảng cách giữa hai dòng (px)",
        min_value=10,
        max_value=150,
        value=34
    )


# ============================================================
# PREVIEW
# ============================================================

if uploaded_files:

    first_file = uploaded_files[0]

    file_bytes = np.asarray(
        bytearray(first_file.read()),
        dtype=np.uint8
    )

    first_file.seek(0)

    preview_img = cv2.imdecode(
        file_bytes,
        cv2.IMREAD_COLOR
    )

    if preview_img is not None:

        preview_result = draw_metadata(
            preview_img.copy(),
            line1,
            line2,
            font_size,
            line_spacing,
            margin_left,
            margin_bottom,
            add_label=True
        )

        preview_rgb = cv2.cvtColor(
            preview_result,
            cv2.COLOR_BGR2RGB
        )

        st.image(
            preview_rgb,
            caption="Xem trước",
            use_container_width=True
        )


# ============================================================
# PROCESS BUTTON
# ============================================================

if uploaded_files:

    if st.button(
        "🚀 Bắt đầu xử lý hàng loạt",
        type="primary"
    ):

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(
            zip_buffer,
            "w",
            zipfile.ZIP_DEFLATED
        ) as zip_file:

            progress = st.progress(0)

            total = len(uploaded_files)

            for idx, uploaded_file in enumerate(
                uploaded_files
            ):

                # --------------------------------------------
                # Read image
                # --------------------------------------------

                uploaded_file.seek(0)

                file_bytes = np.asarray(
                    bytearray(uploaded_file.read()),
                    dtype=np.uint8
                )

                img = cv2.imdecode(
                    file_bytes,
                    cv2.IMREAD_COLOR
                )

                if img is None:
                    continue

                # --------------------------------------------
                # Draw new metadata
                # --------------------------------------------

                final_img = draw_metadata(
                    img,
                    line1,
                    line2,
                    font_size,
                    line_spacing,
                    margin_left,
                    margin_bottom,
                    add_label=True
                )

                # --------------------------------------------
                # JPEG quality
                # --------------------------------------------

                success, encoded = cv2.imencode(
                    ".jpg",
                    final_img,
                    [
                        int(cv2.IMWRITE_JPEG_QUALITY),
                        98
                    ]
                )

                if not success:
                    continue

                # --------------------------------------------
                # Add to ZIP
                # --------------------------------------------

                output_name = (
                    "edited_" +
                    os.path.splitext(
                        uploaded_file.name
                    )[0] +
                    ".jpg"
                )

                zip_file.writestr(
                    output_name,
                    encoded.tobytes()
                )

                progress.progress(
                    (idx + 1) / total
                )

        st.success(
            "✅ Đã xử lý xong!"
        )

        st.download_button(
            label="📥 Tải ZIP kết quả",
            data=zip_buffer.getvalue(),
            file_name="vtools_edited_images.zip",
            mime="application/zip"
        )
