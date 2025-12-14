import json

try:
    with open('mishanya/готовые статьи часть 2_1.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
except FileNotFoundError:
    data = []

f = open('mishanya/готовые статьи часть 2.txt','r', encoding='utf-8')
f1 = open('mishanya/готовые статьи часть 2.txt','r', encoding='utf-8')
#k = open('mishanya/готовые статьи часть 1.json','w')
for i in range(len(f.readlines())):
    z = f1.readline()
    s = f1.readline()
    inp = z+'\n'+s
    out = f1.readline()
    new_data = {"input":inp.strip(),"output":out.strip()}
    data.append(new_data)
with open('mishanya/готовые статьи часть 2_1.json', 'w', encoding='utf-8') as file:
    json.dump(data, file, ensure_ascii=False, indent=4)