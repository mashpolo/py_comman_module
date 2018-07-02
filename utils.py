#!/usr/bin/python
#coding=utf-8

import socket
import smtplib
import multiprocessing

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage


def send_mail(smtp_server, from_addr, to_addr, port,
              username, password, subject, message, message_type="plain",
              image=None, attach=None, logger=None):
    """
    desc: 对标准smtplib发送邮件的作了封装，进行了一些错误处理
    param: <smtp_server> smtp 发送服务器的地址
           <from_addr> 从哪个邮箱发送的
           <to_addr> 发给哪些邮箱，这是个列表
           <port> 邮件端口
           <username> 登陆的邮箱账号，一般跟from_addr是一样的
           <password> 登陆的邮箱密码
           <subject> 邮件主题
           <message> 要发送的内容
           <message_type> 邮件信息类型
           <image> 图片
           <attach> 附件
           <logger> 日志实例
    return: True 发送成功
            False 发送失败
    """
    try:
        smtp = smtplib.SMTP_SSL(smtp_server, port, timeout=10)
        smtp.login(username, password)
    except socket.gaierror:
        if logger:
            logger.error("socket.gaierror: [Errno -2] Name or service not known, "
                         "maybe your network has something wrong")
        return False
    except smtplib.SMTPAuthenticationError:
        if logger:
            logger.error("email authentication error, please check your email name and password")
        return False

    multipart_mail = MIMEMultipart("related")
    multipart_mail["Subject"] = subject.encode("utf-8")
    multipart_mail["From"] = from_addr
    multipart_mail["To"] = ";".join(to_addr)

    message = MIMEText(message, _subtype=message_type, _charset="utf-8")
    multipart_mail.attach(message)

    #构造图片
    if image is not None:
        if logger:
            logger.info("Image: %s -- %s" % (image, multiprocessing.current_process().name))
        fp = open(image, "rb")
        msg_image = MIMEImage(fp.read(), _subtype=image.rsplit(".", 1)[1])
        fp.close()

        msg_image.add_header("Content-ID", "alert_graph")
        multipart_mail.attach(msg_image)

    #构造附件
    if attach is not None:
        pass
    msg = multipart_mail.as_string()
    try:
        smtp.sendmail(from_addr, to_addr, msg)
    except smtplib.SMTPRecipientsRefused as e:
        if logger:
            logger.error("Send mail failure: %s" % e)
        return False
    except smtplib.SMTPServerDisconnected as e:
        if logger:
            logger.error("send mail failure: %s" % e)
        return False

    smtp.close()
    return True
