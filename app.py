import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile
import os
import urllib.request


# ============================================================
# CẤU HÌNH
# ============================================================

st.set_page_config(
    page_title="vTools Metadata Editor",
    page_icon="📷",
    layout="wide"
)

st.title("📷 vTools Metadata Editor")
st.caption(
    "Xóa vùng metadata cũ, phục hồi nền bằng inpainting và thêm metadata mới."
)


# ============================================================
# FONT ROBOTO
# ============================================================

@st.cache_resource
def load_font(font_size):

    filename = "Roboto-Regular.ttf"

    if not os.path.exists(filename):

        urls = [
            "https://raw.githubusercontent.com/google/fonts/main/apache/roboto/Roboto-Regular.ttf",
            "https://cdnjs.cloudflare.com/ajax/libs/ink/3.1.10/fonts/Roboto/roboto-regular-webfont.ttf"
        ]

        for url in urls:

            try:
                urllib.request.urlretrieve(
                    url,
                    filename
                )

                if (
                    os.path.exists(filename)
                    and os.path.getsize(filename) > 0
                ):
                    break

            except Exception:
                pass

    if os.path.exists(filename):

        try:
            return ImageFont.truetype(
                filename,
                int(font_size)
            )
        except Exception:
            pass

    return ImageFont.load_default()


# ============================================================
# PHÁT HIỆN CHỮ TRẮNG
# ============================================================

def detect_white_text_mask(
    roi,
    brightness_threshold=165,
    saturation_threshold=90,
    min_component_area=2
):

    """
    Tạo mask cho chữ trắng.

    Không lấy toàn bộ pixel sáng.
    Chỉ ưu tiên:
        - sáng
        - ít bão hòa
        - có cấu trúc giống nét chữ
    """

    hsv = cv2.cvtColor(
        roi,
        cv2.COLOR_BGR2HSV
    )

    h, s, v = cv2.split(hsv)

    # Chữ trắng thường:
    # V cao
    # S thấp
    white = (
        (v >= brightness_threshold) &
        (s <= saturation_threshold)
    ).astype(np.uint8) * 255

    # Loại nhiễu nhỏ
    kernel_open = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (2, 2)
    )

    white = cv2.morphologyEx(
        white,
        cv2.MORPH_OPEN,
        kernel_open
    )

    # Kết nối các phần nhỏ của ký tự
    kernel_close = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (2, 2)
    )

    white = cv2.morphologyEx(
        white,
        cv2.MORPH_CLOSE,
        kernel_close
    )

    # Loại component quá nhỏ
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        white,
        connectivity=8
    )

    cleaned = np.zeros_like(white)

    for i in range(1, num_labels):

        area = stats[i, cv2.CC_STAT_AREA]

        if area >= min_component_area:

            cleaned[
                labels == i
            ] = 255

    return cleaned


# ============================================================
# XÓA METADATA CŨ
# ============================================================

def remove_old_metadata(
    img,
    x,
    y,
    width,
    height,
    threshold=165,
    saturation=90,
    dilation=2,
    inpaint_radius=3
):

    """
    Chỉ xử lý vùng metadata được chỉ định.

    Không làm tối toàn bộ ROI.
    """

    h, w = img.shape[:2]

    x1 = max(0, int(x))
    y1 = max(0, int(y))

    x2 = min(
        w,
        int(x + width)
    )

    y2 = min(
        h,
        int(y + height)
    )

    if x2 <= x1 or y2 <= y1:
        return img.copy()

    result = img.copy()

    roi = result[
        y1:y2,
        x1:x2
    ].copy()

    if roi.size == 0:
        return result

    # --------------------------------------------------------
    # Detect chữ trắng
    # --------------------------------------------------------

    mask = detect_white_text_mask(
        roi,
        brightness_threshold=threshold,
        saturation_threshold=saturation
    )

    # --------------------------------------------------------
    # Mở rộng mask vừa đủ quanh nét chữ
    # --------------------------------------------------------

    if dilation > 0:

        kernel_size = (
            dilation * 2 + 1
        )

        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (
                kernel_size,
                kernel_size
            )
        )

        mask = cv2.dilate(
            mask,
            kernel,
            iterations=1
        )

    # --------------------------------------------------------
    # Làm mềm biên mask
    # --------------------------------------------------------

    mask = cv2.GaussianBlur(
        mask,
        (3, 3),
        0
    )

    # --------------------------------------------------------
    # Inpaint
    # --------------------------------------------------------

    repaired = cv2.inpaint(
        roi,
        mask,
        inpaintRadius=inpaint_radius,
        flags=cv2.INPAINT_TELEA
    )

    result[
        y1:y2,
        x1:x2
    ] = repaired

    return result


