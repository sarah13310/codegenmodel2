# Analyse et prépare les modèles
import os
from enum import Enum


class Dump(Enum):
    PHPMYADMIN = 1
    DBEAVER = 2
    WORKBENCH = 3
    UNKNOWN = 99


tables = []
keys = []

dump_status = Dump.UNKNOWN


def detect_signature(line):
    status = Dump.UNKNOWN
    if 'MySQL dump' in line:
        status = Dump.DBEAVER
    if 'phpMyAdmin SQL Dump' in line:
        status = Dump.PHPMYADMIN
    if 'Workbench' in line:
        status = Dump.WORKBENCH

    return status


def capitalize_all(s):
    if '_' in s:
        f = s.split('_')
        count = len(f)
        i = 0
        text: str = ""
        for p in f:
            if i < (count - 1):
                text += str(p.capitalize()) + '_'
            else:
                text += str(p.capitalize())
            i += 1
    else:
        text = s

    return text


def class_name_model(line):
    if '_' in line:
        s = capitalize_all(line)
        st = f'{s}Model'
    else:
        s = line.capitalize()
        st = f'{s}Model'
    return str(st)


def purify(keyword, string):
    s = string.replace(keyword, "").replace("`", "").replace("(", "").strip()
    return s


def purify2(keyword, string):
    s = string.replace(keyword, "") \
        .replace("`", "") \
        .replace("(", "") \
        .replace("IF NOT EXISTS", "").strip()
    s = s.split('.')
    if s:
        return s[1]

    return ''


def identify(line, keyword='CREATE TABLE', status=Dump.DBEAVER):
    if keyword in line:
        if status == Dump.DBEAVER:
            s = (purify(keyword, line))
        if status == Dump.WORKBENCH:
            s = purify2(keyword, line)
        return s


def detect_field(line):
    s = ""
    if 'NULL' in line:
        s = line.split("`")
    return s


def detect_primary_key(line):
    if 'PRIMARY KEY' in line:
        s = line.split("`")
        return s[1]
    return ''


def parse(lines):
    is_table = False
    is_primary_key = False
    fields = []
    table_primary_key = ""

    for line in lines:

        if 'CREATE TABLE' in line:
            is_table = True
            w_table = identify(line, 'CREATE TABLE')
            table = {"table": w_table}
            classname = class_name_model(str(w_table))

            table['classname'] = classname
            print('\n')
            print('_' * 40)
            print(f'📕Table {w_table}')
            print('_' * 40)

        if ')' and 'ENGINE' in line:
            is_table = False
            table['fields'] = fields
            tables.append(table)
            fields = []

        if is_table:
            field = detect_field(line)
            if len(field) > 0:
                fields.append(field[1])
                print(f'💬 {field[1]}')

        if is_primary_key:
            key = detect_primary_key(line)
            if key and table_primary_key:
                keys.append([table_primary_key, key])
            is_primary_key = False

        if 'ALTER TABLE' in line:
            is_table = False
            table_primary_key = identify(line, 'ALTER TABLE')
            print('_' * 40)
            print(f' \U0001f511 {table_primary_key}')

            is_primary_key = True


def parse_dbeaver(lines):
    is_table = False
    fields = []

    for line in lines:

        if 'CREATE TABLE' in line:
            is_table = True
            w_table = identify(line, 'CREATE TABLE')
            table = {"table": w_table}
            classname = class_name_model(str(w_table))
            table['classname'] = classname
            print('\n')
            print('_' * 40)
            print(f'📕Table {w_table}')
            print('_' * 40)

        if ')' and 'ENGINE' in line:
            is_table = False
            table['fields'] = fields
            tables.append(table)
            fields = []

        if is_table:
            field = detect_field(line)
            if len(field) > 0:
                fields.append(field[1])
                print(f'💬 {field[1]}')

            key = detect_primary_key(line)
            if key:
                print('_' * 40)
                keys.append([table['table'], key])
                print(f'\U0001f511 {key}')


def parse_workbench(lines):
    is_table = False
    fields = []
    table={}
    dump_status = Dump.WORKBENCH
    for line in lines:

        if 'CREATE TABLE' in line:
            is_table = True
            w_table = identify(line, 'CREATE TABLE', dump_status)
            table = {"table": w_table}
            classname = class_name_model(str(w_table))
            table['classname'] = classname
            print('\n')
            print('_' * 40)
            print(f'📕Table {w_table}')
            print('_' * 40)
            fields=[]

        if is_table:
            field = detect_field(line)
            if len(field) > 0:
                fields.append(field[1])
                print(f'💬 {field[1]}')

        if 'ENGINE =' in line:
            is_table = False
            table['fields'] = fields
            tables.append(table)



        if "PRIMARY KEY" in line:
            key = detect_primary_key(line)
            if key:
                print('_' * 40)
                keys.append([table['table'], key])
                print(f'\U0001f511 {key}')


def scan(file):
    with open(file, 'r') as f:
        lines = f.readlines()

    if 'phpMyAdmin' in lines[0]:
        if Dump.PHPMYADMIN == (detect_signature(lines[0])):
            print('DUMP phpMyAdmin')
            parse(lines)
    if 'dump' in lines[0]:
        if Dump.DBEAVER == (detect_signature(lines[0])):
            print('DUMP Dbeaver')
            parse_dbeaver(lines)
    if 'Workbench' in lines[0]:
        if Dump.WORKBENCH == (detect_signature(lines[0])):
            print('DUMP Workbench')
            parse_workbench(lines)


def create_file(table):
    template = os.getcwd() + "/template.model"
    with open(template) as f:
        buffer = f.readlines()

    fields = table['fields']
    st = ""
    index = 0
    for field in fields:
        field = str(field)
        if index == 0:
            st += f"'{field}',\n"
        else:
            st += f"\t\t'{field}',\n"
        index += 1

    text = ""
    primary_key = ""
    for key in keys:
        if key[0] == table['table']:
            primary_key = key[1]
            break

    for line in buffer:
        if '<CLASSNAME>' in line:
            line = line.replace("<CLASSNAME>", f"{table['classname']}")
        if '<TABLENAME>' in line:
            line = line.replace("<TABLENAME>", f"'{table['table']}'")
        if '<FIELDS>' in line:
            line = line.replace("<FIELDS>", st)
        if '<PRIMARYKEY>' in line:
            if primary_key:
                line = line.replace("<PRIMARYKEY>", f"protected $primaryKey = '{primary_key}';")
                line += '\tprotected $useAutoIncrement = true;\n'
            else:
                line = line.replace("<PRIMARYKEY>", "")

            line = line.replace("//", "")
        text += str(line)

    filename = os.getcwd() + f"/Models/{table['classname']}.php"
    with open(filename, "w+") as fw:
        fw.write(text)


def generateModels():
    for table in tables:
        create_file(table)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print('\033[92mCodeGenModel Verion 2.0')
    print('\033[97m')
    scan('c:/workbench.sql')
    print('_' * 40)
    generateModels()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
