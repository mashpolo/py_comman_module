import time
from datetime import datetime
import requests
import json
from flask import current_app

from app import logger
from app.exceptions.exceptions import FeishuException


OPER_DICT = {
    'PENDING': '审批中',
    'APPROVED': '通过',
    'REJECTED': '拒绝',
    'CANCELED': '撤回',
    'DELETED': '删除'
}


class FeiShu:
    def __init__(self):
        self.__app_id = current_app.config["FEISHU_APP_ID"]
        self.__app_secret = current_app.config["FEISHU_APP_SECRET"]
        self.__opes_url = current_app.config["FEISHU_OPEN_URL"]
        self.__host_url = current_app.config["FEISHU_HOST_URL"]
        self.headers = self.__init_header()

    def _get_tenant_access_token(self):
        """认证接口"""
        try:
            response = requests.post(self.__opes_url + '/open-apis/auth/v3/app_access_token/internal/',
                                     data={'app_id': self.__app_id, 'app_secret': self.__app_secret})
            app_access_token = json.loads(response.text)['app_access_token']
            return app_access_token
        except Exception as e:
            logger.error("Feishu get tenant_access_token fail!")
            raise FeishuException(e)

    def __init_header(self):
        """header构造方法"""
        app_access_token = self._get_tenant_access_token()
        headers = {
            'content-type': 'application/json',
            'Authorization': 'Bearer ' + app_access_token
        }
        return headers

    def _post(self, url, data):
        """封装底层post请求"""
        data_to_send = json.dumps(data).encode("utf-8")
        try:
            response = None
            for x in range(3):
                try:
                    response = requests.post(url, data=data_to_send, headers=self.headers, timeout=5)
                except Exception as e:
                    time.sleep(1)
                    if x == 2:
                        raise e
                else:
                    break
            logger.info('Feishu post response. url={},data={},response={}'.format(url, data, response.text))
            return json.loads(response.text)
        except requests.exceptions.Timeout:
            logger.error("Feishu post timeout! url={0} data={1}".format(url, data))
            raise FeishuException('飞书接口post请求超时，请重试')
        except Exception as e:
            logger.error("Feishu post msg fail! url={0} data={1} error by {2}".format(url, data, e))
            raise FeishuException(e)

    def _get(self, url, data=None):
        """封装底层get请求"""
        try:
            response = None
            for x in range(3):
                try:
                    response = requests.get(url, params=data, headers=self.headers, timeout=5)
                except Exception as e:
                    time.sleep(1)
                    if x == 2:
                        raise e
                else:
                    break
            logger.info('Feishu get response. url={},data={},response={}'.format(url, data, response.text))
            return json.loads(response.text)
        except requests.exceptions.Timeout:
            logger.error("Feishu get timeout! url={0} data={1}".format(url, data))
            raise FeishuException('飞书接口get请求超时，请重试')
        except Exception as e:
            logger.error("Feishu get msg fail! url={0} data={1} error by {2}".format(url, data, e))
            raise FeishuException(e)

    def _send_msg(self, data):
        """消息发送内部使用"""
        result = self._post(self.__opes_url + '/open-apis/message/v4/send/', data=data)
        return result

    def send_user_msg(self, user_code, content, type='text'):
        """
        给用户发送消息
        :param user_code: company id ，前提是飞书必须跟邮箱绑定在一起，是否绑定可以去查看飞书的个人信息简介
        :param content: 发送消息内容
        :param type: 发送消息的类型，text，是纯文本消息（https://open.feishu.cn/document/ukTMukTMukTM/uUjNz4SN2MjL1YzM），
                                 card，是卡片消息。（https://open.feishu.cn/document/ukTMukTMukTM/uYTNwUjL2UDM14iN1ATN）
        :return:
        """
        try:
            result = {'code': -1}
            if type == 'text':
                result = self._send_msg(data={
                    'email': user_code + "@company.com",
                    'msg_type': 'text',
                    "content": {
                        "text": content
                    }
                })
            elif type == 'card':
                result = self._send_msg(data={
                    'email': user_code + "@company.com",
                    'msg_type': 'interactive',
                    'card': content
                })
            if result['code'] != 0:
                logger.error("Send user msg fail! result={0}".format(result))
                raise FeishuException(result)
        except Exception as e:
            raise FeishuException(e)

    def send_user_msg_many(self, open_ids, content, type='text'):
        """
        给多个用户发送消息，一次性只能发送200个人，所以下面做了循环发送
        :param open_ids: 用户的飞书唯一标识列表，[,,,,]
        :param content: 发送消息内容
        :param type: 发送消息的类型，text，是纯文本消息（https://open.feishu.cn/document/ukTMukTMukTM/uUjNz4SN2MjL1YzM），
                                 card，是卡片消息。（https://open.feishu.cn/document/ukTMukTMukTM/uYTNwUjL2UDM14iN1ATN）
        :return:
        """
        try:
            for i in range(0, len(open_ids), 199):
                result = {'code': -1}
                if type == 'text':
                    result = self._post(self.__opes_url + '/open-apis/message/v4/batch_send/', data={
                        'open_ids': open_ids[i:i + 199],
                        'msg_type': 'text',
                        "content": {
                            "text": content
                        }
                    })
                elif type == 'card':
                    result = self._post(self.__opes_url + '/open-apis/message/v4/batch_send/', data={
                        'open_ids': open_ids[i:i + 199],
                        'msg_type': 'interactive',
                        'card': content
                    })
                if result['code'] != 0:
                    logger.error("Send user msg many fail! result={0}".format(result))
                    raise FeishuException(
                        '发送成功{}条，发送失败{}条，错误信息：{}'.format(i + 199, len(open_ids) - i - 199, str(result)))
        except Exception as e:
            raise FeishuException(e)

    def get_user_id_info(self, user_code, email_type='@company.com'):
        """
        通过邮箱获取用户的飞书唯一标识 ,(https://open.feishu.cn/document/ukTMukTMukTM/uUzMyUjL1MjM14SNzITN)
        :param user_code: company id
        :param email_type: 邮箱类型，主要是有些用户不是绑定的company.com
        :return: {
                    "open_id": "ou_979112345678741d29069abcdef089d4",
                    "user_id": "a7eb3abe"
                },
        """
        try:
            email_code = user_code + email_type
            result = self._get(self.__opes_url + '/open-apis/user/v1/batch_get_id', {'emails': email_code})
            if 'email_users' in result['data'].keys():
                user_info = result['data']['email_users'][email_code][0]
                return user_info
            else:
                raise FeishuException('飞书账号未与邮箱绑定，请联系飞书管理员绑定邮箱')
        except Exception as ex:
            logger.error("Feishu get user id info fail! user_code={0} error by {1}".format(user_code, ex))
            raise FeishuException(ex)

    def get_user_info(self, user_open_id):
        """
        获取用户的个人信息，只能通过open_id获取 (https://open.feishu.cn/document/ukTMukTMukTM/uIzNz4iM3MjLyczM)
        :param user_open_id: 用户在飞书的唯一标识，可以通过方法self.get_user_id_info获取用户的open_id标识
        :return:
        "user_infos":[
            {
                "name":"zhang san",
                "name_py":"zhang san",
                "en_name":"John",
                "employee_id":"a0615a67",
                "employee_no":"235634",
                "open_id":"ou_e03053f0541cecc3269d7a9dc34a0b21",
                "union_id":"on_7dba11ff38a2119f89349876b12af65c",
                .......
            }
        """
        try:
            user_info = self._get(self.__opes_url + '/open-apis/contact/v1/user/batch_get', {'open_ids': user_open_id})
            if user_info['code'] == 0:
                return user_info['data']['user_infos'][0]
            else:
                raise FeishuException('获取该用户飞书个人信息失败,请联系管理员处理')
        except Exception as ex:
            logger.error("Feishu get user info fail! user_open_id={0} error by {1}".format(user_open_id, ex))
            raise FeishuException(ex)

    def get_department_info(self, open_department_id):
        try:
            department = self._get(self.__opes_url + '/open-apis/contact/v1/department/info/get',
                                   {'open_department_id': open_department_id})
            return department
        except Exception as ex:
            logger.error(
                "Feishu get department info fail! open_department_id={0} error by {1}".format(open_department_id, ex))
            raise FeishuException(ex)

    def approval_create(self, approval_code, apply_user_id, data, approval_user_id=None, approval_node_id=None):
        """
        临时发布申请创建审批
        :param approval_code: 审批流程唯一标识
        :param apply_user_id: 申请人
        :param data: 表单数据
        :param approval_user_id:审批人，不传默认领导审批
        :param approval_node_id:审批节点id，不传默认领导审批
        :return:
        """
        try:
            print(data)
            approval_data = {
                "approval_code": approval_code,
                "user_id": apply_user_id,
                "form": json.dumps(data),
            }
            if approval_user_id:
                approval_data['node_approver_user_id_list'] = {
                    approval_node_id: [approval_user_id],
                    "manager_node_id": [approval_user_id]
                }
            print(approval_data)
            result = self._post(self.__host_url + '/approval/openapi/v2/instance/create', approval_data)
            if result['code'] != 0:
                raise FeishuException('飞书创建审批失败,错误信息：{}，请联系管理员处理'.format(result['msg']))
            else:
                return result['data']
        except Exception as ex:
            logger.error(
                "Feishu approval create fail! approval_code={0},apply_user_id={1},data={2},approval_user_id={3} error by {4}"
                    .format(approval_code, apply_user_id, data, approval_user_id, ex))
            raise FeishuException(ex)

    def approval_revoke(self, approval_code, instance_code, apply_user_id):
        """
        审批撤回
        :param approval_code: 审批流程唯一标识
        :param instance_code: 审批任务id
        :param apply_user_id: 申请人id
        :return:
        """
        try:
            result = self._post(self.__host_url + '/approval/openapi/v2/instance/cancel', {
                'approval_code': approval_code,
                'instance_code': instance_code,
                'user_id': apply_user_id
            })
            if result['code'] != 0:
                if self.__check_approval_status(result, instance_code, 'CANCELED'):
                    return 'repeat'
                else:
                    raise FeishuException('飞书撤回审批失败,错误信息：{}，请联系管理员处理'.format(result['msg']))
            else:
                return 'success'
        except Exception as ex:
            logger.error("Feishu approval revoke fail! instance_code={0},error by {1}"
                         .format(instance_code, ex))
            raise FeishuException(ex)

    def get_approval_info(self, instance_code):
        """
        获取审批实例详情
        :param instance_code:审批任务id
        :return:
        """
        try:
            result = self._post(self.__host_url + '/approval/openapi/v2/instance/get', {
                'instance_code': instance_code
            })
            if result['code'] == 0:
                return result['data']
            else:
                raise FeishuException('飞书获取审批实例详情失败，错误信息是:{0},请联系管理员处理'.format(result['msg']))
        except Exception as ex:
            logger.error("Feishu approval revoke fail! instance_code={0},error by {1}"
                         .format(instance_code, ex))
            raise FeishuException(ex)

    def __check_approval_status(self, result, instance_code, oper):
        """
        检查审批状态，如果状态与操作不一致，则提示用户
        :param result:飞书的返回状态是65001，内部错误，所以判断一下是不是飞书状态跟操作不一致
        :param instance_code:审批任务id
        :param oper:执行的操作
        :return:
        """
        if result['code'] == 65001:
            try:
                approval_info = self.get_approval_info(instance_code)
                if approval_info['status'] == oper:
                    return True
                elif approval_info['status'] == 'APPROVED':
                    raise FeishuException('飞书审批已经通过,无法进行审批{}'.format(OPER_DICT[oper]))
                elif approval_info['status'] == 'REJECTED':
                    raise FeishuException('飞书审批已经拒绝,无法进行审批{}'.format(OPER_DICT[oper]))
                elif approval_info['status'] == 'CANCELED':
                    raise FeishuException('飞书审批已经撤回,无法进行审批{}'.format(OPER_DICT[oper]))
                elif approval_info['status'] == 'DELETED':
                    raise FeishuException('飞书审批已经删除,无法进行审批{}'.format(OPER_DICT[oper]))
                else:
                    return False
            except Exception as ex:
                logger.error("Feishu check status approval fail! result={0},instance_code={1},oper{2},error by {3}"
                             .format(result, instance_code, oper, ex))
                raise FeishuException(ex)