# ============================================================
# VẼ METADATA MỚI
# ============================================================

def draw_new_metadata(
    img,
    line1,
    line2,
    font_size,
    line_spacing,
    margin_left,
    margin_bottom,
    add_edit_label=True
):

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

    font = load_font(
        font_size
    )

    h, w = img.shape[:2]

    # --------------------------------------------------------
    # Vị trí
    # --------------------------------------------------------

    y2 = (
        h
        - margin_bottom
        - font_size
    )

    y1 = (
        y2
        - line_spacing
    )

    x = margin_left

    # --------------------------------------------------------
    # Dòng 1
    # --------------------------------------------------------

    if line1:

        draw.text(
            (x, y1),
            line1,
            font=font,
            fill=(
                255,
                255,
                255,
                255
            ),
            stroke_width=1,
            stroke_fill=(
                0,
                0,
                0,
                175
            )
        )

    # --------------------------------------------------------
    # Dòng 2
    # --------------------------------------------------------

    if line2:

        draw.text(
            (x, y2),
            line2,
            font=font,
            fill=(
                255,
                255,
                255,
                255
            ),
            stroke_width=1,
            stroke_fill=(
                0,
                0,
                0,
                175
            )
        )

    # --------------------------------------------------------
    # Nhãn chỉnh sửa
    # --------------------------------------------------------

    if add_edit_label:

        small_size = max(
            12,
            int(font_size * 0.55)
        )

        small_font = load_font(
            small_size
        )

        label = "ĐÃ CHỈNH SỬA"

        label_y = (
            y1
            - small_size
            - 7
        )

        draw.text(
            (x, label_y),
            label,
            font=small_font,
            fill=(
                255,
                220,
                0,
                255
            ),
            stroke_width=1,
            stroke_fill=(
                0,
                0,
                0,
                200
            )
        )

    result = np.array(
        pil_img.convert("RGB")
    )

    return cv2.cvtColor(
        result,
        cv2.COLOR_RGB2BGR
    )


# ============================================================
# UPLOAD
# ============================================================

uploaded_files = st.file_uploader(
    "Tải ảnh JPG / PNG",
    type=[
        "jpg",
        "jpeg",
        "png"
    ],
    accept_multiple_files=True
)


# ============================================================
# NỘI DUNG MỚI
# ============================================================

st.subheader(
    "1. Nội dung metadata mới"
)

line1 = st.text_input(
    "Dòng ngày",
    "Thứ Bảy, 15 tháng 2 2025"
)

line2 = st.text_input(
    "Dòng giờ",
    "09:28:23 GMT+07:00"
)


# ============================================================
# VÙNG METADATA CŨ
# ============================================================

st.subheader(
    "2. Vùng metadata cũ cần xử lý"
)

col1, col2, col3 = st.columns(3)

with col1:

    old_x = st.number_input(
        "X",
        min_value=0,
        value=20
    )

    old_y = st.number_input(
        "Y",
        min_value=0,
        value=650
    )

with col2:

    old_width = st.number_input(
        "Chiều rộng",
        min_value=10,
        value=500
    )

    old_height = st.number_input(
        "Chiều cao",
        min_value=10,
        value=100
    )

with col3:

    threshold = st.slider(
        "Ngưỡng chữ trắng",
        100,
        230,
        165
    )

    dilation = st.slider(
        "Độ mở rộng mask",
        0,
        5,
        2
    )


