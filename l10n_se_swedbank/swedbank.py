# -*- coding: utf-8 -*-
"""Class to parse camt files."""
##############################################################################
#
#    Copyright (C) 2013-2016 Vertel AB <http://vertel.se>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GMaxNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

# git clone -b 8.0 https://github.com/OCA/bank-statement-import.git


import re
from datetime import datetime
from openerp.addons.account_bank_statement_import.parserlib import (
    BankStatement)

import logging
_logger = logging.getLogger(__name__)


class avsnitt(object):
    def __init__(self,rec):
        self.header = rec
        self.footer = {}
        self.ins = []
        self.bet = []
        self.type = ''

    def add(self,rec):
        self.type = rec['type']
        if rec['type'] == '20':
            self.type = '20'
            self.ins.append(rec)
        elif rec['type'] == '21':
            self.type = '21'
            self.bet.append(rec)
        elif self.type == '20':
            for r in rec.keys():
                self.bet[-1][r] = rec[r]
        elif self.type == '21':
            for r in rec.keys():
                self.ins[-1][r] = rec[r]
            
    def check_insbelopp(self):
        #print "summa",sum([float(b['betbelopp'])/100 for b in self.ins])
        #print "insbel",float(self.footer['insbelopp']) / 100
        return float(self.footer['insbelopp']) / 100 == sum([float(b['betbelopp'])/100 for b in self.ins])
    def check_antal_bet(self):
        #print "antal",len(self.ins)
        #print "antal_bet",int(self.footer['antal_bet'])
        return len(self.ins) == int(self.footer['antal_bet'])


class BgMaxRowParser(object):
    """Parser for BgMax bank statement import files lines."""
    
    layout = {
            '01': [ # Start post
                ('layoutnamn',3,22),
                ('version',23,24),
                ('skrivdag',25,44),
                ('testmarkering',45,45),
                ('reserv',46,80),
            ],
            '05': [ # Record start
                ('mottagarbankgiro',3,12),
                ('mottagarplusgiro',13,22),
                ('valuta',46,50),
            ],
            '15': [ # Record end / insättning
                ('mottagarbankkonto',3,37),
                ('betalningsdag',38,45),
                ('inslopnummer',46,50),
                ('insbelopp',51,68),
                ('valuta',69,71),
                ('antal_bet',72,79),
                ('typ_av_ins',80,80),
            ],
            '20': [ # betalning
                ('bankgiro',3,12),
                ('referens',13,37),
                ('betbelopp',38,55),
                ('referenskod',56,56),
                ('betalningskanalkod',57,57),
                ('BGC-nummer',58,69),
                ('avibildmarkering',70,70),
                ('reserv',71,80),
            ],
            '21': [ # avdrag
                ('bankgiro',3,12),
                ('referens',13,37),
                ('betbelopp',38,55),
                ('referenskod',56,56),
                ('betalningskanalkod',57,57),
                ('BGC-nummer',58,69),
                ('avibildmarkering',70,70),
                ('avdragskod',71,71),
            ],
            '22': [ 
                ('22bankgiro',3,12),
                ('22referens',13,37),
                ('22betbelopp',38,55),
                ('22referenskod',56,56),
                ('22betalningskanalkod',57,57),
                ('22BGC-nummer',58,69),
                ('22avibildmarkering',70,70),
                ('22reserv',71,80),
            ],
            '23': [ 
                ('23bankgiro',3,12),
                ('23referens',13,37),
                ('23betbelopp',38,55),
                ('23referenskod',56,56),
                ('23betalningskanalkod',57,57),
                ('23BGC-nummer',58,69),
                ('23avibildmarkering',70,70),
                ('reserv',71,80),
            ],
            '25': [ 
                ('informationstext',3,52),
                ('reserv',53,80),
            ],            
            '26': [ 
                ('betalarens_namn',3,37),
                ('extra_namn',38,72),
                ('reserv',73,80),
            ],
            '27': [ 
                ('betalarens_adress',3,37),
                ('betalarens_postnr',38,46),
                ('reserv',47,80),
            ],
            '28': [ 
                ('betalarens_ort',3,37),
                ('betalarens_land',38,72),
                ('betalarens_landkod',73,74),
                ('reserv',75,80),
            ],
            '29': [ 
                ('organisationsnummer',3,14),
                ('reserv',15,80),
            ],
            '70': [ 
                ('antal_betposter',3,10),
                ('antal_avdrag',11,18),
                ('antal_ref',19,26),
                ('antal_ins',27,34),
                ('reserv',35,80),
            ],

        }

    def parse_row(self,row):
        record = {'type': row[0:2]}
        for name,start,stop in self.layout[record['type']]:
            record[name] = row[start-1:stop]
        return record


