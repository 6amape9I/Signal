import requests, re

s = open(r'newslinks.txt','r')
links = s.readlines()[:-1]
r = open(r'statyi.txt', 'w', encoding='utf-8')
for link in links:
    print(link, end='')
    #Markdownstyled__Wrapper-sc-1kn53tb-0 laVxKq - div с основным текстом, может быть не один
    #Text__sc-vycpdy-0 eFjttV - блок заголовка
    req = requests.get(link)
    content = req.text
    zagolovki = re.findall(r'<h1[^>]*class="Text__sc-vycpdy-0 eFjttV"[^>]*>(.*?)</h1>', content)
    text = re.findall(r'<div',content)
    print(list(zagolovki))

    content_div = re.search(r'<div[^>]*class="Markdownstyled__Wrapper-sc-1kn53tb-0 laVxKq"[^>]*>(.*?)</div>', content, re.DOTALL)

    paragraphs = []
    if content_div:
        # Ищем абзацы только внутри этого div
        content_text = content_div.group(1)
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', content_text, re.DOTALL)

    # Очистка текста
    clean_paragraphs = []
    for paragraph in paragraphs:
        clean_text = re.sub(r'<[^>]+>', '', paragraph)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        if clean_text and len(clean_text) > 10:
            clean_paragraphs.append(clean_text.replace('&nbsp',''))

    print(clean_paragraphs)
    text = ''
    for i in clean_paragraphs:
        text+=i
    r.write(f'{zagolovki[0]}\n{text}\n\n')
r.close()

