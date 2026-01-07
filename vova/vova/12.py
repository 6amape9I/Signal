import requests

def GetNews(page = 0):
    news = requests.get(f'https://www.vesti.ru/api/news?page={page}')
    article = news.json()['data'][0]['id']
    oneNews = requests.get(f'https://www.vesti.ru/api/article/{article}')
    print(oneNews.json()['data']['body'])

GetNews()