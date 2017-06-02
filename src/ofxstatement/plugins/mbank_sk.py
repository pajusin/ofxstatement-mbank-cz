# -*- coding: utf-8 -*-

"""
    Author: Michal Zimen mzimen@epitheton.com
"""

from ofxstatement.plugin import Plugin
from ofxstatement.parser import StatementParser, CsvStatementParser
from ofxstatement.statement import StatementLine, Statement

import csv, re, datetime


class MBankSKPlugin(Plugin):
    """MBank.SK plugin (for developers only)
    """

    def get_parser(self, filename):
        return MBankSKParser(filename)


class MBankSKParser(CsvStatementParser):
    """
    Parsing CSV file
    """
    mappings = {"date_user":0, "date": 1,
                "payee":4, #"id": 2,
                "memo": 3, "amount": 9, }
    encoding = 'windows-1250' # 'utf-8'
    date_format = "%d-%m-%Y"

    def __init__(self, filename):
        self.filename = filename
        self.statement = Statement()
        self.last_line = ""

    def parse(self):
        """Main entry point for parsers

        super() implementation will call to split_records and parse_record to
        process the file.
        """
        with open(self.filename, "r", encoding=self.encoding) as self.csvfile:
            return super(MBankSKParser, self).parse()

    def split_records(self):
        """Return iterable object consisting of a line per transaction
        """
        return csv.reader(self.csvfile, delimiter=';', quotechar='"')

    def parse_float(self, value):
        value = value.replace(" ", "")
        value = value.replace(",", ".")
        return float(value)

    def parse_record(self, line):
        """Parse given transaction line and return StatementLine object
        """
        if not self.statement.currency \
           and re.match(r"^#Mena ..tu", self.last_line):
            self.statement.currency = line[0]
        if not self.statement.bank_id \
           and re.match(r"^#BIC", self.last_line):
            self.statement.bank_id = line[0]
        if not self.statement.account_id \
           and re.match(r"^#..slo ..tu:", self.last_line):
            self.statement.account_id = line[0]
        self.last_line = line[0]
        if len(line) > 10:
            md1 = re.match(r"^\d{2}-\d{2}-\d{4}$", line[0])
            md2 = re.match(r"^\d{2}-\d{2}-\d{4}$", line[1])
            if md1 and md2:
                mx_date = re.search(r'DÁTUM VYKONANIA TRANSAKCIE: (\d+)-(\d+)-(\d+)', line[3])
                if mx_date:
                    line[0] = "-".join([mx_date.group(3), mx_date.group(2),
                                       mx_date.group(1)])
                # let super CSV parserd with mappings do this job instead
                stmt_line = super(MBankSKParser, self).parse_record(line)
                if len(stmt_line.date_user):
                    stmt_line.date_user = datetime.datetime.strptime(line[0], self.date_format)
                if line[2] == "PLATBA KARTOU":
                    stmt_line.trn_type = "PAYMENT"
                elif line[2] == u"VÝBER V BANKOMATE":
                    stmt_line.trn_type = "ATM"
                else:
                    stmt_line.trn_type = "XFER"
                return stmt_line
