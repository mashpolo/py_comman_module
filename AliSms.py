#!/usr/bin/env python
# encoding: utf-8
"""
desc: ali sms module & ali dingding module
author: lu.luo
date:  2017-06-07
"""
import urllib2
import urllib
import json
import requests

from settings import *


class AliyunSms(object):
    """
    params:  dict or str, sms content
    recnum:  str or list, sms receiver
    template_id: sms content template id
    """

    def __init__(self):
        self.host = SmsUrl
        self.path = SmsPath
        self.method = "GET"
        self.app_code = AppCode
        self.signname = "SignName=%s" % SignName

    def send_sms(self, params=None, recnum=None, template_id=None):
        # 判断传入的sms内容是str还是dict，dict需要转化成str后在进行url编码
        if isinstance(params, dict):
            param = urllib.quote(json.dumps(params))
            subject = "ParamString=%s" % param
        elif isinstance(params, str):
            param = urllib.quote(params)
            subject = "ParamString=%s" % param
        else:
            return "ERROR params, please notice!"

        # 判断传入的sms num是个列表还是str，列表需要转成str，用'，'隔开
        if isinstance(recnum, str):
            notice_nums = "RecNum=%s" % recnum
        elif isinstance(recnum, list):
            nums = ",".join(recnum)
            nums = urllib.quote(nums)
            notice_nums = "RecNum=%s" % nums
        else:
            return "ERROR recnums,please notice"

        # 判断是否有模版
        if template_id:
            template = "TemplateCode=%s" % template_id

        query = "&".join([subject, notice_nums, self.signname, template])
        url = self.host + self.path + "?" + query

        request = urllib2.Request(url)
        request.add_header('Authorization', 'APPCODE ' + self.app_code)
        response = urllib2.urlopen(request)
        content = response.read()
        return content


class DingSms(object):
    """
    content: message content
    contact_nums: list, contacts phone nums
    isAtAll: bool, true=at all, false=no
    """

    def __init__(self, DingRobotUrl):
        self.url = DingRobotUrl
        self.session = requests.session()
        self.session.headers.update({"Content-Type": "application/json"})

    def send_text(self, content, contact_nums=None, isAtAll=False):
        data = {"msgtype": "text",
                "text": {
                    "content": content}
                }
        if contact_nums:
            data["at"] = {"atMobiles": contact_nums,
                          "isAtAll": isAtAll
                          }
        r = self.session.post(self.url, data=json.dumps(data))
        result = json.loads(r.content)
        if result["errcode"] != 0:
            status = True
        else:
            status = False
        return status

    def send_alert(self, error_info, contact_nums, isAtAll=False, is_send=False):
        if not is_send:
            content = u"检测到rabbitmq中信息有问题，筛选失败\n"
            content += u"报错信息: {0}".format(error_info)
        else:
            content = u"检测到发送告警失败，请立即查看..."
            content = u"报错信息: {0}".format(error_info)
        data = {"msgtype": "text",
                "text": {
                    "content": content}
                }
        if contact_nums:
            data["at"] = {"atMobiles": contact_nums,
                          "isAtAll": isAtAll
                          }
        r = self.session.post(self.url, data=json.dumps(data))
        result = json.loads(r.content)
        if result["errcode"] != 0:
            status = True
        else:
            status = False
        return status
