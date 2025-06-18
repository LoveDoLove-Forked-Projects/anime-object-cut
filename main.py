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


@app.get("/result/{id}")
async def download_result(
    id: str,
    auth_header: str = Header(None, description="认证头部"),
):
    authenticate(auth_header)

    output_dir = Path(__file__).parent / "output"
    result_file = output_dir / f"{id}.png"
    if not result_file.exists():
        raise HTTPException(status_code=404, detail="文件未找到")

    return FileResponse(
        result_file,
        filename=f"{id}.png",
        background=BackgroundTasks(
            [BackgroundTask(utils.cleanup_temp_file, [result_file])]
        ),
    )


@app.post(
    "/cutone/{type}", description="从单个上传图像中生成指定对象的第一个正方形图片"
)
async def cut_image(
    type: gen.GenSquareType,
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
    auth_header: str = Header(None, description="认证头部"),
):
    authenticate(auth_header)

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="文件类型不支持")

    img_path = Path(
        tempfile.mktemp(suffix=".png", dir=Path(__file__).parent.resolve() / "input")
    )
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
            output_dir=Path(__file__).parent / "output",
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


@app.post("/cutall/{type}", description="从单个上传图像中生成指定对象的所有正方形图片")
async def cut_all_images(
    req: Request,
    type: gen.GenSquareType,
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
    auth_header: str = Header(None, description="认证头部"),
):
    authenticate(auth_header)

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="文件类型不支持")

    img_path = Path(
        tempfile.mktemp(suffix=".png", dir=Path(__file__).parent.resolve() / "input")
    )
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
            output_dir=Path(__file__).parent / "output",
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

        img_path = Path(
            tempfile.mktemp(
                suffix=".png", dir=Path(__file__).parent.resolve() / "input"
            )
        )
        with open(img_path, "wb") as f:
            f.write(content)
        avatars = await asyncio.to_thread(
            gen.square,
            type=gen.GenSquareType.HEAD,
            img_path=img_path,
            output_dir=Path(tempfile.mkdtemp(dir="./output")),
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
