"""ShaosongMap FastAPI 应用入口。"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from shaosongmap.ocr import _get_ocr
from shaosongmap.routers.extract import router as extract_router
from shaosongmap.routers.ocr import router as ocr_router
from shaosongmap.routers.render import router as render_router

logger = logging.getLogger('shaosongmap')


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """应用生命周期：启动时预加载 PaddleOCR 模型。"""
    logger.info('正在预加载 PaddleOCR 模型...')
    _get_ocr()
    logger.info('PaddleOCR 模型预热完成')
    yield


app = FastAPI(
    title='ShaosongMap',
    description='让历史小说读者「边读边看地图」——输入战役段落，生成古代地图',
    version='0.1.0',
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(extract_router)
app.include_router(ocr_router)
app.include_router(render_router)

# 挂载静态文件（必须在所有路由之后）
static_dir = Path(__file__).parent / 'static'
if static_dir.exists():
    app.mount('/', StaticFiles(directory=str(static_dir), html=True), name='static')
