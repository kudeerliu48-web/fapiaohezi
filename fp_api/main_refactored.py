from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from routes import api_router
from database import DatabaseManager
from utils import hash_password, generate_uuid, format_datetime

# 创建FastAPI应用
app = FastAPI(
    title="发票盒子API",
    description="智能发票管理系统后端服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务
if not os.path.exists("files"):
    os.makedirs("files")
app.mount("/files", StaticFiles(directory="files"), name="files")

# 注册路由
app.include_router(api_router)

# 初始化
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    # 初始化主数据库
    db = DatabaseManager()
    
    # 创建测试用户
    create_test_user()
    
    print("🚀 发票盒子API服务启动成功")
    print("📚 API文档地址: http://localhost:8000/docs")
    print("🔧 ReDoc文档地址: http://localhost:8000/redoc")

def create_test_user():
    """创建测试用户"""
    from database import DatabaseManager
    from utils import create_user_folders, init_user_database
    from config import config
    
    db = DatabaseManager()
    
    # 检查是否已存在测试用户
    if db.user_exists(username="testuser"):
        print("✅ 测试用户已存在")
        return
    
    # 创建测试用户
    test_user_data = {
        "username": "testuser",
        "password": hash_password("test123456"),
        "email": "test@example.com",
        "company": "测试科技有限公司",
        "phone": "13800138000",
        "status": 1
    }
    
    try:
        user_id = db.create_user(test_user_data)
        
        # 创建用户文件夹和数据库
        create_user_folders(user_id)
        user_db_path = config.get_user_db_path(user_id)
        init_user_database(user_id, user_db_path)
        
        print(f"✅ 测试用户创建成功 - ID: {user_id}")
        print("📋 测试账号信息:")
        print("   用户名: testuser")
        print("   密码: test123456")
        print("   邮箱: test@example.com")
        
    except Exception as e:
        print(f"❌ 创建测试用户失败: {e}")

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "发票盒子API服务",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main_refactored:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