class FeishuApproval(FeiShu):
    """飞书审批公共类，提供撤回、同意、拒绝接口,不能单独使用，为接口类"""

    def revoke_apply(self, instance_code=None, approval_code=None, companyid=None):
        """
        撤回审批
        :param instance_code:
        :return:
        """
        user_id_info = self.get_user_id_info(companyid)
        feishu_result = self.approval_revoke(
            approval_code,
            instance_code,
            user_id_info['user_id']
        )
        return feishu_result

    def get_approval_content(self, instance_code):
        """
        获取审批内容
        :param instance_code: 审批任务id
        :return:
        """
        approval_info = self.get_approval_info(instance_code)
        for obj in approval_info['timeline']:
            if 'comment' in obj.keys():
                return obj['comment']
        return ''

    def get_leader_comment(self,approval_info=None):
        """
        获取审批流领导评论
        :param instance_code: 审批任务id
        :return:
        """
        # if approval_info:
        #     approval_info = self.get_approval_info(instance_code)
        task_id=''
        for obj in approval_info['task_list']:
            if obj['node_name']=='领导审批' and obj['status'] in ['APPROVED','REJECTED']:
                task_id=obj['id']
                break
        for obj in approval_info['timeline']:
            if 'task_id' in obj.keys() and obj['task_id']==task_id:
                if 'comment' in obj.keys():
                    return obj['comment']
        return ''

    def get_ops_comment(self, instance_code=None, approval_info=None):
        """
        获取审批流运维评论
        :param instance_code: 审批任务id
        :return:
        """
        if instance_code:
            approval_info = self.get_approval_info(instance_code)
        task_id = ''
        for obj in approval_info['task_list']:
            if obj['node_name'] == '运维审批' and obj['status'] in ['APPROVED', 'REJECTED']:
                task_id = obj['id']
                break
        for obj in approval_info['timeline']:
            if 'task_id' in obj.keys() and obj['task_id'] == task_id:
                if 'comment' in obj.keys():
                    return obj['comment']
        return ''


