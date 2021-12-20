# -*- coding: utf-8 -*-

"""
    Author: Michal Zimen mzimen@epitheton.com
"""

from ofxstatement.plugin import Plugin
from ofxstatement.parser import StatementParser, CsvStatementParser
from ofxstatement.statement import StatementLine, Statement, BankAccount, Currency, TRANSACTION_TYPES
import hashlib
import base64

import csv, re, datetime
from datetime import timezone, timedelta

class MBankCZPlugin(Plugin):
    """MBank.CZ plugin (for developers only test)
    """

    def get_parser(self, filename):
        return MBankCZParser(filename)


def calculateHash(stmt_line):
    encode_bytes = hashlib.md5(str(stmt_line).encode()).hexdigest().encode('ascii')
    return base64.b64encode(encode_bytes).decode('ascii')[:18]

def createPaymentTypes(types):
    paymentTypes = {}
    for type in types:
        match type:
            case "CREDIT":  # Generic credit
                paymentTypes[type] = ["P..CHOZ. PLATBA Z"]
            case "DEBIT":  # Generic debit
                paymentTypes[type] = ["ODCHOZ. PLATBA DO", ".V.R"]
            case "ATM":  # ATM debit or credit
                paymentTypes[type] = ["BANKOMAT"]
            case "PAYMENT":  # Electronic payment
                paymentTypes[type] = ["KARTOU"]
            case "DIRECTDEBIT":  # Merchant initiated debit
                paymentTypes[type] = ["INKASO", "SIPO"]
    return paymentTypes

class MBankCZParser(CsvStatementParser):
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
        self.paymentTypes = createPaymentTypes(TRANSACTION_TYPES)

    def parse(self):
        """Main entry point for parsers

        super() implementation will call to split_records and parse_record to
        process the file.
        """
        with open(self.filename, "r", encoding=self.encoding) as self.csvfile:
            return super(MBankCZParser, self).parse()

    def split_records(self):
        """Return iterable object consisting of a line per transaction
        """
        return csv.reader(self.csvfile, delimiter=';', quotechar='"')

    def parse_float(self, value):
        value = value.replace(" ", "")
        value = value.replace(",", ".")
        return float(value)

    def getTrnType(self, payType):
        for key in self.paymentTypes:
            posibilities = self.paymentTypes[key]
            for item in posibilities:
                if re.match(r".*" + item, payType):
                    return key
        return "OTHER"

    def parse_record(self, line):
        """Parse given transaction line and return StatementLine object
        """
        if not self.statement.currency \
           and re.match(r"^#M.na ..tu", self.last_line):
            self.statement.currency = line[0]
        if not self.statement.bank_id \
           and re.match(r"^#BIC", self.last_line):
            self.statement.bank_id = line[0]
        if not self.statement.account_id \
           and re.match(r"^#..slo ..tu:", self.last_line):
            self.statement.account_id = line[0]
        if not self.statement.start_date \
           and re.match(r"^#Za obdob.", self.last_line):
            self.statement.start_date = datetime.datetime.strptime(line[0], "%d.%m.%Y").replace(tzinfo=timezone(timedelta(hours=1)))
            self.statement.end_date = datetime.datetime.strptime(line[1], "%d.%m.%Y").replace(hour=23, minute=59, second=59, tzinfo=timezone(timedelta(hours=1)))
        if not self.statement.start_balance \
           and len(line) > 6 \
           and re.match(r"^#Po..te.n. z.statek:", line[6]):
            self.statement.start_balance = self.parse_decimal(re.sub("[ .a-zA-Z]", "", line[7]).replace(",", "."))
        if not self.statement.end_balance \
           and len(line) > 6 \
           and re.match(r"^#Kone.n. z.statek:", line[6]):
            self.statement.end_balance = self.parse_float(re.sub("[ .a-zA-Z]", "", line[7]).replace(",", "."))
        self.last_line = line[0]
        if len(line) > 10:
            md1 = re.match(r"^\d{2}-\d{2}-\d{4}$", line[0])
            md2 = re.match(r"^\d{2}-\d{2}-\d{4}$", line[1])
            if md1 and md2:
                mx_date = re.search(r'DATUM PROVEDENÍ TRANSAKCE: (\d+)-(\d+)-(\d+)', line[3])
                if mx_date:
                    line[0] = "-".join([mx_date.group(3), mx_date.group(2),
                                       mx_date.group(1)])
                # let super CSV parserd with mappings do this job instead
                stmt_line = super(MBankCZParser, self).parse_record(line)

                stmt_line.currency = Currency(self.statement.currency)
                stmt_line.refnum = ""
                if len(line[7]):
                    stmt_line.refnum = stmt_line.refnum + "/VS" + line[7]
                if len(line[8]):
                    stmt_line.refnum = stmt_line.refnum + "/SS" + line[8]
                if len(line[6]):
                    stmt_line.refnum = stmt_line.refnum + "/KS" + line[6]
                if len(line[5]):
                    stmt_line.bank_account_to = BankAccount("", re.sub("[ ']", "", line[5]))
                else:
                    stmt_line.bank_account_to = None

                print(stmt_line)
                if len(str(stmt_line.date_user)):
                    stmt_line.date_user = datetime.datetime.strptime(line[0], self.date_format).replace(tzinfo=timezone(timedelta(hours=1)))
                stmt_line.date = stmt_line.date.replace(tzinfo=timezone(timedelta(hours=1)))
                stmt_line.trntype = self.getTrnType(line[2])
                if stmt_line.trntype == "PAYMENT":
                    payee = line[3].split('/')
                    if len(payee) > 0:
                        stmt_line.payee = payee[0].strip()
                stmt_line.id = calculateHash(stmt_line)
                return stmt_line




