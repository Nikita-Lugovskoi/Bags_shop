from django.core.management import BaseCommand

import pyodbc

from config.settings import USER, PASSWORD, HOST, DRIVER, PAD_DATABASE, DATABASE


class Command(BaseCommand):

    def handle(self, *args, **options):
        Connection_string = f'''DRIVER={DRIVER};
                                SERVER={HOST};
                                DATABASE={PAD_DATABASE};
                                UID={USER};
                                PWD={PASSWORD}'''

        try:
            conn = pyodbc.connect(Connection_string)
        except pyodbc.ProgrammingError as ex:
            print(ex)
        else:
            conn.autocommit = True
            try:
                conn.execute(fr'CREATE DATABASE {DATABASE};')
            except pyodbc.ProgrammingError as ex:
                print(ex)
            else:
                print(f'База данных {DATABASE} успешно создана')