class FeishuCapacityAndEmergencyApproval(FeishuApproval):
    """
    飞书扩容审批流操作类
    """

    def create_apply(self, capacity_obj=None, emergency_obj=None, unit_capacity_objs=None,
                     leader=None, user_code=None, app_approval=None, app_approval_detail=None):
        """
        创建审批申请
        """
        FS_PLUS_CAPACITY_APPROVAL_CODE = current_app.config["FS_PLUS_CAPACITY_APPROVAL_CODE"]
        FS_REDUCE_CAPACITY_APPROVAL_CODE = current_app.config["FS_REDUCE_CAPACITY_APPROVAL_CODE"]
        FS_EMERGENCY_RELEASE_APPROVAL_CODE = current_app.config["FS_EMERGENCY_RELEASE_APPROVAL_CODE"]
        
        user_id_info = self.get_user_id_info(user_code)
        value = ""

        if capacity_obj:
            # 扩容分支
            if capacity_obj.capacity_kind == 0:
                approval_code = FS_PLUS_CAPACITY_APPROVAL_CODE.get("approval_code")
                approval_node_id = FS_PLUS_CAPACITY_APPROVAL_CODE.get("approval_node_id")
                for unit_capacity in unit_capacity_objs:
                    unit_capacity_blue_now = unit_capacity.now_blue_instance - unit_capacity.blue_instance if unit_capacity.now_blue_instance is not None and unit_capacity.blue_instance is not None else 0
                    unit_capacity_green_now = unit_capacity.now_green_instance - unit_capacity.green_instance if unit_capacity.now_green_instance is not None and unit_capacity.green_instance is not None else 0
                    unit_capacity_gray_now = unit_capacity.now_gray_instance - unit_capacity.gray_instance if unit_capacity.now_gray_instance is not None and unit_capacity.gray_instance is not None else 0
                    value += "单元{}({}): \n蓝组现有实例数: {}，扩容数: {};" \
                             "\n绿组现有实例数: {}，扩容数: {};" \
                             "\n灰组现有实例数: {}，扩容数: {}\n\n".format(unit_capacity.unit, "扩容",
                                                                unit_capacity.blue_instance if unit_capacity.blue_instance else 0,
                                                                unit_capacity_blue_now,
                                                                unit_capacity.green_instance if unit_capacity.green_instance else 0,
                                                                unit_capacity_green_now,
                                                                unit_capacity.gray_instance if unit_capacity.gray_instance else 0,
                                                                unit_capacity_gray_now)
                if capacity_obj.app_type == 0:
                    deploy_type = FS_PLUS_CAPACITY_APPROVAL_CODE.get("form_info").get("deploy_type").get('k8s')
                else:
                    deploy_type = FS_PLUS_CAPACITY_APPROVAL_CODE.get("form_info").get("deploy_type").get('dvd')
            # 缩容分支
            else:
                approval_code = FS_REDUCE_CAPACITY_APPROVAL_CODE.get("approval_code")
                approval_node_id = FS_REDUCE_CAPACITY_APPROVAL_CODE.get("approval_node_id")
                for unit_capacity in unit_capacity_objs:
                    unit_capacity_blue_now = unit_capacity.blue_instance - unit_capacity.now_blue_instance if unit_capacity.now_blue_instance is not None and unit_capacity.blue_instance is not None else 0
                    unit_capacity_green_now = unit_capacity.green_instance - unit_capacity.now_green_instance if unit_capacity.now_green_instance is not None and unit_capacity.green_instance is not None else 0
                    unit_capacity_gray_now = unit_capacity.gray_instance - unit_capacity.now_gray_instance if unit_capacity.now_gray_instance is not None and unit_capacity.gray_instance is not None else 0
                    value += "单元{}({}): \n蓝组现有实例数: {}，缩容数: {};" \
                             "\n绿组现有实例数: {}，缩容数: {};" \
                             "\n灰组现有实例数: {}，缩容数: {}\n\n".format(unit_capacity.unit, "缩容",
                                                                unit_capacity.blue_instance if unit_capacity.blue_instance else 0,
                                                                # unit_capacity.blue_instance - unit_capacity.now_blue_instance,
                                                                unit_capacity_blue_now,
                                                                unit_capacity.green_instance if unit_capacity.green_instance else 0,
                                                                # unit_capacity.green_instance - unit_capacity.now_green_instance,
                                                                unit_capacity_green_now,
                                                                unit_capacity.gray_instance if unit_capacity.gray_instance else 0,
                                                                # unit_capacity.gray_instance - unit_capacity.now_gray_instance
                                                                unit_capacity_gray_now
                                                                )

                if capacity_obj.app_type == 0:
                    deploy_type = FS_REDUCE_CAPACITY_APPROVAL_CODE.get("form_info").get("deploy_type").get('k8s')
                else:
                    deploy_type = FS_REDUCE_CAPACITY_APPROVAL_CODE.get("form_info").get("deploy_type").get('dvd')

            # 构建表单
            form_data = [{"id": "module_code", "type": "input", "value": capacity_obj.app_name},
                         {"id": "capacity_text", "type": "textarea", "value": value},
                         {"id": "deploy_type", "type": "radioV2", "value": deploy_type},
                         {"id": "apply_reason", "type": "textarea", "value": capacity_obj.apply_reason}]
        elif emergency_obj:
            approval_code = FS_EMERGENCY_RELEASE_APPROVAL_CODE.get("approval_code")
            approval_node_id = FS_EMERGENCY_RELEASE_APPROVAL_CODE.get("approval_node_id")
            leader_approval = FS_EMERGENCY_RELEASE_APPROVAL_CODE.get("form_info").get("approval_type").get(
                'leader_approval')
            custome_approval = FS_EMERGENCY_RELEASE_APPROVAL_CODE.get("form_info").get("approval_type").get(
                'custome_approval')
            if emergency_obj.app_type == 0:
                deploy_type = FS_EMERGENCY_RELEASE_APPROVAL_CODE.get("form_info").get("deploy_type").get('k8s')
            else:
                deploy_type = FS_EMERGENCY_RELEASE_APPROVAL_CODE.get("form_info").get("deploy_type").get('dvd')

            if leader:
                approval_type = custome_approval
            else:
                approval_type = leader_approval

            form_data = [{"id": "module_code", "type": "input", "value": emergency_obj.app_name},
                         {"id": "deploy_type", "type": "radioV2", "value": deploy_type},
                         {"id": "approval_type", "type": "radioV2", "value": approval_type},
                         {"id": "timerange", "type": "dateInterval", "value": {
                             "start": datetime.strftime(emergency_obj.cd_start_time, "%Y-%m-%dT%H:%M:%S+08:00"),
                             "end": datetime.strftime(emergency_obj.cd_end_time, "%Y-%m-%dT%H:%M:%S+08:00"),
                             "interval": 4.0}},
                         {"id": "apply_reason", "type": "textarea", "value": emergency_obj.apply_reason}]
        elif app_approval:
            approval_node_id = None
            approval_code = current_app.config["FS_APP_DETAIL_APPROVAL_CODE"].get("approval_code")
            form_data = self.handle_app_approval(app_approval_detail)
        else:
            raise TypeError("必须满足扩缩容/紧急发布任意一种模式")

        if leader:
            feishu_result = self.approval_create(approval_code,
                                                 user_id_info['user_id'],
                                                 form_data,
                                                 approval_user_id=leader,
                                                 approval_node_id=approval_node_id)
        else:
            feishu_result = self.approval_create(approval_code,
                                                 user_id_info['user_id'],
                                                 form_data)
        return feishu_result

    def handle_app_approval(self, data):
        # 构建表单
        value = ""
        old_value = ""
        for _data in data.get("deploymentConfig"):
            value += f"单元{_data.get('zone')}蓝组个数{_data.get('blue')}, 绿组个数{_data.get('green')}, 灰组个数{_data.get('gray')}\n"
        for _old_data in data.get("old_deployment"):
            old_data = data['old_deployment'][_old_data]
            old_value += f"单元{_old_data}蓝组个数{old_data.get('blue')}, 绿组个数{old_data.get('green')}, 灰组个数{old_data.get('gray')}\n"
        form_data = [{"id": "version_type", "type": "input", "value": data.get("versionType")},
                     {"id": "env", "type": "input", "value": data.get("Environment")},
                     {"id": "code", "type": "input", "value": data.get("code")},
                     {"id": "all_specs", "type": "input", "value": data.get("resourceName")},
                     {"id": "old_all_specs", "type": "input", "value": data.get("old_resource_name")},
                     {"id": "apply_reason", "type": "textarea", "value": value},
                     {"id": "old_apply_reason", "type": "textarea", "value": old_value}]
        return form_data
