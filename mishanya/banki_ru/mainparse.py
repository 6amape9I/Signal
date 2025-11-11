import requests
import re

st_accept = "text/html"
st_useragent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15"
headers = {
    "Accept": st_accept,
    "User-Agent": st_useragent
}

req = requests.get("https://www.banki.ru/news/lenta/", headers=headers)

content = req.text
matches = re.findall(r'href="/news/lenta/\?id=[^\D]*', content)

s = open('mishanya/banki_ru/newslinks.txt', 'w')
for match in matches:
    s.write("https://www.banki.ru/"+match[7:]+'\n')
s.close()