import requests
import os
import re

def token():
    '''
    Prepare your api_token in 'api.txt'
    '''
    with open('api.txt', 'r') as f:
        api_token = f.read().strip()
    return api_token

def fetch(url:str, new=True):
    '''
    Fetch the task and param of the puzzle from the url
    Example:
        >>> fetch('https://www.puzzle-sudoku.com/')
        ('d7a8f3b6_4...', 'amU5fmJJT2...')
    Args:
        url: str, the url of the puzzle
        new: bool, whether to start a new puzzle
    Returns:
        task: str, the task of the puzzle, needed to be parsed
        param: str, the param of the puzzle to submit the result
    '''
    api_token = token()
    headers = {'Cookie': f'api_token={api_token}'}
    data = {'robot': 1}
    if new:
        data['new'] = '+++New+Puzzle+++'
    response = requests.post(url, headers=headers, data=data)
    task = re.search(r'var task = \'(.*?)\';', response.text).group(1)
    param = re.search(r'name="param" value="(.*?)"', response.text).group(1)
    return task, param

def submit(url:str, result:str, param:str):
    '''
    Submit the result to get the verdict and solparam
    Example:
        >>> submit('https://www.puzzle-sudoku.com/', '1,2,3,4,5,...', 'amU5fmJJT2...')
        ('Congratulations! You have solved the puzzle in ...', 'amVbPEU0Vj...')
    Args:
        url: str, the url of the puzzle
        result: str, the result of the puzzle
        param: str, the param of the puzzle got from fetch()
    Returns:
        verdict: str, the verdict of the result
        solparam: str, the solparam to submit to hall
    '''
    api_token = token()
    headers = {'Cookie': f'api_token={api_token}'}
    data = {'robot': 1, 'ansH': result, 'param': param, 'ready': 'Done'}
    response = requests.post(url, headers=headers, data=data)
    verdict = re.search(r'<div id="ajaxResponse"><p class="(.*?)">(.*?)</p>', response.text).group(2)
    try:
        solparam = re.search(r'name="solparams" value="(.*?)"', response.text).group(1)
    except:
        solparam = ''
    return verdict, solparam

def hall(url:str, solparam:str):
    '''
    Submit to hall of fame
    Example:
        >>> hall('https://www.puzzle-sudoku.com/', 'amVbPEU0Vj...')
        200
    Args:
        url: str, the url of the puzzle
        solparam: str, the solparam got from submit()
    Returns:
        code: int, the status code of the response
    '''
    api_token = token()
    domain = re.search(r'www\.(.*?)\.com', url).group(1)
    url = f'https://www.{domain}.com/hallsubmit.php'
    headers = {'Cookie': f'api_token={api_token}'}
    data = {'solparams': solparam, 'robot': 1}
    response = requests.post(url, headers=headers, data=data)
    return response.status_code


if __name__ == '__main__':
    os.environ['http_proxy'] = '127.0.0.1:10809'
    os.environ['https_proxy'] = '127.0.0.1:10809'
    with open('api.txt', 'r') as f:
        api_token = f.read().strip()
    url = 'https://www.puzzles-mobile.com/api/profile'
    headers = {'Cookie': f'api_token={api_token}'}
    response = requests.get(url, headers=headers)
    print(response.text)