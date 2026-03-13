import os
import time
import fitz  # PyMuPDF
import dashscope
from dashscope import MultiModalConversation

# 配置 API KEY
QWEN_API_KEY = "sk-cb4bc9e9a80c42bc8c7886fee8f28f8f"
dashscope.api_key = QWEN_API_KEY

def convert_pdf_to_jpg(pdf_path):
    """
    将 PDF 第一页转换为临时 JPG 文件。
    使用 1.2 倍分辨率，在保证可识别的前提下减小体积、加快上传与识别速度。
    """
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)  # 获取第一页
        # 1.2 倍分辨率，兼顾清晰度与速度（原 2 倍过大且慢）
        pix = page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2))
        temp_jpg = pdf_path.replace(".pdf", "_convert_tmp.jpg")
        pix.save(temp_jpg)
        doc.close()
        return temp_jpg
    except Exception as e:
        print(f"   ❌ PDF 转换失败: {e}")
        return None

def parse_invoice_with_qwen(file_path, save_preview_to=None):
    """
    调用 Qwen-VL-Plus 解析发票，内部自动处理 PDF 转换。
    save_preview_to: 若提供路径，会将用于识别的图片复制到该路径，供前端预览大图。
    """
    is_pdf = file_path.lower().endswith(".pdf")
    target_path = file_path
    temp_file = None

    # 1. 如果是 PDF，先转成图片
    if is_pdf:
        print(f"   🔄 检测到 PDF，正在转换为高清图片...")
        temp_file = convert_pdf_to_jpg(file_path)
        if not temp_file:
            return "❌ 转换失败，无法解析", None
        target_path = temp_file

    # 保存预览图（PDF 转的图或原图）
    if save_preview_to:
        try:
            import shutil
            shutil.copy2(target_path, save_preview_to)
        except Exception as e:
            print(f"[发票解析] 保存预览图失败: {e}")

    # 2. 构建 API 调用
    local_file_url = f"file://{os.path.abspath(target_path)}"
    print(f"[发票解析] 调用 Qwen 图片路径: {local_file_url}")
    prompt = (
        "你是一个专业的财务助手。请从图片中提取发票信息并以 JSON 格式返回，"
        "必须包含：发票号码、开票日期、销售方名称、购买方名称、合计金额、税额、价税合计。"
    )

    messages = [
        {
            "role": "user",
            "content": [
                {"image": local_file_url},
                {"text": prompt}
            ]
        }
    ]

    try:
        response = MultiModalConversation.call(model='qwen-vl-plus', messages=messages)

        if response.status_code == 200:
            raw = response.output.choices[0].message.content
            # API 可能返回字符串或 list[dict]（如 [{'text': '...'}]），统一转为字符串
            if isinstance(raw, str):
                content = raw
            elif isinstance(raw, list) and raw:
                parts = []
                for item in raw:
                    if isinstance(item, dict) and item.get("text"):
                        parts.append(item["text"])
                    elif isinstance(item, str):
                        parts.append(item)
                content = "\n".join(parts) if parts else str(raw)
            else:
                content = str(raw) if raw is not None else ""
            print(f"[发票解析] Qwen 返回 status=200 内容长度: {len(content)} 预览: {(content[:200] + '…') if len(content) > 200 else content}")
            return content, save_preview_to if save_preview_to and os.path.exists(save_preview_to) else None
        else:
            msg = f"❌ API 报错: {response.message}"
            print(f"[发票解析] Qwen 非 200: {response.status_code} {msg}")
            return msg, None
    except Exception as e:
        print(f"[发票解析] Qwen 调用异常: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ 系统异常: {str(e)}", None
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass