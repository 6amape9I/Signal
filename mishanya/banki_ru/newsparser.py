import requests

s = open(r'newslinks.txt','r')
links = s.readlines()[:-1]
for link in links:
    print(link, end='')
    #Markdownstyled__Wrapper-sc-1kn53tb-0 laVxKq - div с основным текстом, может быть не один
    #Text__sc-vycpdy-0 eFjttV - блок заголовка