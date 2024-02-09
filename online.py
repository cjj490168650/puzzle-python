import requests
import os
import re

def fetch(url, new=True):
    with open('api.txt', 'r') as f:
        api_token = f.read().strip()
    headers = {'Cookie': f'api_token={api_token}'}
    data = {'robot': 1}
    if new:
        data['new'] = '+++New+Puzzle+++'
    response = requests.post(url, headers=headers, data=data)
    task = re.search(r'var task = \'(.*?)\';', response.text).group(1)
    param = re.search(r'name="param" value="(.*?)"', response.text).group(1)
    return task, param

def submit(url, result, param):
    with open('api.txt', 'r') as f:
        api_token = f.read().strip()
    headers = {'Cookie': f'api_token={api_token}'}
    data = {'robot': 1, 'ansH': result, 'param': param, 'ready': 'Done'}
    response = requests.post(url, headers=headers, data=data)
    verdict = re.search(r'<div id="ajaxResponse"><p class="(.*?)">(.*?)</p>', response.text).group(2)
    return verdict

if __name__ == '__main__':
    os.environ['http_proxy'] = '127.0.0.1:10809'
    os.environ['https_proxy'] = '127.0.0.1:10809'
    with open('api.txt', 'r') as f:
        api_token = f.read().strip()
    url = 'https://www.puzzles-mobile.com/api/profile'
    headers = {'Cookie': f'api_token={api_token}'}
    response = requests.get(url, headers=headers)
    print(response.text)