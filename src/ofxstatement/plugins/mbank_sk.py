# -*- coding: utf-8 -*-

"""
    Author: Michal Zimen mzimen@epitheton.com
"""

from ofxstatement.plugin import Plugin
from ofxstatement.parser import StatementParser, CsvStatementParser
from ofxstatement.statement import StatementLine, Statement

import csv, re, datetime
from datetime import timezone, timedelta

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
        if not self.statement.start_date \
           and re.match(r"^#Za obdobie:", self.last_line):
            self.statement.start_date = datetime.datetime.strptime(line[0], "%d.%m.%Y").replace(tzinfo=timezone(timedelta(hours=1)))
            self.statement.end_date = datetime.datetime.strptime(line[1], "%d.%m.%Y").replace(hour=23, minute=59, second=59, tzinfo=timezone(timedelta(hours=1)))
        if not self.statement.start_balance \
           and len(line) > 6 \
           and re.match(r"^#Po.iato.n. zostatok:", line[6]):
            self.statement.start_balance = self.parse_float(re.sub("[ .a-zA-Z]", "", line[7]).replace(",", "."))
        if not self.statement.end_balance \
           and len(line) > 6 \
           and re.match(r"^#Kone.n. zostatok:", line[6]):
            self.statement.end_balance = self.parse_float(re.sub("[ .a-zA-Z]", "", line[7]).replace(",", "."))
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

                stmt_line.refnum = ""
                if len(line[7]):
                    stmt_line.refnum = stmt_line.refnum + "/VS" + line[7]
                if len(line[8]):
                    stmt_line.refnum = stmt_line.refnum + "/SS" + line[8]
                if len(line[6]):
                    stmt_line.refnum = stmt_line.refnum + "/KS" + line[6]

                if len(stmt_line.date_user):
                    stmt_line.date_user = datetime.datetime.strptime(line[0], self.date_format).replace(tzinfo=timezone(timedelta(hours=1)))
                stmt_line.date = stmt_line.date.replace(tzinfo=timezone(timedelta(hours=1)))
                if line[2] == "PLATBA KARTOU":
                    stmt_line.trn_type = "PAYMENT"
                    payee = line[3].split('/')
                    if len(payee) > 0:
                        stmt_line.payee = payee[0].strip()
                elif line[2] == u"VÝBER V BANKOMATE":
                    stmt_line.trn_type = "ATM"
                elif line[2] == u"INKASO":
                    stmt_line.trn_type = "DIRECTDEBIT"
                else:
                    stmt_line.trn_type = "XFER"
                return stmt_line
