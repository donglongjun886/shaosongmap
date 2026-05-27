"""ShaosongMap FastAPI 应用入口。"""

from __future__ import annotations

import contextvars
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from shaosongmap.config import Settings, limiter
from shaosongmap.routers.extract import router as extract_router
from shaosongmap.routers.health import router as health_router
from shaosongmap.routers.ocr import router as ocr_router
from shaosongmap.routers.render import router as render_router

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('request_id', default='-')


class _RequestIdFilter(logging.Filter):
    """将 contextvars 中的 request_id 注入每条日志记录。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def _setup_logging(log_level: str, log_format: str) -> None:
    """配置全局日志格式，注入 request_id。"""
    handler = logging.StreamHandler()
    handler.addFilter(_RequestIdFilter())

    if log_format == 'json':
        from pythonjsonlogger.json import JsonFormatter

        handler.setFormatter(
            JsonFormatter(
                fmt='%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s',
                datefmt='%Y-%m-%dT%H:%M:%S',
            )
        )
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt='%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
            )
        )

    logging.root.handlers.clear()
    logging.root.addHandler(handler)
    logging.root.setLevel(getattr(logging, log_level.upper(), logging.INFO))


async def _init_settings():
    """初始化全局配置单例，启动时校验必填项。"""
    from shaosongmap.config import Settings

    try:
        s = Settings()  # type: ignore[call-arg]
    except Exception as e:
        logging.error('配置校验失败: %s', e)
        raise SystemExit(1) from e

    if not s.deepseek_api_key:
        logging.error('配置校验失败: DEEPSEEK_API_KEY 未设置')
        raise SystemExit(1)

    import shaosongmap.config as config_mod

    config_mod.settings = s
    return s


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """应用生命周期：启动时校验配置并预加载 PaddleOCR 模型，关闭时释放资源。"""
    s = await _init_settings()
    _setup_logging(s.log_level, s.log_format)

    logger = logging.getLogger(__name__)
    logger.info('配置校验通过，正在预加载 PaddleOCR 模型...')

    from shaosongmap.ocr import _get_ocr

    _get_ocr()
    _app.state.ocr_ready = True
    logger.info('PaddleOCR 模型预热完成')
    yield
    # --- 关闭阶段 ---
    logger.info('正在关闭应用，释放资源...')
    _app.state.ocr_ready = False
    logger.info('应用已关闭')


app = FastAPI(
    title='ShaosongMap',
    description='让历史小说读者「边读边看地图」——输入战役段落，生成古代地图',
    version='0.1.0',
    lifespan=_lifespan,
)


@app.middleware('http')
async def _request_id_middleware(request: Request, call_next):
    """为每个 HTTP 请求注入唯一标识符，支持上游传入复用。"""
    request_id = request.headers.get('X-Request-ID', uuid.uuid4().hex[:12])
    request_id_var.set(request_id)
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers['X-Request-ID'] = request_id
    return response


_CSP_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
    "img-src 'self' data: blob: https://*.tile.openstreetmap.org https://tile.openstreetmap.org; "
    "connect-src 'self' https://unpkg.com; "
    "font-src 'self' https://cdn.jsdelivr.net; "
    "worker-src 'self' blob:"
)


@app.middleware('http')
async def _security_headers_middleware(request: Request, call_next):
    """为每个响应添加安全响应头（CSP 等）。"""
    response = await call_next(request)
    response.headers['Content-Security-Policy'] = _CSP_POLICY
    return response


# 速率限制器注册到 app.state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]


@app.exception_handler(HTTPException)
async def _http_exception_handler(_request: Request, exc: HTTPException):
    """自定义 HTTP 异常处理器：若 detail 为统一错误格式则直接返回，否则包装为 detail。"""
    if isinstance(exc.detail, dict) and 'error' in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={'detail': exc.detail})


# CORS 中间件：直接在模块加载时读取配置（pydantic-settings 已支持 .env）
_cors_origins = Settings().cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_origins != ['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(extract_router)
app.include_router(health_router)
app.include_router(ocr_router)
app.include_router(render_router)


# 挂载静态文件（必须在所有路由之后）
static_dir = Path(__file__).parent / 'static'
if static_dir.exists():
    app.mount('/', StaticFiles(directory=str(static_dir), html=True), name='static')
