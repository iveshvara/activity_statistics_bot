
import datetime

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from _settings import SUPER_ADMIN_ID


def get_today(only_date=False):
    if only_date:
        result = datetime.date.today()
    else:
        result = datetime.datetime.today().replace(microsecond=0)
    return result


def its_admin(id_user, chat_admins):
    if id_user == SUPER_ADMIN_ID:
        return True

    for ii in chat_admins:
        if ii.user.id == id_user:
            return True

    return False


def convert_bool(value):
    if value == True or value == 1:
        return 'Да'
    else:
        return 'Нет'


def convert_bool_binary(value):
    if value == True or value == 1:
        return '1'
    else:
        return '0'


def shielding(text):
    text_result = ''
    # allowed_simbols = ' ,:;—'
    forbidden_characters = '_*[]()~"<>#+-=|{}.!'
    for i in text:
        # if i.isalnum() or i in allowed_simbols:
        #     text_result += i
        # elif i in forbidden_characters:
        #     text_result += '\\' + i
        # else:
        #     pass
        if i in forbidden_characters:
            text_result += '\\' + i
        else:
            text_result += i

    # if text_result[-1] == ':':
    #     text_result = text_result[:-1]

    return text_result


def add_buttons_time_selection(shift):
    inline_kb = InlineKeyboardMarkup(row_width=7)
    massive = []
    massive_line = []
    first_pass = True
    for i in range(12):
        if shift > 0:
            first_pass = False
        value = i + shift
        # if value < 3 or value > 22:
        #     continue
        for ii in ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']:
            i_zero = ''
            if first_pass:
                i_text = ii
                callback_data = 'no'
            else:
                if value < 10:
                    i_zero = '0'
                i_text = i_zero + str(value)# + ':00'
                callback_data = 'call_meeting ' + ii + ' ' + i_zero + str(value)
            massive_line.append(InlineKeyboardButton(text=i_text, callback_data=callback_data))

        first_pass = False
        massive.append(massive_line)
        massive_line = []

    for massive_line in massive:
        inline_kb.row(*massive_line)

    return inline_kb


def get_name_tg(id_user, first_name, last_name, username, fio=None):
    if first_name is None:
        first_name = ''

    if last_name is None:
        last_name = ''

    if username is None:
        username = ''

    if fio is None or fio.split() == '' or len(fio) < 5:
        name_user = shielding(first_name + '\xa0' + last_name).strip()
    else:
        name_user = shielding(fio).strip()
    # if use_username and not i_username == '':
    #     # user = '@' + i_username
    #     user = f'[{name_user}](http://t.me/{i_username})'
    # else:
    #     user = f'[{name_user}](tg://user?id={i_id_user})'
    # если ошибка сохранится, то нужно попробовать хтмл разметку
    user = f'[{name_user}](tg://user?id={id_user})'
    if not username == '':
        user += f'\xa0\(@{shielding(username)}\)'

    return user


def reduce_large_numbers(number):
    # if number <= 10000:
    #     text_result = str(number)
    # else:
    if number == 0:
        text_result = '0'
    else:
        short_number = round(number/1000, 1)
        short_number_integer = str(round(short_number // 1))
        short_number_fractional = str(round(short_number % 1))
        text_result = short_number_integer + '\.' + short_number_fractional + 'K'

    return text_result


def align_by_number_of_characters(number, number_of_characters):
    text_result = str(number)
    if len(text_result) >= number_of_characters:
        return text_result

    cycle_length = number_of_characters - len(text_result)
    for i in range(cycle_length):
        text_result = ' ' + text_result

    return text_result


def message_requirements():
    # return \
    #     '\nТребования к сообщению:\n' \
    #     '— Можно использовать эмодзи и ссылки в открытом виде.\n' \
    #     '— Нельзя использовать форматирование. Введенное форматирование будет утеряно.\n' \
    #     '— Текст должен помещаться в одно сообщение Telegram (не больше 4096 символов).'
    return ""


def add_text_to_array(array_text, text):
    page_length = 4096
    current_page = array_text[-1]
    current_page_learn = len(current_page)
    text_learn = len(text)

    if current_page_learn + text_learn <= page_length:
        array_text[-1] = array_text[-1] + text
    else:
        part_start = 0
        part_end = page_length - current_page_learn
        add_to_current_page = current_page_learn < page_length
        finish = False
        while True:
            part_text = text[part_start:part_end]

            if len(text[part_end:]) == 0:
                finish = True
            else:
                part_end = part_text.rfind(' ')
                if part_end == -1:
                    add_to_current_page = False
                    part_end = part_start + page_length
                    continue
                part_text = text[part_start:part_end]

            if add_to_current_page:
                array_text[-1] = array_text[-1] + part_text
                add_to_current_page = False
            else:
                array_text.append(part_text)

            # array_text[-1] = array_text[-1] + f'\n\n\~ {len(array_text)} \~'

            if finish:
                break

            part_start = part_end + 1
            part_end = part_start + page_length

    return array_text