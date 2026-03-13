import imaplib
import email
import os
import re
import time
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta

# Selenium 相关库
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def _safe_decode(bs, encoding):
    """极简解码邮件头"""
    if not isinstance(bs, bytes):
        return str(bs) if bs else ""
    try:
        return bs.decode(encoding or 'utf-8', errors='ignore')
    except (LookupError, TypeError):
        return bs.decode('latin-1', errors='ignore')

def fetch_invoice_attachments_from_mail(email_account, auth_code, months=3, save_dir="downloads"):
    """
    仅从收件箱拉取主题含「发票」的邮件中的附件（PDF/OFD/JPG/PNG），保存到 save_dir，返回所有附件路径列表。
    不执行 Selenium 网页链接下载，适合服务端无头环境。
    """
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    paths = []
    try:
        imap_server = imaplib.IMAP4_SSL("imap.qq.com", 993)
        imap_server.login(email_account, auth_code)
        imap_server.select("INBOX", readonly=True)
        since_date = (datetime.now() - timedelta(days=months * 30)).strftime("%d-%b-%Y")
        status, data = imap_server.search(None, f'(SINCE {since_date})')
        if status != 'OK' or not data[0]:
            return paths
        all_seqs = data[0].split()
        all_seqs.reverse()
        for seq in all_seqs:
            seq_id = seq.decode()
            _, h_data = imap_server.fetch(seq, '(BODY[HEADER.FIELDS (SUBJECT)])')
            msg_header = email.message_from_bytes(h_data[0][1])
            subj_parts = decode_header(msg_header.get("Subject", ""))
            subject = "".join([_safe_decode(p, e) for p, e in subj_parts])
            if "发票" not in subject:
                continue
            _, full_data = imap_server.fetch(seq, '(RFC822)')
            msg = email.message_from_bytes(full_data[0][1])
            for part in msg.walk():
                filename = part.get_filename()
                if not filename:
                    continue
                fname = "".join([_safe_decode(p, e) for p, e in decode_header(filename)])
                if fname.lower().endswith(('.pdf', '.ofd', '.jpg', '.jpeg', '.png')):
                    filepath = os.path.join(save_dir, f"{seq_id}_{fname}")
                    with open(filepath, "wb") as f:
                        f.write(part.get_payload(decode=True))
                    paths.append(filepath)
        imap_server.logout()
    except Exception as e:
        print(f"❌ 拉取邮件附件出错: {e}")
    return paths

def selenium_download_invoice(url, save_dir):
    """
    通用 Selenium 下载器：支持诺诺网(jss.com.cn)和百望云(fapiao.com)
    """
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    chrome_options = Options()
    download_path = os.path.abspath(save_dir)
    
    # 浏览器下载偏好设置
    prefs = {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True  # PDF 不预览直接下载
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # 常用请求头伪装
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    # chrome_options.add_argument("--headless") # 稳定后可开启无头模式

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        print(f"   🌐 浏览器正在访问: {url}")
        driver.get(url)
        # 给网页充足的加载和自动下载时间
        time.sleep(10) 
        
        # 判断是否已经触发了自动下载（针对百望云等点击链接直接下 JPG/PDF 的情况）
        # 如果页面没有复杂的按钮且已经下载，可直接跳过
        
        # 定义可能的下载按钮 XPath
        if "jss.com.cn" in url:
            # 诺诺网常用按钮
            xpath = "//a[contains(text(), 'PDF')] | //button[contains(., 'PDF')] | //*[contains(text(), '下载PDF')]"
        elif "fapiao.com" in url:
            # 百望云常用按钮
            xpath = "//button[contains(., '下载')] | //a[contains(@class, 'download')] | //*[contains(text(), '保存')] | //*[contains(text(), '下载')]"
        else:
            xpath = "//*[contains(text(), '下载')] | //*[contains(text(), 'PDF')]"

        # 尝试寻找并点击按钮（如果上述自动下载未触发）
        try:
            download_btn = driver.find_element(By.XPATH, xpath)
            print(f"   🖱️ 识别到下载按钮，尝试点击...")
            driver.execute_script("arguments[0].click();", download_btn)
            time.sleep(5) # 等待下载
        except:
            print("   ℹ️ 未发现显式下载按钮，可能已触发自动下载或页面结构不同。")

        return True
    except Exception as e:
        print(f"   ❌ 自动化下载异常: {str(e)}")
        return False
    finally:
        driver.quit()

def download_invoices_from_mail(email_account, auth_code, months=3, save_dir="downloads"):
    """
    解析邮件，区分附件提取与网页链接下载
    """
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    results = []
    try:
        imap_server = imaplib.IMAP4_SSL("imap.qq.com", 993)
        imap_server.login(email_account, auth_code)
        imap_server.select("INBOX", readonly=True)

        since_date = (datetime.now() - timedelta(days=months*30)).strftime("%d-%b-%Y")
        status, data = imap_server.search(None, f'(SINCE {since_date})')
        
        if status != 'OK' or not data[0]:
            return []

        all_seqs = data[0].split()
        all_seqs.reverse()

        for seq in all_seqs:
            seq_id = seq.decode()
            _, h_data = imap_server.fetch(seq, '(BODY[HEADER.FIELDS (SUBJECT DATE)])')
            msg_header = email.message_from_bytes(h_data[0][1])
            
            subj_parts = decode_header(msg_header.get("Subject", ""))
            subject = "".join([_safe_decode(p, e) for p, e in subj_parts])

            if "发票" not in subject:
                continue

            print(f"\n📂 处理邮件: {subject}")
            _, full_data = imap_server.fetch(seq, '(RFC822)')
            msg = email.message_from_bytes(full_data[0][1])
            
            mail_info = {"subject": subject, "attachments": [], "links": []}

            for part in msg.walk():
                content_type = part.get_content_type()
                filename = part.get_filename()

                # 情况 A: 直接附件提取
                if filename:
                    fname = "".join([_safe_decode(p, e) for p, e in decode_header(filename)])
                    if fname.lower().endswith(('.pdf', '.ofd', '.xml', '.jpg', '.png')):
                        filepath = os.path.join(save_dir, f"{seq_id}_{fname}")
                        with open(filepath, "wb") as f:
                            f.write(part.get_payload(decode=True))
                        mail_info["attachments"].append(filepath)
                        print(f"   📎 已提取附件: {fname}")

                # 情况 B: 网页链接识别 (支持诺诺网、百望云等)
                elif content_type == "text/html":
                    html = _safe_decode(part.get_payload(decode=True), part.get_content_charset())
                    links = re.findall(r'href=[\'"]?(https?://[^\'"\s>]+(?:nnfp|jss|fapiao|invoice|pdf|download)[^\'"\s>]*)[\'"]?', html, re.I)
                    
                    for link in list(set(links)):
                        # 只要匹配到发票平台关键词，统一由 Selenium 托管
                        if any(domain in link for domain in ["jss.com.cn", "fapiao.com", "nnfp"]):
                            print(f"   🌐 发现发票平台链接，启动自动化下载...")
                            if selenium_download_invoice(link, save_dir):
                                mail_info["attachments"].append(f"网页下载成功 (检查 {save_dir})")
                            else:
                                mail_info["links"].append(link)
                        else:
                            mail_info["links"].append(link)

            results.append(mail_info)
            
        imap_server.logout()
        return results
    except Exception as e:
        print(f"❌ 运行出错: {e}")
        return []