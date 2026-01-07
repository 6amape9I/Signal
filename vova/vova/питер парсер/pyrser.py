import requests

def GetNews(page):
    news = requests.get(f'https://www.vesti.ru/api/news?page={page}')
    article = news.json()['data'][0]['id']
    oneNews = requests.get(f'https://www.vesti.ru/api/article/{article}')
    print(oneNews.json()['data']['body'])

for i in range(1,10):
    GetNews(i)
    print('sled str')