class bgMaxIterator(BgMaxRowParser):
    def __init__(self, data):
        self.row = 0
        self.data = data.splitlines()
        self.rows = len(self.data)
        self.header = {}
        self.footer = {}
        self.avsnitt = []
    
    def __iter__(self):
        return self

    def next(self):
        if self.row >= self.rows:
            raise StopIteration
        rec = self.next_rec()
        if rec['type'] == '01':
            self.header = rec
            rec = self.next_rec()
        if rec['type'] == '70':
            self.footer = rec
            raise StopIteration()
        if rec['type'] == '05':
            self.avsnitt.append(avs(rec))
            rec = self.next_rec()
            while rec['type'] in ['20','21','22','23','25','26','27','28','29']:
                self.avsnitt[-1].add(rec)
                rec = self.next_rec()                
            if rec['type'] == '15':
                self.avsnitt[-1].footer = rec
            return self.avsnitt[-1]
        return rec

    def next_rec(self):
        self.row += 1
        return self.parse_row(self.data[self.row])
    def check_avsnitt(self):
        ok = True
        for a in self.avsnitt:
            if not (a.check_insbelopp() and a.check_antal_bet()):
                ok = False
        return ok
    def check_antal_ins(self):
        #print "antal",len(self.avsnitt)
        #print "antal_ins",int(self.footer['antal_ins'])
        return len(self.avsnitt) == int(self.footer['antal_ins'])
    def check_antal_betposter(self):
        #print "antal",sum([len(a.ins) for a in self.avsnitt])
        #print "antal_betposter",int(self.footer['antal_betposter'])
        return sum([len(a.ins) for a in self.avsnitt]) == int(self.footer['antal_betposter'])
    def check(self):
        ok = True
        for c,result in [('avsnitt',self.check_avsnitt()),('antal_betpost',self.check_antal_betposter()),('check_antal_ins',self.check_antal_ins())]:
            if not result:
                print "Error in check %s" % c
                ok = False
        return ok



class BgMaxParser(object):
    """Parser for BgMax bank statement import files."""
    
    def __init__(self, data):
        self.row = 0
        self.data = data.splitlines()
        self.rows = len(self.data)
        self.header = {}
        self.footer = {}
        self.avsnitt = []
        self.header_regex = '^01BGMAX'  # Start of header

    def is_bgmax(self, line):
        """determine if a line is the header of a statement"""
        if not bool(re.match(self.header_regex, line)):
            raise ValueError(
                'File starting with %s does not seem to be a'
                ' valid %s format bank statement.' %
                (line[:12], 'BgMax')
            )

    def __init__(self):
        """Initialize parser - override at least header_regex.
        This in fact uses the ING syntax, override in others."""
        self.bgmax_type = 'General'
        self.header_regex = '^01BGMAX'  # Start of header
        self.current_statement = None
        self.current_transaction = None
        self.statements = []
        self.currency = ''
        self.header_balance = 0.0

    def parse(self, data):
        """Parse bgmax bank statement file contents."""
        
        self.is_bgmax(data)
        iterator = BgMaxIterator(data)
        
        for avsnitt in iterator:
            self.current_statement = BankStatement()
            self.statements.append(self.current_statement)
            
        return self.statements


    def handle_record(self, line):
        """find a function to handle the record represented by line"""
        tag_match = re.match(self.tag_regex, line)
        tag = tag_match.group(1)
        #raise Warning(tag)
        _logger.error('got this tk%s' % tag)
        if not hasattr(self, 'handle_tk%s' % re.match(self.tag_regex, line).group(1)):
            _logger.error('Unknown tk%s', re.match(self.tag_regex, line).group(1))
            _logger.error(line)
            return
        handler = getattr(self, 'handle_tk%s' % re.match(self.tag_regex, line).group(1))
        handler(line)

    def handle_tag_60F(self, data):
        """get start balance and currency"""
        # For the moment only first 60F record
        # The alternative would be to split the file and start a new
        # statement for each 20: tag encountered.
        stmt = self.current_statement
        if not stmt.local_currency:
            stmt.local_currency = data[7:10]
            stmt.start_balance = str2amount(data[0], data[10:])

    def handle_tag_61(self, data):
        """get transaction values"""
        transaction = self.current_statement.create_transaction()
        self.current_transaction = transaction
        transaction.execution_date = datetime.strptime(data[:6], '%y%m%d')
        transaction.value_date = datetime.strptime(data[:6], '%y%m%d')
        #  ...and the rest already is highly bank dependent

    def handle_tag_62F(self, data):
        """Get ending balance, statement date and id.

        We use the date on the last 62F tag as statement date, as the date
        on the 60F record (previous end balance) might contain a date in
        a previous period.

        We generate the statement.id from the local_account and the end-date,
        this should normally be unique, provided there is a maximum of
        one statement per day.

        Depending on the bank, there might be multiple 62F tags in the import
        file. The last one counts.
        """
        stmt = self.current_statement
        stmt.end_balance = str2amount(data[0], data[10:])
        stmt.date = datetime.strptime(data[1:7], '%y%m%d')
        # Only replace logically empty (only whitespace or zeroes) id's:
        # But do replace statement_id's added before (therefore starting
        # with local_account), because we need the date on the last 62F
        # record.
        test_empty_id = re.sub(r'[\s0]', '', stmt.statement_id)
        if ((not test_empty_id) or
                (stmt.statement_id.startswith(stmt.local_account))):
            stmt.statement_id = '%s-%s' % (
                stmt.local_account,
                stmt.date.strftime('%Y-%m-%d'),
            )