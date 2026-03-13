from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import traceback

try:
    # 当以包方式运行（推荐：uvicorn fp_api_new.main:app）时
    from fp_api_new.user import router as user_router  # type: ignore
    from fp_api_new.invoices import router as invoices_router  # type: ignore
    from fp_api_new.admin import router as admin_router  # type: ignore
except Exception:
    # 当在 fp_api_new 目录下直接运行 python main.py 时
    from user import router as user_router
    from invoices import router as invoices_router
    from admin import router as admin_router
from config import config

app = FastAPI(
    title="发票识别系统 API",
    description="发票识别与管理系统后端服务",
    version="1.0.0"
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print("=" * 60)
    print(f"[GLOBAL ERROR] {exc}")
    print(f"[TRACEBACK] {traceback.format_exc()}")
    print("=" * 60)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}"}
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router)
app.include_router(invoices_router)
app.include_router(admin_router)

if os.path.exists("files"):
    app.mount("/files", StaticFiles(directory="files"), name="files")


@app.get("/")
async def root():
    return {
        "message": "发票识别系统 API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "invoice-recognition-api"
    }


@app.get("/debug/routes")
async def debug_routes():
    out = []
    for r in app.router.routes:
        path = getattr(r, "path", None)
        methods = sorted(list(getattr(r, "methods", []) or []))
        name = getattr(r, "name", None)
        if path:
            out.append({"path": path, "methods": methods, "name": name})
    out.sort(key=lambda x: (x["path"], ",".join(x["methods"])))
    return {"count": len(out), "routes": out}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
