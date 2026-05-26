"""OCR 相关路由：单张/批量截图识别。"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from shaosongmap.ocr import merge_texts, ocr_main
from shaosongmap.schemas import OcrResponse
from shaosongmap.utils import sse_event

logger = logging.getLogger('shaosongmap')

router = APIRouter()

_ALLOWED_IMAGE_TYPES = {'image/png', 'image/jpeg'}
_MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
_MAX_BATCH_SIZE = 10


@router.post('/api/ocr', response_model=OcrResponse)
async def ocr_image(file: UploadFile = File(...)):
    """接收截图上传，OCR 识别后返回清洗文本。

    支持 PNG 和 JPEG 格式，最大 10MB。
    返回的文本可直接用于 /api/extract。
    """
    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail='仅支持 PNG 和 JPEG 格式',
        )

    image_bytes = await file.read()
    if len(image_bytes) > _MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f'图片大小不能超过 {_MAX_IMAGE_SIZE // 1024 // 1024}MB',
        )

    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail='图片不能为空')

    try:
        t0 = time.perf_counter()
        text, raw_lines = ocr_main(image_bytes)
        elapsed = (time.perf_counter() - t0) * 1000
        logger.info('OCR完成: %d行 → %d字符, 耗时 %.0fms', raw_lines, len(text), elapsed)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    return OcrResponse(text=text, raw_lines=raw_lines, elapsed_ms=round(elapsed))


@router.post('/api/ocr/batch')
async def ocr_batch(files: list[UploadFile] = File(...)):
    """批量截图 OCR：接收多张截图，依次识别后去重拼接。

    通过 SSE 流式返回每张图的处理进度，最终返回拼接后的完整文本。
    最多支持 10 张截图，单张失败则整体中止并指明失败序号。
    """
    if len(files) > _MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f'每次最多上传 {_MAX_BATCH_SIZE} 张截图',
        )
    if len(files) == 0:
        raise HTTPException(status_code=400, detail='请至少上传一张截图')

    # 先读取所有文件内容，避免 StreamingResponse 中文件被提前关闭
    file_data: list[tuple[str, bytes]] = []
    for i, file in enumerate(files):
        label = f'第 {i + 1} 张'
        if file.content_type not in _ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f'{label}截图格式不支持，仅支持 PNG 和 JPEG 格式',
            )
        image_bytes = await file.read()
        if len(image_bytes) > _MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f'{label}截图大小超过 {_MAX_IMAGE_SIZE // 1024 // 1024}MB 限制',
            )
        if len(image_bytes) == 0:
            raise HTTPException(
                status_code=400,
                detail=f'{label}截图不能为空',
            )
        file_data.append((label, image_bytes))

    async def event_stream():
        texts: list[str] = []
        total = len(file_data)
        t_pipeline_start = time.perf_counter()

        for label, img_bytes in file_data:
            t0 = time.perf_counter()
            try:
                text, _raw_lines = ocr_main(img_bytes)
            except ValueError as e:
                yield sse_event(
                    'error',
                    {
                        'message': f'{label}截图识别失败: {e}',
                    },
                )
                return

            elapsed = (time.perf_counter() - t0) * 1000
            logger.info('批量OCR %s: %d字符, 耗时 %.0fms', label, len(text), elapsed)
            texts.append(text)
            yield sse_event(
                'progress',
                {
                    'current': len(texts),
                    'total': total,
                    'char_count': len(text),
                    'elapsed_ms': round(elapsed),
                },
            )

        # 去重拼接
        original_chars = sum(len(t) for t in texts)
        t_merge_start = time.perf_counter()
        merged_text, removed_dup = merge_texts(texts)
        merge_elapsed = (time.perf_counter() - t_merge_start) * 1000
        logger.info(
            '批量OCR 去重拼接: %d字符 → %d字符 (去重%d), 耗时 %.0fms',
            original_chars,
            len(merged_text),
            removed_dup,
            merge_elapsed,
        )
        yield sse_event(
            'merge',
            {
                'original_chars': original_chars,
                'merged_chars': len(merged_text),
                'removed_dup': removed_dup,
                'elapsed_ms': round(merge_elapsed),
            },
        )

        total_elapsed = (time.perf_counter() - t_pipeline_start) * 1000
        logger.info(
            '批量OCR 全部完成: %d张截图 → %d字符, 总耗时 %.0fms',
            total,
            len(merged_text),
            total_elapsed,
        )
        yield sse_event('complete', {'text': merged_text, 'total_elapsed_ms': round(total_elapsed)})

    return StreamingResponse(
        event_stream(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        },
    )
