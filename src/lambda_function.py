from base64 import b64decode
import logging
import boto3
import requests
# Fill this value with the output of
# `aws kms encrypt --key-id alias/lambda-secrets --cli-input-json '{"Plaintext": "<url>"}'`
ENCRYPTED_URL = 'CiDSIjVflQrv9Xm9Wqre38Q2YylLgz6FAR9FNIC7tty9exLYAQEBAgB40iI1X5UK7/V5vVqq3t/ENmMpS4M+hQEfRTSAu7bcvXsAAACvMIGsBgkqhkiG9w0BBwaggZ4wgZsCAQAwgZUGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMtJE4Iyfl96cF7AvaAgEQgGjNQQWBXZHVrY/FVguEYhOinwU4ZPVfEZiTFPzPpq3bEXfbKnFVm17HYAtBnZ1EWoE7qxf/S4/92ujJCqN6aTDTTJILWFuV0gUEO+CmRqgSStHFw9j9XjnDz9ff13U4GgML2PMwtcysTw=='

kms = boto3.client('kms')
slack_url = kms.decrypt(CiphertextBlob = b64decode(ENCRYPTED_URL))['Plaintext']

logger = logging.getLogger()
logger.setLevel(logging.INFO)

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

    try :
        issue_key = body['issue']['key']
        issue_summary = body['issue']['fields']['summary']
        issue_api_url = body['issue']['self']  # https://cloudar.atlassian.net/rest/api/2/issue/14703
        comment = body['comment']['body']
        author = body['comment']['author']['displayName']
        avatar = body['comment']['author']['avatarUrls']['16x16']
    except KeyError as e:
        logger.info('Stopped processing, because required key is missing: %s' % e)
        return

    url_parts = issue_api_url.split('://')
    proto = url_parts[0]
    url_parts = url_parts[1].split('/')
    domain = url_parts[0]
    url = '%(proto)s://%(domain)s/browse/%(key)s' % {'proto': proto, 'domain': domain, 'key': issue_key}
    data_dict = {
        'ik': issue_key,
        'is': issue_summary,
        'a': author,
        'url': url,
    }


    payload = {
        'attachments': [
            {
                'fallback': 'New comment from %(a)s on #%(ik)s - %(url)s' % data_dict,
                'pretext': 'New comment added',
                'author_name': author,
                'author_icon': avatar,
                'title': '#%(ik)s - %(is)s' % data_dict,
                'title_link': url,
                'text': comment,
            }
        ]

    }

    if channel is not None:
        payload['channel'] = '#%s' % channel

    r = requests.post(slack_url, json=payload)

    if r.status_code != 200:
        logger.error('Posting to slack failed with status code %s' % r.status_code)

    return

