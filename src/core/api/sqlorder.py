import logging
import json
from libs import baseview, util
from libs import call_inception
import subprocess
from core.task import submit_push_messages
from rest_framework.response import Response
from django.http import HttpResponse
from core.models import (
    DatabaseList,
    SqlOrder
)

CUSTOM_ERROR = logging.getLogger('Yearning.core.views')

conf = util.conf_path()
addr_ip = conf.ipaddress

class sqlsoar(baseview.BaseView):
    def post(self, request, args: str = None):
        try:
            base = request.data['base']
            connection_name = request.data['connection_name']
            sql = request.data['sql']
            arg = request.data['arg']
        except KeyError as e:
            CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
            return Response({'status': 'failed', 'log': '缺少必要参数'})
        else:
            if arg == 'check':
                print(r'echo "%s" | /usr/local/Yearning/soar' % sql)
                result = subprocess.Popen(r'echo "%s" | /usr/local/Yearning/soar' % sql, shell=True,stdout=subprocess.PIPE)
                result =  ''.join([x.decode("utf8","ignore") for x in result.stdout.readlines()])
                return Response({'status': 'success', 'data': result})
            if arg == 'soar':
                info = DatabaseList.objects.get(connection_name=connection_name)
                print(r'echo "%s" | /usr/local/Yearning/soar -online-dsn  %s:%s@%s:%s/%s' % (sql, info.username, info.password, info.ip, info.port, base))
                result = subprocess.Popen('echo "%s" | /usr/local/Yearning/soar -online-dsn  %s:%s@%s:%s/%s' % (sql, info.username, info.password, info.ip, info.port, base), shell=True,
                                          stdout=subprocess.PIPE)
                result = ''.join([x.decode("utf8", "ignore") for x in result.stdout.readlines()])
                return Response({'status': 'success', 'data': result})

class sqlorder(baseview.BaseView):
    '''

    :argument 手动模式工单提交相关接口api

    put   美化sql  测试sql

    post 提交工单

    '''

    def put(self, request, args=None):
        if args == 'beautify':
            try:
                data = request.data['data']
            except KeyError as e:
                CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
            else:
                try:
                    res = call_inception.Inception.BeautifySQL(sql=data)
                    return HttpResponse(res)
                except Exception as e:
                    CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                    return HttpResponse(status=500)

        elif args == 'test':
            try:
                id = request.data['id']
                base = request.data['base']
                sql = request.data['sql']
                sql = str(sql).strip('\n').strip().rstrip(';')
                data = DatabaseList.objects.filter(id=id).first()
                info = {
                    'host': data.ip,
                    'user': data.username,
                    'password': data.password,
                    'db': base,
                    'port': data.port
                }
            except KeyError as e:
                CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
            else:
                try:
                    with call_inception.Inception(LoginDic=info) as test:
                        res = test.Check(sql=sql)
                        return Response({'result': res, 'status': 200})
                except Exception as e:
                    CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                    return HttpResponse(e)

    def post(self, request, args=None):
        try:
            data = json.loads(request.data['data'])
            tmp = json.loads(request.data['sql'])
            type = request.data['type']
            real_name = request.data['real_name']
            id = request.data['id']
        except KeyError as e:
            CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
            return HttpResponse(status=500)
        else:
            try:
                x = [x.rstrip(';') for x in tmp]
                if str(x[0]).lstrip().startswith('use'):
                    del x[0]
                sql = ';'.join(x)
                sql = sql.strip(' ').rstrip(';')
                workId = util.workId()
                SqlOrder.objects.get_or_create(
                    username=request.user,
                    date=util.date(),
                    work_id=workId,
                    status=2,
                    basename=data['basename'],
                    sql=sql,
                    type=type,
                    text=data['text'],
                    backup=data['backup'],
                    bundle_id=id,
                    assigned=data['assigned'],
                    delay=data['delay'],
                    real_name=real_name
                )
                submit_push_messages(
                    workId=workId,
                    user=request.user,
                    addr_ip=addr_ip,
                    text=data['text'],
                    assigned=data['assigned'],
                    id=id
                ).start()
                return Response('已提交，请等待管理员审核!')
            except Exception as e:
                CUSTOM_ERROR.error(f'{e.__class__.__name__}: {e}')
                return HttpResponse(status=500)
