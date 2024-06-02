# Для учета времени работы скрипта
import time
# Для отображения прогресса pdf_parser
from tqdm.auto import tqdm
# Для считывания PDF
import PyPDF2
# Для анализа структуры PDF и извлечения текста
from pdfminer.high_level import extract_pages, extract_text
from pdfminer.layout import LTTextContainer, LTChar, LTRect, LTFigure, LTItemT
# Для извлечения текста из таблиц в PDF
import pdfplumber
# Для извлечения изображений из PDF
from PIL import Image
from pdf2image import convert_from_path
# Для выполнения OCR, чтобы извлекать тексты из изображений 
import pytesseract 
# Для удаления дополнительно созданных файлов
import os


def text_from_pdf(pdf_path: str) -> dict[str: list]:
    # создаём объект файла PDF
    pdfFileObj = open(pdf_path, 'rb')
    # создаём объект считывателя PDF
    pdfReaded = PyPDF2.PdfReader(pdfFileObj)

    # Создаём словарь для извлечения текста из каждого изображения
    text_per_page = {}
    # Извлекаем страницы из PDF
    
    for page_num, page in tqdm(enumerate(extract_pages(pdf_path)), 'Pages', position=2):

        # Инициализируем переменные, необходимые для извлечения текста со страницы
        pageObj = pdfReaded.pages[page_num]
        page_text, line_format = [], []
        text_from_images, text_from_tables = [], []
        page_content = []

        # Инициализируем количество исследованных таблиц
        table_num = 0
        first_element= True
        table_extraction_flag= True

        # Открываем файл pdf
        pdf = pdfplumber.open(pdf_path)
        # Находим исследуемую страницу
        page_tables = pdf.pages[page_num]
        # Находим количество таблиц на странице
        tables = page_tables.find_tables()

        # Находим все элементы
        page_elements = [(element.y1, element) for element in page._objs]
        # Сортируем все элементы по порядку нахождения на странице
        page_elements.sort(key=lambda a: a[0], reverse=True) 

        # Итеративно обходим элементы, из которых состоит страница
        for i, component in tqdm(enumerate(page_elements), 'Elements', position=3, leave=False):
            # Извлекаем положение верхнего края элемента в PDF
            pos = component[0] 
            # Извлекаем элемент структуры страницы
            element = component[1]

            # Проверяем, является ли элемент текстовым
            if isinstance(element, LTTextContainer):
                # Проверяем, находится ли текст в таблице
                if table_extraction_flag is False:
                    # Функция для извлечения текста из текстового блока
                    (line_text, format_per_line) = _text_extraction(element=element)
                    # Добавляем текст каждой строки к тексту страницы
                    page_text.append(line_text)
                    # Добавляем формат каждой строки, содержащей текст
                    line_format.append(format_per_line)
                    page_content.append(line_text)
                else:
                    # Пропускаем текст, находящийся в таблице
                    pass

            # Проверка элементов на наличие изображений
            if isinstance(element, LTFigure):
                # Вырезаем изображение из PDF
                cropped_image_path = _crop_image(element, pageObj)
                # Преобразуем обрезанный pdf в изображение
                image_path = _convert_to_images(cropped_image_path)
                # Извлекаем текст из изображения
                image_text = _image_to_text(image_path)
                text_from_images.append(image_text)
                page_content.append(image_text)
                # Добавляем условное обозначение в списки текста и формата
                page_text.append('image')
                line_format.append('image')

            # Проверка элементов на наличие таблиц
            if isinstance(element, LTRect):
                # Если первый прямоугольный элемент
                if first_element is True and (table_num + 1) <= len(tables):
                    # Находим ограничивающий прямоугольник таблицы
                    lower_side = page.bbox[3] - tables[table_num].bbox[3]
                    upper_side = element.y1 
                    # Функция для извлечения таблицы
                    table = _extract_table(pdf_path=pdf_path, page_num=page_num, table_num=table_num)

                    # Преобразуем информацию таблицы в формат структурированной строки
                    table_string = _table_converter(table=table)
                    # Добавляем строку таблицы в список
                    text_from_tables.append(table_string)
                    page_content.append(table_string)
                    # Устанавливаем флаг True, чтобы избежать повторения содержимого
                    table_extraction_flag = True
                    # Преобразуем в другой элемент
                    first_element = False
                    # Добавляем условное обозначение в списки текста и формата
                    page_text.append('table')
                    line_format.append('table')

                if not isinstance(page_elements[i+1][1], LTRect):
                    table_extraction_flag = False
                    first_element = True
                    table_num+=1

        # Создаём ключ для словаря
        dict_key = 'Page_'+str(page_num)
        # Добавляем список списков как значение ключа страницы
        text_per_page[dict_key]= [page_text, line_format, text_from_images,text_from_tables, page_content]

    # Закрываем объект файла pdf
    pdfFileObj.close()

    # Удаляем созданные дополнительные файлы
    os.remove('../tmp/cropped_image.pdf')
    os.remove('../tmp/PDF_image.png')

    # Возвращаем весь словарь файла text_per_page
    return text_per_page



