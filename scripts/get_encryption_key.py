#!/usr/bin/env python3
import base64
import getpass
import hashlib
import hmac
import json
import sys

import boto3
import requests

# Those values have been obtained from the following files in SwitchBot Android app
# That's how you can verify them yourself
# /assets/switchbot_config.json
# /res/raw/amplifyconfiguration.json
# /res/raw/awsconfiguration.json
SWITCHBOT_INTERNAL_API_BASE_URL = 'https://l9ren7efdj.execute-api.us-east-1.amazonaws.com'
SWITCHBOT_COGNITO_POOL = {
    'PoolId': 'us-east-1_x1fixo5LC',
    'AppClientId': '66r90hdllaj4nnlne4qna0muls',
    'AppClientSecret': '1v3v7vfjsiggiupkeuqvsovg084e3msbefpj9rgh611u30uug6t8',
    'Region': 'us-east-1',
}


def main():
    if len(sys.argv) < 3:
        print(f'Usage: {sys.argv[0]} <device_mac> <username> [<password>]')
        exit(1)

    device_mac = sys.argv[1].replace(':', '').replace('-', '').upper()
    username = sys.argv[2]
    if len(sys.argv) == 3:
        password = getpass.getpass()
    else:
        password = sys.argv[3]

    msg = bytes(username + SWITCHBOT_COGNITO_POOL['AppClientId'], 'utf-8')
    secret_hash = base64.b64encode(
        hmac.new(SWITCHBOT_COGNITO_POOL['AppClientSecret'].encode(), msg, digestmod=hashlib.sha256).digest()).decode()

    cognito_idp_client = boto3.client('cognito-idp', region_name=SWITCHBOT_COGNITO_POOL['Region'])
    auth_response = None
    try:
        auth_response = cognito_idp_client.initiate_auth(
            ClientId=SWITCHBOT_COGNITO_POOL['AppClientId'],
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password,
                'SECRET_HASH': secret_hash,
            }
        )
    except cognito_idp_client.exceptions.NotAuthorizedException as e:
        print(f'Error: Failed to authenticate - {e}')
        exit(1)
    except BaseException as e:
        print(f'Error: Unexpected error during authentication - {e}')
        exit(1)

    if auth_response is None \
            or 'AuthenticationResult' not in auth_response \
            or 'AccessToken' not in auth_response['AuthenticationResult']:
        print(f'Error: unexpected authentication result')
        exit(1)

    access_token = auth_response['AuthenticationResult']['AccessToken']
    key_response = requests.post(
        url=SWITCHBOT_INTERNAL_API_BASE_URL + '/developStage/keys/v1/communicate',
        headers={'authorization': access_token},
        json={'device_mac': device_mac, 'keyType': 'user'}
    )
    key_response_content = json.loads(key_response.content)
    if key_response_content['statusCode'] != 100:
        print('Error: {} ({})'.format(key_response_content['message'], key_response_content['statusCode']))
        exit(1)

    print('Key ID: ' + key_response_content['body']['communicationKey']['keyId'])
    print('Encryption key: ' + key_response_content['body']['communicationKey']['key'])


if __name__ == '__main__':
    main()
