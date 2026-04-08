import openpyxl
import json

def read_xlsx(file_path):
    c=0
    try:

        data = []

        workbook = openpyxl.load_workbook(file_path, data_only=True)
        sheet = workbook.active  # Можно выбрать по имени: workbook["Лист1"]

        # Перебор строк
        for row in sheet.iter_rows(values_only=True):
            if c != 0:
                inp = row[5]+". "+row[6] if row[6] != None else row[5]
                if row[4] == "Политика":
                    new_data = {"input": inp, "output": row[4]}
                    data.append(new_data)

            c+=1

        with open(r'C:\Users\iae81\Documents\GitHub\Signal\Signal\vova\vova\par\tem.json', 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

    except FileNotFoundError:
        print(f"Файл '{file_path}' не найден.")
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}")



# Пример использования
read_xlsx(r"C:\Users\iae81\Documents\GitHub\Signal\Signal\vova\vova\par\dad.xlsx")