### Текст из текста PDF
# Создаём функцию для извлечения текста
def _text_extraction(element: list[LTItemT]) -> tuple[str, list[str]]:
    # Извлекаем текст из вложенного текстового элемента
    line_text = element.get_text()
    
    # Находим форматы текста
    # Инициализируем список со всеми форматами, встречающимися в строке текста
    line_formats = []
    for text_line in element:
        if isinstance(text_line, LTTextContainer):
            # Итеративно обходим каждый символ в строке текста
            for character in text_line:
                if isinstance(character, LTChar):
                    # Добавляем к символу название шрифта
                    line_formats.append(character.fontname)
                    # Добавляем к символу размер шрифта
                    line_formats.append(character.size)
    # Находим уникальные размеры и названия шрифтов в строке
    format_per_line = list(set(line_formats))
    
    # Возвращаем кортеж с текстом в каждой строке вместе с его форматом
    return (line_text, format_per_line)


### Текст из картинки
# Создаём функцию для вырезания элементов изображений из PDF
def _crop_image(element, pageObj, path_output_with_name: str ='../tmp/cropped_image'):
    # Получаем координаты для вырезания изображения из PDF
    [image_left, image_top, image_right, image_bottom] = [element.x0,element.y0,element.x1,element.y1] 
    # Обрезаем страницу по координатам (left, bottom, right, top)
    pageObj.mediabox.lower_left = (image_left, image_bottom)
    pageObj.mediabox.upper_right = (image_right, image_top)
    # Сохраняем обрезанную страницу в новый PDF
    cropped_pdf_writer = PyPDF2.PdfWriter()
    cropped_pdf_writer.add_page(pageObj)
    # Сохраняем обрезанный PDF в новый файл
    with open(f'{path_output_with_name}.pdf', 'wb') as cropped_pdf_file:
        cropped_pdf_writer.write(cropped_pdf_file)
    return f'{path_output_with_name}.pdf'


# Создаём функцию для преобразования PDF в изображения
def _convert_to_images(input_file: str, path_output_with_name: str ='../tmp/PDF_image'):
    poppler_path = r"C:\poppler-24.02.0\Library\bin"
    images = convert_from_path(input_file, poppler_path=poppler_path)
    image = images[0]
    output_file = f"{path_output_with_name}.png"
    image.save(output_file, "PNG")
    return f"{path_output_with_name}.png"



# Создаём функцию для считывания текста из изображений
def _image_to_text(image_path: str) -> str:
    # Считываем изображение
    img = Image.open(image_path)
    # Извлекаем текст из изображения
    text = pytesseract.image_to_string(img, lang='eng+rus')
    return text


### Текст из таблицы
# Извлечение таблиц из страницы
def _extract_table(pdf_path: str, page_num: int, table_num: int) -> list[list[list[str | None]]]:
    # Открываем файл pdf
    pdf = pdfplumber.open(pdf_path)
    # Находим исследуемую страницу
    table_page = pdf.pages[page_num]
    # Извлекаем соответствующую таблицу
    table = table_page.extract_tables()[table_num]
    return table


# Преобразуем таблицу в соответствующий формат
def _table_converter(table: list[list[list[str | None]]]) -> str:
    table_string = ''
    # Итеративно обходим каждую строку в таблице
    for row_num in range(len(table)):
        row = table[row_num]
        # Удаляем разрыв строки из текста с переносом
        cleaned_row = [item.replace('\n', ' ') if item is not None and '\n' in item else 'None' if item is None else item for item in row]
        # Преобразуем таблицу в строку
        table_string+=('|'+'|'.join(cleaned_row)+'|'+'\n')
    # Удаляем последний разрыв строки
    table_string = table_string[:-1]
    return table_string


def create_txt_files():
    pdfs_path = '../files/pdfs/all_docs' 
    txts_path = '../files/txts'
    for pdf_file_path in tqdm(os.listdir(pdfs_path), 'Files', position=0):
        pdf_path = f'{pdfs_path}/{pdf_file_path}'
        txt_path = txts_path + f"/{pdf_file_path[:pdf_file_path.rfind('.pdf')]}.txt"

        dict_with_text = text_from_pdf(pdf_path=pdf_path)
        page_numbers = [key for key in dict_with_text.keys()]
        with open(txt_path, "w", encoding='utf-8') as file:
            for page in tqdm(page_numbers, 'Pages', position=1, leave=False):
                result = ''.join(dict_with_text[page][4]) + '\n\n'  # + f"\n{'-'*100}\n"
                file.write(result)


def main():
    create_txt_files()


if __name__ == "__main__":
    start_time = time.time()
    main()
    print(f'Work time = {time.time() - start_time}')