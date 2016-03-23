import logging
from base64 import b64decode

import boto3
import requests

# Fill this value with the output of
# `aws kms encrypt --key-id alias/lambda-secrets --cli-input-json '{"Plaintext": "<url>"}'`
ENCRYPTED_URL = 'CiDSIjVflQrv9Xm9Wqre38Q2YylLgz6FAR9FNIC7tty9exLYAQEBAgB40iI1X5UK7/V5vVqq3t/ENmMpS4M+hQEfRTSAu7bcvXsAAACvMIGsBgkqhkiG9w0BBwaggZ4wgZsCAQAwgZUGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMtJE4Iyfl96cF7AvaAgEQgGjNQQWBXZHVrY/FVguEYhOinwU4ZPVfEZiTFPzPpq3bEXfbKnFVm17HYAtBnZ1EWoE7qxf/S4/92ujJCqN6aTDTTJILWFuV0gUEO+CmRqgSStHFw9j9XjnDz9ff13U4GgML2PMwtcysTw=='

kms = boto3.client('kms')
slack_url = kms.decrypt(CiphertextBlob=b64decode(ENCRYPTED_URL))['Plaintext']

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def is_comment(body):
    """
    Check to see if the posted body has a comment
    :param dict body:
    :return: bool
    """
    return body.has_key('comment')


def is_changelog(body):
    """

    :param dict body:
    :return: bool
    """
    return body.has_key('changelog')


def parse_issue(body):
    """
    parse the info from the body and add it to a dictonary
    :param dict body:
    :return: dict
    """
    try:
        issue_key = body['issue']['key']
        issue_summary = body['issue']['fields']['summary']
        issue_api_url = body['issue']['self']  # https://foobar.atlassian.net/rest/api/2/issue/14703
    except KeyError as e:
        logger.info('Required key is missing: %s' % e)
        raise AttributeError('Required key is missing')

    url_parts = issue_api_url.split('://')
    proto = url_parts[0]
    url_parts = url_parts[1].split('/')
    domain = url_parts[0]
    url = '%(proto)s://%(domain)s/browse/%(key)s' % {'proto': proto, 'domain': domain, 'key': issue_key}

    return {'key': issue_key, 'summary': issue_summary, 'url': url}


def post_to_slack(channel, fallback, pretext, title, text, issue_info, author, avatar):
    data_dict = {'author': author, 'avatar': avatar}

    for k, v in issue_info.iteritems():
        data_dict['issue_%s' % k] = v

    payload = {
        'attachments': [
            {
                'fallback': fallback % data_dict,
                'pretext': pretext % data_dict,
                'author_name': author,
                'author_icon': avatar,
                'title': title % data_dict,
                'title_link': data_dict.get('issue_url'),
                'text': text % data_dict,
            }
        ]

    }

    if channel is not None:
        payload['channel'] = '#%s' % channel

    r = requests.post(slack_url, json=payload)

    if r.status_code != 200:
        logger.error('Posting to slack failed with status code %s' % r.status_code)

    return


def lambda_handler(event, context):
    body = event.get('body', False)
    channel = event.get('channel', None)

    # If no body is defined, use the event as the body
    if not body:
        body = event

    # Validation
    webhook_event = body.get('webhookEvent')
    if not webhook_event == 'jira:issue_updated':
        logger.warn("Event %s is not supported by this function" % webhook_event)
        return

    # Get general info
    try:
        issue_info = parse_issue(body)
    except AttributeError as e:
        logger.info('Stopped processing, because issue parsing failed: %s' % e)
        return
    if is_comment(body):
        try:
            comment = body['comment']['body']
            author = body['comment']['author']['displayName']
            avatar = body['comment']['author']['avatarUrls']['16x16']
        except KeyError as e:
            logger.info('Stopped processing, because required key is missing: %s' % e)
            return

        post_to_slack(
            channel,
            fallback='New comment from %(author)s, on %(issue_key)s - %(issue_url)s',
            pretext='New commend added',
            title='%(issue_key)s - %(issue_summary)s',
            author=author,
            avatar=avatar,
            text=comment,
            issue_info=issue_info,
        )

    if is_changelog(body):
        try:
            author = body['user'].get('displayName', body['user'].get('Name'))
            avatar = body['user']['avatarUrls']['16x16']
            changes = []
            for change in body['changelog']['items']:
                changes.append({
                    'from': change.get('fromString', change.get('from', None)),
                    'to': change.get('toString', change.get('to', None)),
                    'field': change.get('field', None),
                })
        except KeyError as e:
            logger.info('Stopped processing, because required key is missing: %s' % e)
            return

        text = ''
        for change in changes:
            text += '%(field)s changed from %(from)s to %(to)s\n' % change

        post_to_slack(
            channel,
            fallback='Field changed in %(issue_key)s: %(issue_summary)s by %(author) - %(issue_url)s',
            pretext='Issue updated',
            title='%(issue_key)s - %(issue_summary)s',
            author=author,
            avatar=avatar,
            text=text,
            issue_info=issue_info,
        )

    return
