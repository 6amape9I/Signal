import requests
import re

st_accept = "text/html"
st_useragent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15"
headers = {
    "Accept": st_accept,
    "User-Agent": st_useragent
}
s = open('mishanya/banki_ru/newslinks.txt', 'w')
for i in range(1,7735):
    req = requests.get(f"https://www.banki.ru/news/lenta/?page={i}", headers=headers)
    content = req.text
    matches = re.findall(r'href="/news/lenta/\?id=[^\D]*', content)
    for match in matches:
        s.write("https://www.banki.ru/"+match[7:]+'\n')
s.close()