import random
import time
import requests
from bs4 import BeautifulSoup


def get_articles():
    try:
        file = open('Articles.txt', 'w')
        titles = []
        texts = []
        links = [str(r) for r in open('new_links.txt')]
        for link in links:
            url = link[:-1]
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'}

            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            #получение заголовков
            articles = soup.find('h1')
            for it in articles:
                title = it.get_text()
                titles.append(title)

            #получение текстов статей
            all_text = ''
            for it in (
                    soup.find_all('p', class_='ds-markdown-paragraph') or soup.find_all('div', class_='article__desc')):
                if soup.find_all('span'):
                    text = it.get_text()
                    all_text = all_text + text
                else:
                    text = it.get_text()
                    all_text = all_text + text
            if '\n' or '\xa0' in all_text:
                all_text = all_text.replace('\n', '')
                all_text = all_text.replace('\xa0', '')
            texts.append(all_text + '\n' + '\n')

            rounded = random.random()
            time.sleep(round(rounded, 3))

        all_articles = [': '.join(x) for x in zip(titles, texts)]
        file.writelines(all_articles)
        file.close()
        return all_articles

    except Exception as e:
        print(f"Ошибка при обработкке статьи: {e}")
        return []


if __name__ == '__main__':
    get_articles()
