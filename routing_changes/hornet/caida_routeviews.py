#!/usr/bin/env python3

import datetime
import gzip
import logging
import re
import urllib.request

from bs4 import BeautifulSoup

from util import ExponentialBackoff

BASE_URL = "http://data.caida.org/datasets/routing/routeviews-prefix2as/{}/{}"

PFX2AS_FILENAME_RE =\
    re.compile(".*routeviews-rv2-([0-9]+)-([0-9]+)\.pfx2as.gz", re.IGNORECASE)

def best_pfx2as_url(dt, future_permissible=True):
    links_to_consider = list()

    # Consider pfx2as files from previous, current, and next month
    year = dt.year
    month = dt.month

    yyyy_mm_to_consider = list()
    yyyy_mm_to_consider.append(prev_year_month(year, month))
    yyyy_mm_to_consider.append((year, month))
    yyyy_mm_to_consider.append(next_year_month(year, month))

    for y, m in yyyy_mm_to_consider:
        url = BASE_URL.format(y, month_str(m))
        links_to_consider.extend(pfx2as_links_on_page(url))

    names_with_deltas = map(lambda x: (x, dt - pfx2as_filename_datetime(x)),
                            links_to_consider)

    if not future_permissible:
        names_with_deltas = filter(lambda x: x[1].total_seconds() >= 0,
                                   names_with_deltas)

    names_with_deltas = list(names_with_deltas)
    if len(names_with_deltas) == 0:
        return None

    best_url =\
        min(names_with_deltas, key=lambda x: abs(x[1].total_seconds()))[0]

    return best_url

@ExponentialBackoff
def dl_pfx2as_closest_to_datetime(dt, future_permissible=True):

    best_url = best_pfx2as_url(dt, future_permissible)

    logging.info("Using pfx2as file <{}> for datetime {}".format(best_url, dt))

    with urllib.request.urlopen(best_url) as f:
        data = f.read()

    decompressed_data = gzip.decompress(data).decode('utf-8')

    return decompressed_data

def is_pfx2as_filename(filename):
    return PFX2AS_FILENAME_RE.match(filename) is not None

def month_str(month):
    return "0{}".format(month) if month < 10 else str(month)

def next_year_month(year, month):
    if month == 12:
        return year + 1, 1
    else:
        return year, month + 1

def pfx2as_filename_datetime(pfx2as_filename):
    match_obj = PFX2AS_FILENAME_RE.match(pfx2as_filename)
    yyyy_mm_dd = match_obj.group(1)
    hh_mm = match_obj.group(2)
    dt = datetime.datetime.strptime("{}T{}".format(yyyy_mm_dd, hh_mm),
                                    "%Y%m%dT%H%M")
    return dt.replace(tzinfo=datetime.timezone.utc)

@ExponentialBackoff
def pfx2as_links_on_page(url):
    pfx2as_links = []
    if url[-1] != '/':
        url += '/'

    with urllib.request.urlopen(url) as page:
        page_contents = page.read().decode('utf-8')

    soup = BeautifulSoup(page_contents, 'html.parser')

    for link in soup.find_all('a'):
        if is_pfx2as_filename(link.get('href')):
            pfx2as_links.append(url + link.get('href'))

    return pfx2as_links

def prev_year_month(year, month):
    if month == 1:
        return year - 1, 12
    else:
        return year, month - 1
