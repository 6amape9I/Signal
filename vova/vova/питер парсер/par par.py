import requests
from bs4 import BeautifulSoup
import sqlite3
import time
from pathlib import Path

def init_db(db_path='vesti_news.db'):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            url TEXT UNIQUE
        )
    ''')
    conn.commit()
    return conn

def get_article_links():
    base_url = 'https://www.vesti.ru'
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; GPT-5-Nano)'}
    try:
        response = requests.get(base_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        links = set()
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/news/' in href or '/article/' in href:
                if href.startswith('/'):
                    links.add(base_url + href)
                else:
                    links.add(href)
        return list(links)
    except Exception as e:
        print(f"Ошибка при получении списка ссылок: {e}")
        return []

def parse_article(url):
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; GPT-5-Nano)'}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = None
        for tag in ['h1', 'h2']:
            el = soup.find(tag)
            if el and el.get_text(strip=True):
                title = el.get_text(strip=True)
                break
        if not title:
            title = "Без заголовка"
        
        content_blocks = soup.find_all('div', class_='article__text')
        if not content_blocks:
            content_blocks = soup.find_all('p')
        full_text = ' '.join([p.get_text(strip=True) for p in content_blocks if p.get_text(strip=True)])
        if not full_text:
            full_text = soup.get_text(separator=' ', strip=True)
        
        return title, full_text
    except Exception as e:
        print(f"Ошибка при парсинге статьи {url}: {e}")
        return None, None

def save_to_db(conn, title, content, url):
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO articles (title, content, url)
            VALUES (?, ?, ?)
        ''', (title, content, url))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Ошибка БД: {e}")

def write_to_text_file(filepath, articles):
    """
    articles: список словарей {'title': ..., 'content': ..., 'url': ...}
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        for a in articles:
            f.write(f"Заголовок: {a.get('title', 'Без заголовка')}\n")
            f.write(f"URL: {a.get('url', '')}\n\n")
            content = a.get('content', '')
            if content:
                f.write(content + "\n")
            f.write("\n" + ("-" * 80) + "\n\n")

def main():
    db_name = 'vesti_news.db'
    conn = init_db(db_name)
    
    print("Собираю ссылки на новости...")
    links = get_article_links()
    print(f"Найдено ссылок: {len(links)}")
    
    articles_for_txt = []
    
    for i, url in enumerate(links):
        print(f"[{i+1}/{len(links)}] Обработка: {url}")
        title, content = parse_article(url)
        
        if title and content:
            save_to_db(conn, title, content, url)
            articles_for_txt.append({'title': title, 'content': content, 'url': url})
        else:
            print(f"Пропускаю статью по адресу: {url}")
        
        time.sleep(1)

    print("\n--- Отсортированные заголовки из базы данных ---")
    cursor = conn.cursor()
    cursor.execute('SELECT title, content, url FROM articles ORDER BY title ASC')
    rows = cursor.fetchall()
    
    for row in rows:
        print(f"Заголовок: {row[0]}")
        print(f"Текст (первые 100 символов): {row[1][:100]}...\n")
    
    txt_path = 'vesti_news.txt'
    write_to_text_file(txt_path, articles_for_txt)
    print(f"\nТекстовый файл создан: {txt_path}")

    conn.close()

if __name__ == '__main__':
    main()