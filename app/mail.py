import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from fmf.settings import SMTP_HOST, SMTP_PORT, EMAIL_ACCOUNT, EMAIL_PASSWORD, EMAIL_RECEIVERS
import logging

logger = logging.getLogger('default')


def send(subject, content, img=None, to=EMAIL_RECEIVERS):
    msg_root = MIMEMultipart('related')
    msg_root['Subject'] = Header(subject, 'utf-8')
    msg_alternative = MIMEMultipart('alternative')
    msg_root.attach(msg_alternative)
    if img:
        try:
            with open(img, 'rb') as fp:
                msg_image = MIMEImage(fp.read())
                msg_image.add_header('Content-ID', '<image>')
                msg_root.attach(msg_image)
                content = content + '<p><img src="cid:image"></p>'
        except FileNotFoundError:
            pass
    msg_alternative.attach(MIMEText(content, 'html', 'utf-8'))

    try:
        smtp = smtplib.SMTP_SSL()
        smtp.connect(SMTP_HOST, SMTP_PORT)
        smtp.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        smtp.sendmail(EMAIL_ACCOUNT, to, msg_root.as_string())
        smtp.quit()
        logger.info('Email Sent.')
    except smtplib.SMTPException as e:
        logger.error('Send Email Error: {e}'.format(e=e.args))
