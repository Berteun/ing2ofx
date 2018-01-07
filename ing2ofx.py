#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       ing2ofx.py
#
#       Copyright 2013,2016 Arie van Dobben <avandobben@gmail.com>
#       Copyright 2017, Berteun Damman
#
#       This program is free software: you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation, either version 3 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
The intent of this script is to convert ing (www.ing.nl) csv files to ofx files
that can be read by a program like GnuCash (www.gucash.org).

This script is adapted from pb2ofx.pl Copyright 2008, 2009, 2010 Peter Vermaas,
originally found at http://blog.maashoek.nl/2009/07/gnucash-en-internetbankieren/
which is now dead.

The ofx specification can be downloaded from http://www.ofx.net/

ING Specifications can be downloaded from ING:
https://www.ing.nl/media/266197_1216_tcm162-117728.pdf (may become outdated)
"""

import csv
import argparse
import datetime
import os
import re
from collections import defaultdict

def ing_code_to_trntype(ing_code, af_bij):
    af_bij_codes = { 'DV', 'OV', 'VZ' }
    af_bij_map   = { 'Af'  : 'DEBIT',
                     'Bij' : 'CREDIT' }

    trn_codes =    { 'GT': 'PAYMENT', 
                     'BA': 'POS', 
                     'GM': 'ATM', 
                     'IC': 'DIRECTDEBIT', 
                     'ST': 'DIRECTDEP',
                   }

    if ing_code in af_bij_codes:
        return af_bij_map[af_bij]
    else:
        return trn_codes.get(ing_code, 'OTHER')

def get_transaction_amount(amount, af_bij):
    """Converts the amount to negative iff *af_bij* is 'Af', and replaces ',' by '.'"""
    amount = amount.replace(',', '.')
    sign = '-' if af_bij == 'Af' else ''
    return sign + amount

def fix_text(ing_text):
    text = re.sub('  +', ' ', ing_text).strip()
    return text.replace('&', '&amp;').replace('>', '&gt;').replace('<', '&lt;')

def extract_time(memo):
    # Extracts time from "Mededelingen" if there's something in there resembling a date time.
    matches = re.search(r'\d{2}-\d{2}-(?:20)?\d{2} ([0-9]{2}):([0-9]{2})', memo)
    if matches:
        return matches.group(1) + matches.group(2)
    return ''

def make_unique_id(accountto, dtposted, time, trnamt, idslist):
    # the FITID is composed of the bankaccountto, time, date and amount
    fitid = accountto + dtposted + time + trnamt.replace("-", "").replace(".", "")

    # Check if we already used a certain ID
    idcount = 0
    unique_id = fitid
    while unique_id in idslist:
      idcount += 1
      unique_id = fitid + str(idcount)

    return unique_id

def read_csv_file(filename, split_by_month):
    transactions = defaultdict(list)

    with open(filename, 'rb') as csvfile:
        # Open the csvfile as a Dictreader
        csvreader = csv.DictReader(csvfile, delimiter=',', quotechar='"')

        # Keep track of used IDs to prevent double IDs
        idslist = set()

        for row in csvreader:
            # Map ACCOUNT to "Rekening"
            account = re.sub(r' +', '', row['Rekening'])
            trntype =  ing_code_to_trntype(row['Code'], row['Af Bij'])
            dtposted = row['Datum']
            trnamt = get_transaction_amount(row['Bedrag (EUR)'], row['Af Bij'])
            name = fix_text(row['Naam / Omschrijving'])

            # BANKACCTTO maps to "Tegenrekening"
            accountto = row['Tegenrekening']
            # MEMO maps to "Mededelingen"
            memo = fix_text(row['Mededelingen'])
            time = extract_time(memo)

            unique_id = make_unique_id(accountto, dtposted, time, trnamt, idslist)
            # Append ID to list with IDs
            idslist.add(unique_id)

            month = dtposted[:6] if split_by_month else ''

            transactions[month].append(
                {'account': account, 'trntype': trntype, 'dtposted': dtposted,
                 'trnamt': trnamt, 'fitid': unique_id, 'name': name, 'accountto': accountto,
                 'memo': memo})

    return transactions


MESSAGE_HEADER_TEMPLATE = """
<OFX>
   <SIGNONMSGSRSV1>
      <SONRS>                            <!-- Begin signon -->
         <STATUS>                        <!-- Begin status aggregate -->
            <CODE>0</CODE>               <!-- OK -->
            <SEVERITY>INFO</SEVERITY>
         </STATUS>
         <DTSERVER>{current_date}</DTSERVER>   <!-- Oct. 29, 1999, 10:10:03 am -->
         <LANGUAGE>ENG</LANGUAGE>        <!-- Language used in response -->
         <DTPROFUP>{current_date}</DTPROFUP>   <!-- Last update to profile-->
         <DTACCTUP>{current_date}</DTACCTUP>   <!-- Last account update -->
         <FI>                            <!-- ID of receiving institution -->
            <ORG>NCH</ORG>               <!-- Name of ID owner -->
            <FID>1001</FID>              <!-- Actual ID -->
         </FI>
      </SONRS>                           <!-- End of signon -->
   </SIGNONMSGSRSV1>
   <BANKMSGSRSV1>
      <STMTTRNRS>                        <!-- Begin response -->
         <TRNUID>1001</TRNUID>           <!-- Client ID sent in request -->
         <STATUS>                     <!-- Start status aggregate -->
            <CODE>0</CODE>            <!-- OK -->
            <SEVERITY>INFO</SEVERITY>
         </STATUS>"""

MESSAGE_FOOTER_TEMPLATE = """
      </STMTTRNRS>                        <!-- End of transaction -->
   </BANKMSGSRSV1>
