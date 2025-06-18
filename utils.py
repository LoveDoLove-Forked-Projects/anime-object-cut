from pathlib import Path
from loguru import logger


def cleanup_temp_file(files: list[Path]) -> None:
    """清理临时文件"""
    for file_path in files:
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"已删除临时文件: {file_path}")
        except Exception as e:
            logger.error(f"删除临时文件失败: {str(e)}")
