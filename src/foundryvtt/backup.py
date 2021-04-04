import datetime
import os
import re


class Backup(object):

    def __init__(self, path: str, file: str, date: str):
        self._path = path
        self._file = file
        self._full_path = os.path.join(self._path, self._file)
        self._name = self._file[:-4]
        self._date = date

    @property
    def file(self):
        return self._file
    
    @property
    def path(self):
        return self._full_path
    
    @property
    def date(self):
        return self._date

    @property
    def name(self):
        return self._name

    def __str__(self):
        return f"Name: {self.name} date: {self.date}"
    
