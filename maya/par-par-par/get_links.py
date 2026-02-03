import time
import requests
from bs4 import BeautifulSoup

#на 500 статей
def get_links():
    try:
        file = open('new_links.txt', 'w')
        links = set()
        for page in range(2,42,2): #range:2.42.2
            url = f'https://kubantv.ru/kultura?page={page}'
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; GPT-5-Nano)'}

            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            for link in soup.find_all('a' ,href=True):
                href = link['href']
                if '/kultura/' in href:
                    url2 = 'https://kubantv.ru'
                    if href.startswith('/'):
                        link1 = url2 + href + '\n'
                        links.add(link1)
                    else:
                        link1 = href + '\n'
                        links.add(link1)
            time.sleep(1)

        file.writelines(links)
        file.close()
        return None
    except Exception as e:
        print(f"Ошибка при получении ссылки: {e}")
        return []

get_links()
