from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, WebDriverException
import logging
import datetime
import pychrome
import json
import random
from threading import Timer
from app.models import Location
import requests
from django.db import IntegrityError
from fmf.settings import YINGYAN_ID, BMAP_AK
import app.mail

logger = logging.getLogger('default')
ICLOUD_DICT = {}


class ICloud(object):

    TIMEOUT = 100

    id = None
    account = None
    browser = None
    chrome = None
    wait = None
    tab = None
    deleted = False
    mapping = set()

    def __init__(self):
        self.id = random.randint(0, 100)
        self.start_browser()
        logger.info('Start a browser.')

    def __wait_for_visible(self, xpath):
        return self.wait.until(expected_conditions.visibility_of_element_located((By.XPATH, xpath)))

    def run_login(self, account, password):
        logger.info('"{account}" is logging in.'.format(account=account))
        self.account = account
        # Get the login page.
        self.browser.get('https://www.icloud.com/#fmf')
        auth_frame = self.__wait_for_visible('//*[@id="auth-frame"]')
        self.browser.switch_to.frame(auth_frame)
        logger.info('Login page is loaded.')

        # Process input: account name and password.
        remember_me_input = self.browser.find_element_by_xpath('//*[@id="remember-me"]')
        remember_me_input.click()

        account_name_text_field = self.browser.find_element_by_xpath('//*[@id="account_name_text_field"]')
        account_name_text_field.send_keys(account)
        account_name_text_field.send_keys(Keys.RETURN)

        password_text_field = self.__wait_for_visible('//*[@id="password_text_field"]')
        password_text_field.send_keys(password)
        password_text_field.send_keys(Keys.RETURN)

        try:
            # Wait until the code controls are visible.
            self.__wait_for_visible('//*[@id="char0"]')
            return True
        except TimeoutException:
            # Login failed.
            return False

    def run_codes(self, codes):
        # Write codes to each controls.
        for i in range(6):
            char = self.browser.find_element_by_xpath('//*[@id="char{i}"]'.format(i=i))
            char.send_keys(codes[i])

        try:
            # Click trust button
            trust_browser = self.__wait_for_visible('//*[starts-with(@id, "trust-browser-")]')
            trust_browser.click()
        except TimeoutException:
            # Codes were incorrect.
            return False

        self.save_cookies()

        logger.info('Start network listening...')
        self.tab = self.chrome.list_tab()[-1]
        self.tab.Network.responseReceived = self.response_received
        self.tab.start()
        self.tab.Network.enable()
        # Start auto refresh.
        Timer(60, self.auto_refresh).start()
        return True

    def save_cookies(self):
        cookies = self.browser.get_cookies()
        jsonCookies = json.dumps(cookies)
        with open('./logs/{id}.cookies'.format(id=self.id), 'w') as f:
            f.write(jsonCookies)

    def load_cookies(self):
        self.browser.delete_all_cookies()
        with open('./logs/{id}.cookies'.format(id=self.id), 'r') as f:
            listCookies = json.loads(f.read())
        for cookie in listCookies:
            self.browser.add_cookie({
                'domain': cookie['domain'],
                'name': cookie['name'],
                'value': cookie['value'],
                'path': '/',
                'expires': None
            })
        logger.info('Browser cookies loaded.')

    def start_browser(self):
        # Start chromedriver
        options = webdriver.ChromeOptions()
        options.add_argument('--disable-background-networking=false')
        options.add_argument('--no-sandbox')
        retry_count = 0
        while True:
            try:
                self.browser = webdriver.Chrome(chrome_options=options,
                                                service_args=['--verbose',
                                                              '--log-path=./logs/{id}.log'.format(id=self.id)])
                break
            except ConnectionResetError as e:
                retry_count += 1
                if retry_count >= 10:
                    raise e
        self.browser.set_page_load_timeout(self.TIMEOUT)
        self.wait = WebDriverWait(self.browser, self.TIMEOUT)
        # Get debug url
        url = None
        with open('./logs/{id}.log'.format(id=self.id), 'r') as log:
            for line in log:
                if 'DevTools request: http://localhost' in line:
                    url = line[line.index('http'):].replace('/json/version', '').strip()
                    break
        if not url:
            raise Exception('Invalid protocol url.')
        # Start pychrome
        self.chrome = pychrome.Browser(url=url)

    def restart_browser(self):
        try:
            if self.browser:
                self.browser.close()
                self.browser.quit()
        except Exception:
            pass
        self.start_browser()
        logger.info('Browser restarted.')
        retry = 0
        while True:
            try:
                self.browser.get('https://www.icloud.com')
                self.load_cookies()
                self.browser.get('https://www.icloud.com/#fmf')
                break
            except Exception as e:
                retry += 1
                if retry >= 5:
                    raise e
        logger.info('Start network listening...')
        self.tab = self.chrome.list_tab()[-1]
        self.tab.Network.responseReceived = self.response_received
        self.tab.start()
        self.tab.Network.enable()
        # Start auto refresh.
        Timer(60, self.auto_refresh).start()

    def auto_refresh(self):
        if self.deleted:
            return
        try:
            self.browser.switch_to.default_content()
            frame = self.__wait_for_visible('//*[@id="fmf"]')
            self.browser.switch_to.frame(frame)

            nearby = self.__wait_for_visible('/html/body/div[2]/div/div/div[2]/div[1]/div/div[3]/div[1]/div[1]')
            friends = self.browser.find_elements_by_xpath('/html/body/div[2]/div/div/div[2]/div[1]/div/div[3]/div[1]/div[not(contains(@class, "nearby"))]')
            for friend in friends:
                friend.click()
            nearby.click()
            self.save_cookies()
            Timer(60, self.auto_refresh).start()
        except WebDriverException as e:
            logger.error(e.args)
            self.refresh_page()

    def refresh_page(self, retry=1):
        if self.deleted:
            return
        if retry >= 5:
            logger.error('SERVICE DOWN! restarting...')
            try:
                self.restart_browser()
            except Exception as e:
                ICLOUD_DICT.pop(self.account)
                app.mail.send('FMF: SERVICE DOWN', '<p>{account} unavailable, login again.</p><p>{e}</p>'.format(account=self.account, e=e.args), img='logs/{id}.png'.format(id=self.id))
            return
        logger.info('REFRESHING...')
        try:
            self.browser.save_screenshot('logs/{id}.png'.format(id=self.id))
            self.browser.get('https://www.icloud.com/#fmf')
            Timer(60, self.auto_refresh).start()
        except Exception as e:
            logger.error(e.args)
            retry += 1
            Timer(10, self.refresh_page, [retry]).start()

    def response_received(self, **kwargs):
        response = kwargs.get('response')
        request_id = kwargs.get('requestId')
        if 'refreshClient' in response.get('url'):
            try:
                content = self.tab.Network.getResponseBody(requestId=request_id)['body']
            except pychrome.CallMethodException:
                return
            logger.info('{request_id}: {content}'.format(request_id=request_id, content=content))
            obj = json.loads(content)
            if 'locations' in obj:
                contacts = {}
                for contact in obj['contactDetails']:
                    id = contact['id']
                    name = '{first} {middle} {last}'.format(first=contact['firstName'], middle=contact['middleName'], last=contact['lastName']).strip()
                    contacts[id] = name
                for loc in obj['locations']:
                    if loc['location'] is None:
                        continue
                    id = loc['id']
                    locid = loc['location']['locationId']
                    if loc['location']['address'] is None:
                        address = 'UNKNOWN'
                    elif 'formattedAddressLines' in loc['location']['address']:
                        address = ' '.join(loc['location']['address']['formattedAddressLines'])
                    else:
                        address = '{streetAddress} {locality} {administrativeArea}'.format(streetAddress=loc['location']['address']['streetAddress'], locality=loc['location']['address']['locality'], administrativeArea=loc['location']['address']['administrativeArea'])
                    time = loc['location']['timestamp'] / 1000.0
                    accuracy = loc['location']['horizontalAccuracy']
                    latitude = loc['location']['latitude']
                    longitude = loc['location']['longitude']
                    self.save_model({
                        'locid': locid,
                        'account': self.account,
                        'uid': id,
                        'name': contacts[id],
                        'time': time,
                        'accuracy': accuracy,
                        'latitude': latitude,
                        'longitude': longitude,
                        'address': address
                    })

    def save_model(self, obj):
        if obj['uid'] not in self.mapping:
            res = requests.get(
                'http://yingyan.baidu.com/api/v3/entity/list', params={
                    'ak': BMAP_AK,
                    'service_id': YINGYAN_ID,
                    'filter': 'entity_names:{uid}'.format(uid=obj['uid'])
                })
            jo = json.loads(res.text)
            if jo['status'] != 0:
                res = requests.post('http://yingyan.baidu.com/api/v3/entity/add', data={
                    'ak': BMAP_AK,
                    'service_id': YINGYAN_ID,
                    'entity_name': obj['uid'],
                    'entity_desc': obj['name']
                })
                logger.info('YingYan ADD entity: {res}'.format(res=res.text))
            self.mapping.add(obj['uid'])
        if Location.objects.filter(locid=obj['locid']):
            return
        try:
            Location.objects.create(
                locid=obj['locid'],
                account=obj['account'],
                uid=obj['uid'],
                name=obj['name'],
                time=datetime.datetime.fromtimestamp(obj['time']),
                accuracy=obj['accuracy'],
                latitude=obj['latitude'],
                longitude=obj['longitude'],
                address=obj['address']
            )
        except IntegrityError:
            pass
        res = requests.post('http://yingyan.baidu.com/api/v3/track/addpoint', data={
            'ak': BMAP_AK,
            'service_id': YINGYAN_ID,
            'entity_name': obj['uid'],
            'latitude': obj['latitude'],
            'longitude': obj['longitude'],
            'loc_time': int(obj['time']),
            'radius': obj['accuracy'],
            'coord_type_input': 'wgs84',
            'address': obj['address']
        })
        logger.info('YingYan ADD point: {res}'.format(res=res.text))

    def __del__(self):
        self.deleted = True
        if self.browser:
            self.browser.close()
            self.browser.quit()
        logger.info('A browser is Closed.')
