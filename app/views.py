from django.http import HttpResponse, JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from app.icloud import ICloud, ICLOUD_DICT
import logging

logger = logging.getLogger('default')


@staff_member_required
def hello(request):
    return HttpResponse("Hello world ! ")


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
