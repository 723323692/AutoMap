# -*- coding:utf-8 -*-
"""
邮件发送模块
"""

__author__ = "723323692"
__version__ = '1.0'

import logging
import os
import smtplib
import time
from email.header import Header
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class EmailSender:
    """邮件发送器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化邮件发送配置
        
        Args:
            config: 配置字典，包含 sender, password, smtp_server, smtp_port
        """
        self.sender: str = config.get('sender', '')
        self.password: str = config.get('password', '')
        self.smtp_server: str = config.get('smtp_server', 'smtp.qq.com')
        self.smtp_port: int = config.get('smtp_port', 465)
        
        if not self.sender or not self.password:
            logger.warning("邮件配置不完整，发送功能可能无法正常工作")

    def _build_email_with_images(
        self,
        subject: str,
        content: str,
        receiver: str,
        image_paths: List[str]
    ) -> MIMEMultipart:
        """构造带图片的邮件内容"""
        message = MIMEMultipart('related')
        message['From'] = Header(self.sender)
        message['To'] = Header(receiver)
        message['Subject'] = Header(subject)

        alternative = MIMEMultipart('alternative')
        message.attach(alternative)

        text_part = MIMEText(content, 'plain', 'utf-8')
        alternative.attach(text_part)

        html_content = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
                .text-content {{ white-space: pre-wrap; margin-bottom: 20px; }}
                img {{ max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; margin: 10px 0; }}
                .image-container {{ text-align: center; }}
            </style>
        </head>
        <body>
            <div class="text-content">{content}</div>
        """

        if image_paths:
            for i in range(len(image_paths)):
                html_content += f'''
                <div class="image-container">
                    <img src="cid:image{i}" alt="图片{i + 1}">
                </div>
                '''

        html_content += "</body></html>"

        html_part = MIMEText(html_content, 'html', 'utf-8')
        alternative.attach(html_part)

        if image_paths:
            for i, image_path in enumerate(image_paths):
                try:
                    if not os.path.exists(image_path):
                        logger.warning(f"图片文件不存在: {image_path}")
                        continue

                    with open(image_path, 'rb') as file:
                        image_data = file.read()

                    ext = os.path.splitext(image_path)[1].lower()
                    subtype_map = {'.jpg': 'jpeg', '.jpeg': 'jpeg', '.png': 'png', '.gif': 'gif'}
                    subtype = subtype_map.get(ext)
                    
                    if subtype:
                        image = MIMEImage(image_data, subtype)
                    else:
                        image = MIMEImage(image_data)

                    image.add_header('Content-ID', f'<image{i}>')
                    image.add_header('Content-Disposition', 'inline', filename=os.path.basename(image_path))
                    message.attach(image)
                    logger.debug(f"已添加图片: {os.path.basename(image_path)}")

                except IOError as e:
                    logger.error(f"读取图片失败 {image_path}: {e}")
                except Exception as e:
                    logger.error(f"处理图片失败 {image_path}: {e}")

        return message

    def _build_email(self, subject: str, content: str, receiver: str) -> MIMEText:
        """构造普通文本邮件内容"""
        message = MIMEText(content, 'plain', 'utf-8')
        message['From'] = Header(self.sender)
        message['To'] = Header(receiver)
        message['Subject'] = Header(subject)
        return message

    def _send_with_retry(
        self,
        message: MIMEMultipart,
        receiver: str,
        subject: str,
        retry_count: int = 2
    ) -> bool:
        """带重试的邮件发送"""
        if not self.sender or not self.password:
            logger.error("邮件配置不完整，无法发送")
            return False
            
        for attempt in range(retry_count + 1):
            smtp_obj: Optional[smtplib.SMTP_SSL] = None
            try:
                smtp_obj = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=30)
                smtp_obj.ehlo()
                smtp_obj.login(self.sender, self.password)
                smtp_obj.sendmail(self.sender, [receiver], message.as_string())
                logger.info(f"邮件《{subject}》发送给 {receiver} 成功")
                return True

            except smtplib.SMTPServerDisconnected as e:
                logger.warning(f"第{attempt + 1}次尝试失败: 服务器断开连接 - {e}")
            except smtplib.SMTPAuthenticationError as e:
                logger.error(f"认证失败: {e}")
                return False
            except smtplib.SMTPResponseException as e:
                logger.warning(f"第{attempt + 1}次尝试失败: SMTP错误 {e.smtp_code} - {e.smtp_error}")
                if e.smtp_code in [535, 550]:
                    return False
            except Exception as e:
                logger.warning(f"第{attempt + 1}次尝试失败: {e}")
            finally:
                if smtp_obj:
                    try:
                        smtp_obj.quit()
                    except Exception:
                        try:
                            smtp_obj.close()
                        except Exception:
                            pass

            if attempt < retry_count:
                wait_time = (attempt + 1) * 2
                logger.info(f"等待{wait_time}秒后重试...")
                time.sleep(wait_time)

        logger.error(f"邮件《{subject}》发送给 {receiver} 失败，已重试{retry_count}次")
        return False

    def send_email_with_images(
        self,
        subject: str,
        content: str,
        receiver: str,
        image_paths: Optional[List[str]] = None,
        retry_count: int = 2
    ) -> bool:
        """
        发送带图片的邮件
        
        Args:
            subject: 邮件标题
            content: 正文内容
            receiver: 收件人
            image_paths: 图片路径列表
            retry_count: 重试次数
            
        Returns:
            是否发送成功
        """
        if not image_paths:
            logger.info("没有提供图片路径，将发送普通文本邮件")
            return self.send_email(subject, content, receiver, retry_count)

        message = self._build_email_with_images(subject, content, receiver, image_paths)
        return self._send_with_retry(message, receiver, subject, retry_count)

    def send_email(
        self,
        subject: str,
        content: str,
        receiver: str,
        retry_count: int = 2
    ) -> bool:
        """
        发送普通文本邮件
        
        Args:
            subject: 邮件标题
            content: 正文内容
            receiver: 收件人
            retry_count: 重试次数
            
        Returns:
            是否发送成功
        """
        message = self._build_email(subject, content, receiver)
        return self._send_with_retry(message, receiver, subject, retry_count)
