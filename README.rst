=======
ing2ofx
=======
Intro
-----
The intent of this script is to convert ing (www.ing.nl) csv files to ofx files 
that can be read by a program like GnuCash (www.gucash.org).

This script is adapted from pb2ofx.pl Copyright 2008, 2009, 2010 Peter Vermaas,
originally found at http://blog.maashoek.nl/2009/07/gnucash-en-internetbankieren/ 
which is now offline and then simplified and reworked from the original Python version.

The ofx specification can be downloaded from http://www.ofx.net/

A tutorial on how to keep your bank records in GnuCash can be read on:
http://www.chmistry.nl/financien/beginnen-met-boekhouden-in-gnucash/

Usage - command line:
---------------------
::
    usage: ing2ofx [-h] [-s, --split] [-o, --outfile OUTFILE]
                   [-d, --directory DIR]
                   csvfile

    This program converts ING (www.ing.nl) CSV files to OFX format. The default
    output filename is the input filename.

    positional arguments:
      csvfile               A csvfile to process

    optional arguments:
      -h, --help            show this help message and exit
      -s, --split           Split by month
      -o, --outfile OUTFILE
                            Output filename
      -d, --directory DIR   Directory to store output, default is ./ofx

It runs both with Python 3 and 2.7

Output
------
An ofx file converted from the csv file (default in the folder ./ofx), if
you specify -s a seperate csv file for every month is created; this can be
useful if you want to import a lot piece by piece, Gnucash learns after
each import, so doing all at once is a lot of manual assigning.


::
   Transactions: 21
   Input:        NL99INGB0001234567_01-11-2018_31-11-2018.csv
   Output(s):    ofx/NL99INGB0001234567_01-11-2018_31-11-2018.ofx
