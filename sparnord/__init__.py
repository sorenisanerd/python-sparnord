#!/usr/bin/env python
# encoding: utf-8
import csv
import datetime
import logging
import os
import os.path
import time
import tempfile
import shutil
import xtest
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

LOG = logging.getLogger(__name__)

class SparNordException(Exception):
    pass

class MultipleUserAccountsException(SparNordException):
    pass

class AgreementIdRequired(SparNordException):
    pass

class UnsupportedNavigationException(SparNordException):
    pass

class AutoDownloadProfile(webdriver.FirefoxProfile):
    def __init__(self, *args, **kwargs):
        self.tmpdir = tempfile.mkdtemp()
        super(AutoDownloadProfile, self).__init__(*args, **kwargs)
        self.set_preference('browser.download.folderList', 2)
        self.set_preference('browser.download.useDownloadDir', True)
        self.set_preference('browser.download.manager.showWhenStarting', False)
        self.set_preference('browser.download.manager.showAlertOnComplete', False)
        self.set_preference('browser.download.defaultFolder', self.tmpdir)
        self.set_preference('browser.download.dir', self.tmpdir)
        self.set_preference('browser.download.lastDir', self.tmpdir)
        self.set_preference('browser.helperApps.neverAsk.saveToDisk', 'application/csv,text/csv')
        self.set_preference('plugins.click_to_play', False)
        self.set_preference('plugin.state.java', 2)

    def __del__(self):
        assert self.profile_dir.startswith('/tmp/')
        shutil.rmtree(self.profile_dir)
        assert self.tmpdir.startswith('/tmp/')
        shutil.rmtree(self.tmpdir)

class Entry(object):
    def __init__(self, entry_date, interest_date, description,
                       amount, balance): 
        self.entry_date = entry_date
        self.interest_date = interest_date
        self.description = description
        self.amount = amount
        self.balance = balance

