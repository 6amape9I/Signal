import requests, re, time


def get_article_titles(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        text = re.sub(r'\s+', ' ', resp.text)
        titles = re.findall(r'<h[1-3][^>]*>(.*?)</h[1-3]>', text, re.IGNORECASE)
        article_titles = re.findall(r'<article[^>]*>.*?<h[1-3][^>]*>(.*?)</h[1-3]>', text, re.IGNORECASE)
        a_titles = re.findall(r'<a[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</a>', text, re.IGNORECASE)

        all_titles = titles + article_titles + a_titles
        clean_titles = []

        for title in all_titles:
            clean = re.sub(r'<[^>]*>', '', title).strip()
            if len(clean) > 20 and len(clean) < 200 and clean not in clean_titles:
                clean_titles.append(clean)

        return clean_titles[:5]  # возвращаем первые 5 заголовков

    except Exception as e:
        return [f"Ошибка: {str(e)}"]


sites = [
    'https://ecosphere.press/',
    'https://ria.ru/eco/',
    'https://russian.rt.com/tag/ekologiya/',
    'https://science.mail.ru/rubric/ecology/',
    'https://www.takzdorovo.ru/stati/',
    'https://www.championat.com/articles/lifestyle/_health/1.html',
]


for url in sites:
    domain = url.split('//')[1].split('/')[0]
    print(f'{domain}')

    titles = get_article_titles(url)
    for i, title in enumerate(titles, 1):
        print(f'{i}. {title}')

    print(f'количество заголовков: {len(titles)}\n')
    time.sleep(1)