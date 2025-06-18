import os
from pathlib import Path
from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    Request,
)
from starlette.background import BackgroundTask
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import asyncio
import tempfile

import gen
import utils

OUTPUT_DIR = Path(__file__).parent / "output"
INPUT_DIR = Path(__file__).parent / "input"
if not OUTPUT_DIR.exists():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
if not INPUT_DIR.exists():
    INPUT_DIR.mkdir(parents=True, exist_ok=True)


app = FastAPI(title="Cut Avatar API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    auth_header = request.headers.get("Authorization")
    api_key = os.getenv("API_KEY", "")
    if api_key:
        if not auth_header or auth_header != f"Bearer {api_key}":
            return Response(
                "Unauthorized",
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
    response = await call_next(request)
    return response


@app.get("/result/{id}")
async def download_result(id: str):
    result_file = OUTPUT_DIR / f"{id}.png"
    if not result_file.exists():
        raise HTTPException(status_code=404, detail="文件未找到")

    return FileResponse(
        result_file,
        filename=f"{id}.png",
        background=BackgroundTasks(
            [BackgroundTask(utils.cleanup_temp_file, [result_file])]
        ),
    )


@app.post("/cutone", description="从单个上传图像中生成指定对象的第一个正方形图片")
async def cut_image(
    type: gen.GenSquareType = Form(
        gen.GenSquareType.HEAD,
        description="要生成的对象类型",
    ),
    file: UploadFile = File(
        ...,
        description="上传的图片文件",
    ),
    size: int = Form(512, description="目标正方形边长 (像素)", ge=32),
    padding: float = Form(
        0.3,
        description="对象周围的扩展比例 (0.3表示在对象基础上向外扩展30%)",
        ge=0.0,
        le=1.0,
    ),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="文件类型不支持")

    img_path = Path(tempfile.mktemp(suffix=".png", dir=INPUT_DIR))
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="文件内容为空")

        if not img_path.parent.exists():
            img_path.parent.mkdir(parents=True, exist_ok=True)
        with open(img_path, "wb") as f:
            f.write(content)

        avatars = await asyncio.to_thread(
            gen.square,
            type=gen.GenSquareType(type),
            img_path=img_path,
            output_dir=OUTPUT_DIR,
            target_size=size,
            padding_ratio=padding,
        )
        if not avatars:
            raise HTTPException(status_code=500, detail="未检测到对象")
        avatar = avatars[0]
        return FileResponse(
            avatar,
            filename=f"{type}.png",
            background=BackgroundTasks(
                [BackgroundTask(utils.cleanup_temp_file, [img_path, *avatars])],
            ),
        )
    except Exception as e:
        logger.error(f"处理图片时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"图片处理错误: {str(e)}")
    finally:
        if img_path.exists():
            img_path.unlink(missing_ok=True)


@app.post("/cutall", description="从单个上传图像中生成指定对象的所有正方形图片")
async def cut_all_images(
    req: Request,
    type: gen.GenSquareType = Form(
        gen.GenSquareType.HEAD, description="要生成的对象类型"
    ),
    file: UploadFile = File(
        ...,
        description="上传的图片文件",
    ),
    size: int = Form(512, description="目标正方形边长 (像素)", ge=32),
    padding: float = Form(
        0.3,
        description="对象周围的扩展比例 (0.3表示在对象基础上向外扩展30%)",
        ge=0.0,
        le=1.0,
    ),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="文件类型不支持")

    img_path = Path(tempfile.mktemp(suffix=".png", dir=INPUT_DIR))
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="文件内容为空")

        if not img_path.parent.exists():
            img_path.parent.mkdir(parents=True, exist_ok=True)
        with open(img_path, "wb") as f:
            f.write(content)

        avatars = await asyncio.to_thread(
            gen.square,
            type=gen.GenSquareType(type),
            img_path=img_path,
            output_dir=OUTPUT_DIR,
            target_size=size,
            padding_ratio=padding,
        )
        if not avatars:
            raise HTTPException(status_code=500, detail="未检测到对象")

        return {
            "message": "生成成功",
            "count": len(avatars),
            "urls": [
                f"{str(req.base_url).removesuffix('/')}/result/{avatar.stem}"
                for avatar in avatars
            ],
        }
    except Exception as e:
        logger.error(f"处理图片时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"图片处理错误: {str(e)}")
    finally:
        if img_path.exists():
            img_path.unlink(missing_ok=True)


@app.post("/mask", description="标记识别到的对象区域")
async def mask_image(
    file: UploadFile = File(
        ...,
        description="上传的图片文件",
    ),
    type: gen.GenSquareType = Form(
        gen.GenSquareType.HEAD,
        description="要标记的对象类型",
    ),
    padding: float = Form(
        0.2,
        description="对象周围的扩展比例 (0.3表示在对象基础上向外扩展30%)",
        ge=0.0,
        le=1.0,
    ),
    color: str = Form(
        "red",
        description="标记颜色",
    ),
    width: int = Form(
        8,
        description="标记线条宽度 (像素)",
        ge=1,
        le=32,
    ),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="文件类型不支持")

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="文件内容为空")
        img_path = Path(tempfile.mktemp(suffix=".png", dir=INPUT_DIR))
        with open(img_path, "wb") as f:
            f.write(content)
        result = await asyncio.to_thread(
            gen.mask,
            type=gen.GenSquareType(type),
            img_path=img_path,
            output_dir=OUTPUT_DIR,
            padding_ratio=padding,
            color=color,
            width=width,
        )
        if not result:
            raise HTTPException(status_code=500, detail="标记生成失败")
        return FileResponse(
            result,
            filename=f"{type}_mask.png",
            background=BackgroundTasks(
                [BackgroundTask(utils.cleanup_temp_file, [img_path, result])],
            ),
        )

    except Exception as e:
        logger.error(f"处理图片时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"图片处理错误: {str(e)}")


@app.post("/highlight", description="高亮识别到的对象区域")
async def highlight_image(
    file: UploadFile = File(
        ...,
        description="上传的图片文件",
    ),
    type: gen.GenSquareType = Form(
        gen.GenSquareType.HEAD,
        description="要标记的对象类型",
    ),
    padding: float = Form(
        0.2,
        description="对象周围的扩展比例 (0.3表示在对象基础上向外扩展30%)",
        ge=0.0,
        le=1.0,
    ),
    with_mask: bool = Form(
        False,
        description="是否同时生成遮罩",
    ),
    blur_radius: float = Form(
        15.0,
        description="高亮模糊半径 (像素)",
        ge=0.0,
        le=100.0,
    ),
    mask_color: str = Form(
        "red",
        description="标记颜色",
    ),
    mask_width: int = Form(
        8,
        description="标记线条宽度 (像素)",
        ge=1,
        le=32,
    ),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="文件类型不支持")

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="文件内容为空")
        img_path = Path(tempfile.mktemp(suffix=".png", dir=INPUT_DIR))
        with open(img_path, "wb") as f:
            f.write(content)
        result = await asyncio.to_thread(
            gen.highlight,
            type=gen.GenSquareType(type),
            img_path=img_path,
            output_dir=OUTPUT_DIR,
            padding_ratio=padding,
            blur_radius=blur_radius,
            with_mask=with_mask,
            mask_color=mask_color,
            mask_width=mask_width,
        )
        if not result:
            raise HTTPException(status_code=500, detail="高亮生成失败")
        return FileResponse(
            result,
            filename=f"{type}_highlight.png",
            background=BackgroundTasks(
                [BackgroundTask(utils.cleanup_temp_file, [img_path, result])],
            ),
        )

    except Exception as e:
        logger.error(f"处理图片时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"图片处理错误: {str(e)}")


# for compatibility
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

        img_path = Path(tempfile.mktemp(suffix=".png", dir=INPUT_DIR))
        with open(img_path, "wb") as f:
            f.write(content)
        avatars = await asyncio.to_thread(
            gen.square,
            type=gen.GenSquareType.HEAD,
            img_path=img_path,
            output_dir=OUTPUT_DIR,
            target_size=size,
            padding_ratio=padding,
        )
        if not avatars:
            raise HTTPException(status_code=500, detail="头像生成失败")
        avatar = avatars[0]
        return FileResponse(
            avatar,
            filename="avatar.png",
            background=BackgroundTasks(
                [BackgroundTask(utils.cleanup_temp_file, [img_path, *avatars])],
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