class SparNord(object):
    FRONT_PAGE = 0
    SIMPLE_LOGIN_PAGE = 1
    AGREEMENT_CHOICE_PAGE = 2
    AGREEMENT_FRONT_PAGE = 3
    ACCOUNT_OVERVIEW_PAGE = 4
    ACCOUNT_DETAILS_PAGE = 5

    LOGIN_PAGE_URL = 'https://netbank.sparnord.dk/'

    def __init__(self, username, password, user_id=None, agreement_id=None):
        self.profile = AutoDownloadProfile()
        self.browser = self.get_browser()
        self.logged_in = False
        self.multi_aftale = False
        self.page = -1
        self.username = username
        self.password = password
        self.current_agreement = None
        self.agreement_id = agreement_id
        self.user_id = user_id
        self.xtst = None

    def get_browser(self):
        browser = webdriver.Firefox(self.profile)
        # Ting tager tid..
        browser.implicitly_wait(15)
        return browser

    def goto_frontpage(self):
        if self.page != -1:
            raise UnsupportedNavigationException('Not able to go to front page from here')

        LOG.debug("Going to front page")
        self.browser.get(self.LOGIN_PAGE_URL)
        self.page = self.FRONT_PAGE

    def goto_simple_login_page(self):
        if self.page != self.SIMPLE_LOGIN_PAGE:
            self.goto_frontpage()

            self.find_and_click_link('Log på uden')

            while len(self.browser.find_elements_by_partial_link_text('Log på med')) < 1:
                LOG.debug('Still no elem that says "Log på med..."')
                time.sleep(1)

            LOG.debug('Simple login page is up.')
            LOG.debug('Waiting 10 seconds to let the NemID applet turn up.')
            time.sleep(10)
            self.page = self.SIMPLE_LOGIN_PAGE

    def get_agreements(self):
        self.goto_agreement_choice_page()
        rows = self.browser.find_elements_by_css_selector('div.section.danid_danidlogin form table table tbody tr')
        data = rows[2:]

        tmp = []
        for row in data:
            tmp.append([td.text for td in row.find_elements_by_tag_name('td')])

        data = tmp
        if self.user_id:
            # Filter out agreements that aren't ours
            data = filter(lambda r:r[0] == self.user_id, data)
        else:
            if len(set([r[0] for r in data])) > 1:
                data = [{'user_id': r[0], 'agreement_id': r[1], 'agreement_name': r[2]} for r in data]
                raise MultipleUserAccountsException('Multiple user accounts were shown, but no ID was given: %r' % (data,))
        return [r[1] for r in data]

    def get_accounts(self):
        self.goto_account_overview()
        rows = self.browser.find_elements_by_css_selector('div.section.account_accountlist4 table tr')
        data = rows[2:]
        retval = []
        for row in data:
            val = {}
            val['regnr'], val['accountnr'], val['currency'] = row.find_element_by_css_selector('a.ftext').text.split(' ')
            val['name'] = row.find_element_by_css_selector('span.sdc-inlineedit-content').text
            retval.append(val)
        return retval

    key_event_map = {',': 'comma',
                     '.': 'period',
                     '\t': 'Tab',
                     '\n': 'Return'}

    def send_key(self, c):
        if self.xtst is None:
            self.xtst = xtest.XTest(os.environ['DISPLAY'])
        if c in self.key_event_map:
            self.xtst.fakeKeyEvent(self.key_event_map[c])
        else:
            self.xtst.fakeKeyEvent(c)

    def goto_agreement_choice_page(self):
        if self.page < self.SIMPLE_LOGIN_PAGE:
            self.goto_simple_login_page()

            for c in self.username:
                self.send_key(c)
                time.sleep(0.1)
            self.send_key('\t')
            time.sleep(0.1)
            for c in self.password:
                self.send_key(c)
                time.sleep(0.1)
            self.send_key('\n')

            time.sleep(2)

            elems = self.browser.find_elements_by_css_selector("td.tite2")
            if elems and elems[0].text == u'Vælg aftale':
                self.page = self.AGREEMENT_CHOICE_PAGE
                self.multi_aftale = True
            else:
                self.page = self.ACCOUNT_OVERVIEW_PAGE
        elif self.page > self.AGREEMENT_CHOICE_PAGE:
            if self.multi_aftale:
                self.find_and_click_link('Skift aftale')
                self.page = self.AGREEMENT_CHOICE_PAGE

    def find_and_click_link(self, partial_link_text):
        LOG.debug('Looking for a link that reads %s.' % partial_link_text)
        elems = self.browser.find_elements_by_partial_link_text(partial_link_text)
        LOG.debug('Found %d' % (len(elems),))
        elem = elems[0]
        LOG.debug('Found. Clicking it.')
        elem.click()

    def goto_account_overview(self):
        if not self.multi_aftale or (self.agreement_id and (self.agreement_id == self.current_agreement)):
            if self.page == self.ACCOUNT_OVERVIEW_PAGE:
                return
            elif self.page > self.ACCOUNT_OVERVIEW_PAGE:
                self.find_and_click_link('KONTI')
                self.page = self.ACCOUNT_OVERVIEW_PAGE
                return

        # Det her var af en eller anden grund skrøbeligt
        attempts_left = 3
        while attempts_left:
            try:
                self.goto_agreement_choice_page()
                if self.multi_aftale:
                    if not self.agreement_id:
                            raise AgreementIdRequired("You must set the agreement ID to go to the accounts overview page")
                    self.find_and_click_link(self.agreement_id)
                    self.current_agreement = self.agreement_id
                break
            except IndexError:
                if attempts_left == 1:
                    raise
                attempts_left -= 1
        self.find_and_click_link('KONTI')
        self.page = self.ACCOUNT_OVERVIEW_PAGE

    def goto_account_details(self, account):
        self.goto_account_overview()
        self.find_and_click_link(account)
        self.page = self.ACCOUNT_DETAILS_PAGE

    def get_account_info_csv(self, account, from_date=None, to_date=None):
        self.goto_account_details(account)
        if from_date or to_date:
            if from_date:
                elem = self.browser.find_elements_by_css_selector('input#activityPeriodsFrom')[0]
                elem.send_keys(from_date)
            if to_date:
                elem = self.browser.find_elements_by_css_selector('input#activityPeriodsTo')[0]
                elem.send_keys(to_date)
            imgs = self.browser.find_elements_by_css_selector('form#accountActivitiesForm a img')
            img = filter(lambda x:x.get_attribute('src').endswith('knap_ok'), imgs)[0]
            img.click()

        while len(self.browser.find_elements_by_partial_link_text('Udvidet søgning')) < 1:
            LOG.debug('Still no elem that says "Udvidet søgning"')
            time.sleep(1)

        retval = ''
        LOG.debug('Checking if there\'s a "Vis flere" link')
        if len(self.browser.find_elements_by_partial_link_text('Vis flere')) > 0:
            LOG.debug('There is! Entering the loop')
            while len(self.browser.find_elements_by_partial_link_text('Vis flere')) > 0:
                self.find_and_click_link('Eksporter')
                csvfile = os.path.join(self.profile.tmpdir, 'export.csv')
                LOG.debug('Checking to see if %s exists' % (csvfile,))
                while not os.path.exists(csvfile):
                    LOG.debug('Waiting for export.csv to turn up')
                    time.sleep(1)
                try:
                    LOG.debug("It's there now")
                    with open(csvfile, 'r') as fp:
                        retval = fp.read() + retval
                    LOG.debug("Retval is now: %s" % (retval, ))
                finally:
                    LOG.debug("Deleting it")
                    os.unlink(csvfile)
                self.find_and_click_link('Vis flere')

        self.find_and_click_link('Eksporter')
        csvfile = os.path.join(self.profile.tmpdir, 'export.csv')
        LOG.debug('Checking to see if %s exists' % (csvfile,))
        while not os.path.exists(csvfile):
            LOG.debug('Waiting for export.csv to turn up')
            time.sleep(1)
        try:
            LOG.debug("It's there now")
            with open(csvfile, 'r') as fp:
                retval = fp.read() + retval
                LOG.debug("Retval is now: %s" % (retval,))
            for row in latin1_csv_reader(retval.split("\n")):
                if not row:
                    continue
                yield Entry(parse_date(row[0]), parse_date(row[1]),
                            row[2], parse_amount(row[3]), parse_amount(row[4]))
        finally:
            os.unlink(csvfile)

    def account_list(self):
        self.goto_account_overview()
        elems = self.browser.find_elements_by_css_selector(".account_accountlist4 tr td.under a")
        retval = []
        for elem in elems:
            retval.append()
        # (REG NR, ACCOUNT NR, CURRENCY) (all strings)
        return [e.text.strip().split(' ') for e in elems]

    def __del__(self):
        self.browser.quit()

def latin1_csv_reader(f):
    for row in csv.reader(f, delimiter=';', quotechar='"'):
        yield [cell.decode('latin1') for cell in row]

def parse_date(s):
    return datetime.datetime.strptime(s, '%d-%m-%Y')

def parse_amount(s):
    return float(s.replace('.', '').replace(',', '.'))
