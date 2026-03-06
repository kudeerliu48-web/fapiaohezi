# 解析 AI 返回的发票文本为结构化一行（用于表格/Excel）
import json
import re

# 表格列顺序
INVOICE_COLUMNS = [
    "发票号码", "开票日期", "销售方名称", "购买方名称",
    "合计金额", "税额", "价税合计", "原始内容"
]

def parse_invoice_result_to_row(content):
    """
    将 parse_invoice_with_qwen 返回的字符串解析为一行字典。
    支持纯 JSON、Markdown 代码块中的 JSON、或键值对文本。
    """
    def format_date(date_str):
        if not date_str: return ""
        # 提取数字
        nums = re.findall(r'\d+', date_str)
        if len(nums) >= 3:
            year = nums[0]
            month = nums[1].zfill(2)
            day = nums[2].zfill(2)
            return f"{year}-{month}-{day}"
        return date_str

# 在 _dict_to_row 或解析逻辑中调用
# row["开票日期"] = format_date(obj.get("开票日期"))
    if not content or not isinstance(content, str):
        print("[发票解析] 解析器: 无内容或非字符串")
        return _empty_row("无内容")
    content = content.strip()
    if content.startswith("❌"):
        print("[发票解析] 解析器: 内容为错误信息", content[:100])
        return _empty_row(content)

    # 1. 尝试直接 JSON
    try:
        obj = json.loads(content)
        if isinstance(obj, dict):
            print("[发票解析] 解析器: 使用直接 JSON")
            return _dict_to_row(obj, content)
    except json.JSONDecodeError:
        pass

    # 2. 尝试从 ```json ... ``` 中提取
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
    if m:
        try:
            obj = json.loads(m.group(1).strip())
            if isinstance(obj, dict):
                print("[发票解析] 解析器: 使用代码块内 JSON")
                return _dict_to_row(obj, content)
        except json.JSONDecodeError:
            pass

    # 3. 键值对解析（"发票号码":"xxx" 或 发票号码：xxx）
    print("[发票解析] 解析器: 使用键值对正则, 内容长度", len(content), "预览", content[:150])
    row = {k: "" for k in INVOICE_COLUMNS}
    row["原始内容"] = content[:500] if len(content) > 500 else content
    for key in INVOICE_COLUMNS:
        if key == "原始内容":
            continue
        # 匹配 "key":"value" 或 key：value
        for pat in [
            rf'["\']?{re.escape(key)}["\']?\s*[：:]\s*["\']?([^"\',\n]+)["\']?',
            rf'"{re.escape(key)}"\s*:\s*"([^"]*)"',
        ]:
            m = re.search(pat, content)
            if m:
                row[key] = m.group(1).strip().strip('"\'')
                break
    return row

def _dict_to_row(obj, raw_content):
    row = {k: "" for k in INVOICE_COLUMNS}
    for k in INVOICE_COLUMNS:
        if k == "原始内容":
            row[k] = raw_content[:500] if len(raw_content) > 500 else raw_content
            continue
        v = obj.get(k)
        if v is not None:
            row[k] = str(v).strip()
    return row

def _empty_row(message):
    row = {k: "" for k in INVOICE_COLUMNS}
    row["原始内容"] = message
    return row