# ============================================================
# THÔNG SỐ CHỮ
# ============================================================

st.subheader(
    "3. Vị trí metadata mới"
)

col1, col2 = st.columns(2)

with col1:

    margin_left = st.number_input(
        "Lề trái",
        min_value=0,
        max_value=500,
        value=25
    )

    margin_bottom = st.number_input(
        "Lề dưới",
        min_value=0,
        max_value=500,
        value=45
    )

with col2:

    font_size = st.number_input(
        "Cỡ chữ",
        min_value=8,
        max_value=100,
        value=28
    )

    line_spacing = st.number_input(
        "Khoảng cách dòng",
        min_value=10,
        max_value=100,
        value=34
    )


# ============================================================
# PREVIEW
# ============================================================

if uploaded_files:

    first_file = uploaded_files[0]

    first_file.seek(0)

    data = np.asarray(
        bytearray(
            first_file.read()
        ),
        dtype=np.uint8
    )

    preview = cv2.imdecode(
        data,
        cv2.IMREAD_COLOR
    )

    if preview is not None:

        # Xóa metadata cũ
        cleaned = remove_old_metadata(
            preview,
            old_x,
            old_y,
            old_width,
            old_height,
            threshold=threshold,
            dilation=dilation
        )

        # Thêm metadata mới
        result = draw_new_metadata(
            cleaned,
            line1,
            line2,
            font_size,
            line_spacing,
            margin_left,
            margin_bottom,
            add_edit_label=True
        )

        result_rgb = cv2.cvtColor(
            result,
            cv2.COLOR_BGR2RGB
        )

        st.image(
            result_rgb,
            caption="Xem trước",
            use_container_width=True
        )


# ============================================================
# XỬ LÝ HÀNG LOẠT
# ============================================================

if uploaded_files:

    if st.button(
        "🚀 Xử lý hàng loạt",
        type="primary"
    ):

        zip_buffer = io.BytesIO()

        total = len(
            uploaded_files
        )

        progress = st.progress(0)

        with zipfile.ZipFile(
            zip_buffer,
            "w",
            zipfile.ZIP_DEFLATED
        ) as zip_file:

            for index, uploaded_file in enumerate(
                uploaded_files
            ):

                uploaded_file.seek(0)

                data = np.asarray(
                    bytearray(
                        uploaded_file.read()
                    ),
                    dtype=np.uint8
                )

                img = cv2.imdecode(
                    data,
                    cv2.IMREAD_COLOR
                )

                if img is None:
                    continue

                # ------------------------------------------------
                # Xóa metadata cũ
                # ------------------------------------------------

                cleaned = remove_old_metadata(
                    img,
                    old_x,
                    old_y,
                    old_width,
                    old_height,
                    threshold=threshold,
                    dilation=dilation
                )

                # ------------------------------------------------
                # Thêm metadata mới
                # ------------------------------------------------

                final_img = draw_new_metadata(
                    cleaned,
                    line1,
                    line2,
                    font_size,
                    line_spacing,
                    margin_left,
                    margin_bottom,
                    add_edit_label=True
                )

                # ------------------------------------------------
                # JPEG chất lượng cao
                # ------------------------------------------------

                success, encoded = cv2.imencode(
                    ".jpg",
                    final_img,
                    [
                        int(
                            cv2.IMWRITE_JPEG_QUALITY
                        ),
                        98
                    ]
                )

                if not success:
                    continue

                original_name = os.path.splitext(
                    uploaded_file.name
                )[0]

                output_name = (
                    original_name
                    + "_edited.jpg"
                )

                zip_file.writestr(
                    output_name,
                    encoded.tobytes()
                )

                progress.progress(
                    (index + 1) / total
                )

        st.success(
            f"✅ Đã xử lý {total} ảnh."
        )

        st.download_button(
            label="📥 Tải ZIP kết quả",
            data=zip_buffer.getvalue(),
            file_name="vtools_edited_images.zip",
            mime="application/zip"
        )
