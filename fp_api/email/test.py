import imaplib
import email
from email.header import decode_header

email_account = "821290968@qq.com"
auth_code = "otfizosgmvxhbefd"

imap = imaplib.IMAP4_SSL("imap.qq.com")
imap.login(email_account, auth_code)
imap.select("INBOX")

# 只检查最新的 5 封邮件
_, data = imap.search(None, "ALL")
all_ids = data[0].split()

print(f"邮箱总邮件数: {len(all_ids)}")
print(f"\n最新的 5 封邮件详细信息:")
print("=" * 80)

recent_ids = all_ids[-5:]
for idx, m_id in enumerate(recent_ids, 1):
    _, mdata = imap.fetch(m_id, "(RFC822)")
    msg = email.message_from_bytes(mdata[0][1])
    
    print(f"\n【邮件 {idx}】")
    print(f"  ID: {m_id.decode()}")
    print(f"  From: {msg.get('From', 'N/A')}")
    print(f"  Subject: {msg.get('Subject', 'N/A')[:60]}")
    print(f"  Date: {msg.get('Date', 'N/A')}")
    print(f"  Size: {len(mdata[0][1])} bytes")

# 最早的 5 封邮件
print("\n" + "=" * 80)
print(f"\n最早的 5 封邮件详细信息:")
print("=" * 80)

earliest_ids = all_ids[:5]
for idx, m_id in enumerate(earliest_ids, 1):
    _, mdata = imap.fetch(m_id, "(RFC822)")
    msg = email.message_from_bytes(mdata[0][1])
    
    print(f"\n【邮件 {idx}】")
    print(f"  ID: {m_id.decode()}")
    print(f"  From: {msg.get('From', 'N/A')}")
    print(f"  Subject: {msg.get('Subject', 'N/A')[:60]}")
    print(f"  Date: {msg.get('Date', 'N/A')}")

imap.logout()