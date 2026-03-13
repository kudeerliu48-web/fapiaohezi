@echo off
echo 🗑️  正在清空被占用的文件...
timeout /t 3 /nobreak >nul
del /f /q "f:\web\AI_DEMO\fapiaohezi\fp_api\files\110867151967257590\database\110867151967257590.db"
rmdir /s /q "f:\web\AI_DEMO\fapiaohezi\fp_api\files\110867151967257590"
echo ✅ 清理完成！
pause