</OFX>
"""

MESSAGE_BEGIN_TEMPLATE = """
     <STMTRS>                         <!-- Begin statement response -->
        <CURDEF>EUR</CURDEF>
        <BANKACCTFROM>                <!-- Identify the account -->
           <BANKID>121099999</BANKID> <!-- Routing transit or other FI ID -->
           <ACCTID>{account}</ACCTID> <!-- Account number -->
           <ACCTTYPE>CHECKING</ACCTTYPE><!-- Account type -->
        </BANKACCTFROM>               <!-- End of account ID -->
        <BANKTRANLIST>                <!-- Begin list of statement trans. -->
           <DTSTART>{start_date}</DTSTART>
           <DTEND>{end_date}</DTEND>""" 

MESSAGE_TRANSACTION_TEMPLATE = """
           <STMTTRN>
              <TRNTYPE>{trntype}</TRNTYPE>
              <DTPOSTED>{dtposted}</DTPOSTED>
              <TRNAMT>{trnamt}</TRNAMT>
              <FITID>{fitid}</FITID>
              <NAME>{name}</NAME>
              <BANKACCTTO>
                 <BANKID></BANKID>
                 <ACCTID>{accountto}</ACCTID>
                 <ACCTTYPE>CHECKING</ACCTTYPE>
              </BANKACCTTO>
              <MEMO>{memo}</MEMO>
           </STMTTRN>""" 

MESSAGE_END_TEMPLATE = """
        </BANKTRANLIST>                   <!-- End list of statement trans. -->
        <LEDGERBAL>                       <!-- Ledger balance aggregate -->
           <BALAMT>0</BALAMT>
           <DTASOF>199910291120</DTASOF><!-- Bal date: 10/29/99, 11:20 am -->
        </LEDGERBAL>                      <!-- End ledger balance -->
     </STMTRS>"""

def open_output(args, month_prefix):
    # create path to ofxfile
    if month_prefix:
        month_prefix = month_prefix + '_'

    if not args.outfile:
        csvfile = os.path.basename(args.csvfile)
        filename = month_prefix + csvfile.replace("csv", "ofx").replace("CSV", "OFX")
    else:
        filename = month_prefix + args.outfile

    # if directory does not exists, create it.
    if not os.path.exists(args.dir):
        if not os.path.exists(os.path.join(os.getcwd(), args.dir)):
            os.makedirs(os.path.join(os.getcwd(), args.dir))
            args.dir = os.path.join(os.getcwd(), args.dir)

    return os.path.join(args.dir, filename)

def make_header():
    today_str = datetime.date.today().strftime('%Y%m%d')
    return MESSAGE_HEADER_TEMPLATE.format(current_date = today_str)

def make_message_start(account, mindate, maxdate):
    return MESSAGE_BEGIN_TEMPLATE.format(account=account, start_date=mindate, end_date=maxdate)

def make_transaction(transaction):
    return MESSAGE_TRANSACTION_TEMPLATE.format(**transaction)

def make_message_end():
    return MESSAGE_END_TEMPLATE

def make_footer():
    return MESSAGE_FOOTER_TEMPLATE

def find_accounts(transactions):
    return { t['account'] for t in transactions }

def find_date_range(transactions):
    min_date = min(int(t['dtposted']) for t in transactions)
    max_date = max(int(t['dtposted']) for t in transactions)
    return min_date, max_date

def write_ofx_file(transactions, ofxfile):
    # Determine unique accounts and start and end dates
    accounts = find_accounts(transactions)
    mindate, maxdate = find_date_range(transactions)

    ofxfile.write(make_header())
    for account in accounts:
        ofxfile.write(make_message_start(account, mindate, maxdate))

        account_transactions = (t for t in transactions if t['account'] == account)
        for trns in account_transactions:
            ofxfile.write(make_transaction(trns))

        ofxfile.write(make_message_end())

    ofxfile.write(make_footer())

def parse_arguments():
    parser = argparse.ArgumentParser(prog='ing2ofx', description="""
                                     This program converts ING (www.ing.nl) CSV files to OFX format.
                                     The default output filename is the input filename.
                                     """)

    parser.add_argument('csvfile', help='A csvfile to process')
    parser.add_argument('-s, --split', dest='split',
                        help='Split by month', action='store_true', default=False)
    parser.add_argument('-o, --outfile', dest='outfile',
                        help='Output filename', default=None)
    parser.add_argument('-d, --directory', dest='dir',
                        help='Directory to store output, default is ./ofx', default='ofx')
    return parser.parse_args()
    
def main():
    args = parse_arguments()
    transactions = read_csv_file(args.csvfile, args.split)

    output_files = []
    for month in sorted(transactions.keys()):
        output_file = open_output(args, month)
        output_files.append(output_file)
        with open(output_file, 'w') as ofxfile:
            write_ofx_file(transactions[month], ofxfile)

    # print some statistics:
    print "Transactions: " + str(sum(len(t) for t in transactions.values()))
    print "Input:        " + args.csvfile
    print "Output(s):    " + ",".join(output_files)


if __name__ == "__main__":
    main()
