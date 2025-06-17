import os
from pathlib import Path
from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    Header,
    UploadFile,
)
from starlette.background import BackgroundTask
from fastapi.responses import FileResponse
from imgutils import detect
from PIL import Image
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import asyncio
import tempfile


def generate_square_avatar(
    img_path: Path,
    output_path: Path,
    target_size: int = 512,
    padding_ratio: float = 0.3,
) -> Path | None:
    """
    基于头部检测生成正方形头像

    Args:
        image_path: 输入图片路径
        output_path: 输出头像路径
        target_size: 目标正方形尺寸 (像素)
        padding_ratio: 头部周围的扩展比例 (0.3表示在头部基础上向外扩展30%)
    """
    result = detect.detect_heads(img_path)
    if not result:
        logger.error("未检测到头像")
        return None

    x0, y0, x1, y1 = result[0][0]

    # 打开图片
    img = Image.open(img_path)
    img_width, img_height = img.size

    # 计算头部中心点和扩展后的正方形尺寸
    center_x = (x0 + x1) // 2
    center_y = (y0 + y1) // 2
    base_size = max(x1 - x0, y1 - y0)
    expanded_size = int(base_size * (1 + padding_ratio * 2))

    # 计算正方形裁剪区域的初始坐标
    half_size = expanded_size // 2
    crop_x0 = max(0, center_x - half_size)
    crop_y0 = max(0, center_y - half_size)
    crop_x1 = min(img_width, center_x + half_size)
    crop_y1 = min(img_height, center_y + half_size)

    # 调整为正方形并确保不超出边界
    square_size = min(crop_x1 - crop_x0, crop_y1 - crop_y0)

    new_crop_x0 = max(0, min(center_x - square_size // 2, img_width - square_size))
    new_crop_y0 = max(0, min(center_y - square_size // 2, img_height - square_size))
    new_crop_x1 = new_crop_x0 + square_size
    new_crop_y1 = new_crop_y0 + square_size

    # 裁剪、调整尺寸并保存
    square_img = img.crop((new_crop_x0, new_crop_y0, new_crop_x1, new_crop_y1))
    final_img = square_img.resize((target_size, target_size), Image.Resampling.LANCZOS)
    final_img.save(output_path, format="PNG")
    logger.info(f"头像已保存到: {output_path}")
    return output_path


def cleanup_temp_file(file_path: Path):
    """清理临时文件"""
    try:
        if file_path.exists():
            file_path.unlink()
            logger.info(f"已删除临时文件: {file_path}")
    except Exception as e:
        logger.error(f"删除临时文件失败: {str(e)}")


app = FastAPI(title="Cut Avatar API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def authenticate(auth_header: str = Header(...)):
    api_key = os.getenv("API_KEY", "")
    if api_key:
        if auth_header != "Bearer " + api_key:
            raise HTTPException(
                status_code=401,
                detail="认证失败",
                headers={"WWW-Authenticate": "Basic"},
            )


@app.post("/cut/avatar")
async def cut_avatar(
    file: UploadFile = File(
        ...,
        description="上传的图片文件",
    ),
    size: int = Form(512, description="目标正方形边长 (像素)", ge=32),
    padding: float = Form(
        0.3,
        description="头像周围的扩展比例 (0.3表示在头部基础上向外扩展30%)",
        ge=0.0,
        le=1.0,
    ),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="文件类型不支持")

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="文件内容为空")

        img_path = Path(tempfile.mktemp(suffix=".png", prefix="aniobjcut_"))
        with open(img_path, "wb") as f:
            f.write(content)
        avatar = await asyncio.to_thread(
            generate_square_avatar,
            img_path=img_path,
            output_path=Path(tempfile.mktemp(suffix=".png", prefix="aniobjcut_")),
            target_size=size,
            padding_ratio=padding,
        )
        if not avatar:
            raise HTTPException(status_code=500, detail="头像生成失败")
        return FileResponse(
            avatar,
            filename="avatar.png",
            background=BackgroundTasks(
                [
                    BackgroundTask(cleanup_temp_file, img_path),
                    BackgroundTask(cleanup_temp_file, avatar),
                ]
            ),
        )

    except Exception as e:
        logger.error(f"处理图片时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"图片处理错误: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 39728))
    uvicorn.run(app, host=host, port=port)
