from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from app.icloud import ICloud, ICLOUD_DICT
import logging
import requests
import json
from fmf.settings import BMAP_AK, YINGYAN_ID
from django.shortcuts import render

logger = logging.getLogger('default')


@staff_member_required
def hello(request):
    return render(request, 'index.html')


@staff_member_required
def tracks(request):
    if request.method != 'GET':
        return JsonResponse({'status': -1})

    start_time = request.GET.get('start')
    end_time = request.GET.get('end')

    res = requests.get('http://yingyan.baidu.com/api/v3/entity/list', params={
        'ak': BMAP_AK,
        'service_id': YINGYAN_ID
    })
    jo = json.loads(res.text)
    if jo['status'] == 0:
        tracks = []
        for entity in jo['entities']:
            res = requests.get('http://yingyan.baidu.com/api/v3/track/gettrack', params={
                'ak': BMAP_AK,
                'service_id': YINGYAN_ID,
                'entity_name': entity['entity_name'],
                'start_time': start_time,
                'end_time': end_time,
                'is_processed': 1,
                'process_option': 'need_denoise=1,radius_threshold=0,need_vacuate=1,need_mapmatch=0,radius_threhold=0,transport_mode=auto'
            })
            tracks.append({'name': entity['entity_desc'], 'track': json.loads(res.text)})
        return JsonResponse({
            'status': 0,
            'data': tracks
        })
    else:
        return JsonResponse(jo)


@staff_member_required
def feed_start(request):
    if request.method != 'POST':
        return JsonResponse({'code': -1})

    account = request.POST.get('account')
    password = request.POST.get('password')

    if account in ICLOUD_DICT:
        ICLOUD_DICT.pop(account)
        logger.info('"{account}" has already started. Pop it and restart.'.format(account=account))

    icloud = ICloud()
    ICLOUD_DICT[account] = icloud
    if icloud.run_login(account, password):
        logger.info('"{account}" log in successfully. Waiting for codes.'.format(account=account))
        return JsonResponse({"code": 0})
    else:
        logger.info('"{account}" login timeout.'.format(account=account))
        return JsonResponse({"code": 1})


@staff_member_required
def feed_codes(request):
    if request.method != 'POST':
        return JsonResponse({'code': -1})

    account = request.POST.get('account')
    codes = request.POST.get('codes')

    if not codes.isdigit():
        return JsonResponse({'code': -2})

    if account not in ICLOUD_DICT:
        return JsonResponse({'code': -3})

    icloud = ICLOUD_DICT[account]
    if icloud.run_codes(codes):
        logger.info('"{account}" code auth successfully. Ready.'.format(account=account))
        return JsonResponse({"code": 0})
    else:
        logger.info('"{account}" code auth timeout.'.format(account=account))
        return JsonResponse({"code": 1})
