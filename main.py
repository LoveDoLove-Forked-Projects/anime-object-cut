from imgutils import detect
from PIL import Image
import os


def generate_square_avatar(image_path, output_path, target_size=512, padding_ratio=0.3):
    """
    基于头部检测生成正方形头像

    Args:
        image_path: 输入图片路径
        output_path: 输出头像路径
        target_size: 目标正方形尺寸 (像素)
        padding_ratio: 头部周围的扩展比例 (0.3表示在头部基础上向外扩展30%)
    """
    try:
        # 检测头部位置
        result = detect.detect_heads(image_path)
        if not result:
            print(f"未在 {image_path} 中检测到头部")
            return False

        # 获取第一个检测到的头部坐标 (置信度最高的)
        x0, y0, x1, y1 = result[0][0]  # 左上角和右下角坐标

        # 打开原图
        img = Image.open(image_path)
        img_width, img_height = img.size

        # 计算头部中心点和尺寸
        head_width = x1 - x0
        head_height = y1 - y0
        center_x = (x0 + x1) // 2
        center_y = (y0 + y1) // 2

        # 计算扩展后的正方形尺寸 (取较大的边作为基准)
        base_size = max(head_width, head_height)
        expanded_size = int(base_size * (1 + padding_ratio * 2))

        # 计算正方形裁剪区域的坐标
        crop_x0 = max(0, center_x - expanded_size // 2)
        crop_y0 = max(0, center_y - expanded_size // 2)
        crop_x1 = min(img_width, center_x + expanded_size // 2)
        crop_y1 = min(img_height, center_y + expanded_size // 2)

        # 直接使用裁剪的图像，不做正方形填充
        # 如果需要正方形，通过调整裁剪区域来实现
        crop_width = crop_x1 - crop_x0
        crop_height = crop_y1 - crop_y0

        # 重新计算正方形裁剪区域（使用原始图像内容）
        square_size = min(crop_width, crop_height)

        # 重新居中计算裁剪坐标，确保是正方形
        new_crop_x0 = center_x - square_size // 2
        new_crop_y0 = center_y - square_size // 2
        new_crop_x1 = center_x + square_size // 2
        new_crop_y1 = center_y + square_size // 2

        # 确保不超出图像边界
        if new_crop_x0 < 0:
            new_crop_x0 = 0
            new_crop_x1 = min(img_width, square_size)
        elif new_crop_x1 > img_width:
            new_crop_x1 = img_width
            new_crop_x0 = max(0, img_width - square_size)

        if new_crop_y0 < 0:
            new_crop_y0 = 0
            new_crop_y1 = min(img_height, square_size)
        elif new_crop_y1 > img_height:
            new_crop_y1 = img_height
            new_crop_y0 = max(0, img_height - square_size)

        # 重新裁剪为正方形
        square_img = img.crop((new_crop_x0, new_crop_y0, new_crop_x1, new_crop_y1))

        # 调整到目标尺寸
        final_img = square_img.resize(
            (target_size, target_size), Image.Resampling.LANCZOS
        )

        # 保存头像
        final_img.save(output_path)
        print(f"✓ 成功生成头像: {output_path}")
        return True

    except Exception as e:
        print(f"✗ 处理 {image_path} 时出错: {str(e)}")
        return False


def batch_generate_avatars(input_dir, output_dir, target_size=512, padding_ratio=0.3):
    """
    批量处理文件夹中的图片生成头像

    Args:
        input_dir: 输入图片文件夹路径
        output_dir: 输出头像文件夹路径
        target_size: 目标正方形尺寸
        padding_ratio: 头部周围的扩展比例
    """
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 支持的图片格式
    supported_formats = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}

    success_count = 0
    total_count = 0

    # 遍历输入目录中的所有图片
    for filename in os.listdir(input_dir):
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in supported_formats:
            continue

        input_path = os.path.join(input_dir, filename)
        # 输出文件名添加 _avatar 后缀
        name_without_ext = os.path.splitext(filename)[0]
        output_filename = f"{name_without_ext}_avatar.png"
        output_path = os.path.join(output_dir, output_filename)

        total_count += 1
        if generate_square_avatar(input_path, output_path, target_size, padding_ratio):
            success_count += 1

    print(f"\n批处理完成! 成功: {success_count}/{total_count}")


if __name__ == "__main__":
    print("=== 单张图片处理（纯原始内容）===")
    generate_square_avatar(
        image_path="image.png",
        output_path="avatar.png",
        target_size=512,
        padding_ratio=0.3,
    )
