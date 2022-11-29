#!/usr/bin/python
import errno
import os
import sys
from getpass import getpass
from sys import exit
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from webdriver_manager.core.utils import ChromeType
from texttable import Texttable
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

if not os.path.exists('data'):
    os.makedirs('data')

from functions import *


def terminal(argc):
    if argc[1] == 'setup':
        if (len(argc) < 4) or (len(argc) >= 4 and (argc[3].upper() != "PLACEMENT" and argc[3].upper() != 'INTERNSHIP')):
            print("Usage: cdcauto setup [roll_number] [PLACEMENT/INTERNSHIP]")
            exit()
        a, i = argc[2:]
        a.upper()
        if os.path.exists('data/secret.key'):
            while True:
                confirm = input(
                    'Are you sure to save the new credentials? This action is not undoable and will delete all records of current user. (yes/no) : ')
                confirm.lower()
                if confirm == 'yes':
                    break
                else:
                    exit()
        print("Fetching questions...")
        st = set()
        while True:
            r = requests.post('https://erp.iitkgp.ac.in/SSOAdministration/getSecurityQues.htm', data={'user_id': a})
            if r.text == 'FALSE':
                print("Roll Number seems incorrect!")
                exit()
            else:
                st.add(r.text)
            if len(st) == 3:
                break
        print("Fill your IIT KGP ERP Login Credentials. Don't worry, it's secure!")
        b = getpass("Password: ")
        qs = list(st)
        arr = []
        for j in range(0, 3):
            arr.append(qs[j])
            arr.append(getpass(f'{qs[j]} '))
        c, d, e, f, g, h = arr
        browser_select = 'CHROME'
        print("Select your browser: \n1. Chrome - default (1)\n2. Firefox (2)\n3. Edge (3)\n4. Brave(4)\n5. Chromium(5)")
        while True:
            browser_select = input('Your Input: ')
            if browser_select in ['1', '2', '3', '4', '5']:
                if browser_select == '1':
                    browser_select = 'CHROME'
                elif browser_select == '2':
                    browser_select = 'FIREFOX'
                elif browser_select == '3':
                    browser_select = 'EDGE'
                elif browser_select == '4':
                    browser_select = 'BRAVE'
                elif browser_select == '5':
                    browser_select = 'CHROMIUM'
                break
        setup(a, b, c, d, e, f, g, h, i, browser_select)
        print("Two files: secret.key, data.db are created to directory data. Tampering this may cause data loss.")
    else:
        if not os.path.exists('data/secret.key') or not os.path.exists('data/data.db'):
            print("It seems you haven't completed the setup!")
            print("Use: cdcauto setup [roll_number] [PLACEMENT/INTERNSHIP]")
            exit()
        if argc[1] == 'login' or argc[1] == 'update':
            cred = creds()
            print("Please Wait...")
            options = Options()
            options.page_load_strategy = 'normal'
            if cred[-1] == 'FIREFOX':
                driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()))
            elif cred[-1] == 'EDGE':
                driver = webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()))
            elif cred[-1] == 'BRAVE':
                driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager(chrome_type=ChromeType.BRAVE).install()))
            elif cred[-1] == 'CHROMIUM':
                driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()))
            else:
                driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
            login(driver, cred)
            if argc[1] == 'login':
                while True:
                    q = input("Stop program by pressing q: ")
                    if q.lower() == 'q':
                        exit()
            elif argc[1] == 'update':
                time.sleep(2)
                close_window = True
                if '-w' in argc:
                    close_window = False
                    argc.remove('-w')
                try:
                    updates = cdc_update(driver, cred[-2], close_window)
                except:
                    print("Oops, Something went wrong. Please try again!")
                    exit()
                pipe = os.popen('less', 'w')
                t1 = Texttable(max_width=110)
                t2 = Texttable(max_width=110)
                t1.add_rows(updates['companies'])
                t2.add_rows(updates['notices'])
                output = "Companies with approaching deadline: \n\n" + t1.draw() \
                         + "\n\n Notices: \n \n" + t2.draw()
                pipe.write(output)
                sys.stdout.write('\x1b[2K')
                pipe.close()
                if not close_window:
                    while True:
                        q = input("Stop program by pressing q: ")
                        if q.lower() == 'q':
                            exit()
        else:
            ud = []
            if argc[1] == 'unread':
                ud = unread()
            elif argc[1] == 'notices':
                ud = notices()
            elif argc[1] == 'applied':
                ud = applied()
            elif argc[1] == 'profiles':
                ud = profiles()
            elif argc[1] == 'search':
                key_type = 'company'
                search_type = 'companies'
                all_data = False
                if '-a' in argc:
                    all_data = True
                    argc.remove('-a')
                if '-n' in argc:
                    search_type = 'noticeboard'
                    argc.remove('-n')
                if '-c' in argc or '-r' in argc:
                    if '-r' in argc:
                        key_type = 'profile'
                        argc.remove('-r')
                    else:
                        argc.remove('-c')

                if len(argc) < 3:
                    print("Usage: cdcauto search [-n:if search for notices][key_type(optional): -c(default), "
                          "-r (role)] [key/keys]")
                    exit()

                ud = search(argc[2:], key_type, search_type, all_data)
            elif argc[1] == 'set':
                if len(argc) < 3:
                    print("Usage: cdcauto set [Company ID]")
                    exit()
                company_id = int(argc[2])
                columns = ['other_steps', 'test_time', 'importance', 'test_rating', 'ppt_date', 'ppt_attended',
                           'shortlisted', 'interview_date']
                column_values = {'other_steps': 0, 'test_time': 'DD-MM-YYYY HH:MM',
                                 'importance': ['HIGH', 'NORMAL', 'LOW'],
                                 'test_rating': {
                                     0: "Missed",
                                     1: "Not Yet!",
                                     2: 'Hard for me',
                                     3: 'Generally Hard',
                                     4: 'Did somehow',
                                     5: 'Generally Easy',
                                     6: 'Easy for me'
                                 }, 'ppt_date': 'DD-MM-YYYY HH:MM', 'ppt_attended': [True, False],
                                 'shortlisted': [True, False], 'interview_date': 'DD-MM-YYYY HH:MM'}
                while True:
                    print(
                        """Select the attribute: \n1. Other Steps (1)\n2. Test Schedule (2)\n3. Importance (3)\n4. Test Rating (4)\n5. PPT Schedule (5)\n6. PPT Attended (6)\n7. Shortlisted (7)\n8. Interview Date (8)""")
                    cancel = False
                    while True:

                        try:
                            column = input(
                                f"""Input integer in 1-{len(columns)} (c to exit): """)
                            if column == 'c':
                                if len(ud):
                                    cancel = True
                                    break
                                else:
                                    print("Quitting, bye!")
                                    exit()
                            column = int(column)
                        except ValueError:
                            print("Input should be an integer in range 1-6")
                            continue
                        column -= 1
                        if column < len(columns):
                            break
                        print("Input should be in the range 1 - 6!")

                    if cancel:
                        break

                    prompt = ''
                    value_type = ''
                    if isinstance(column_values[columns[column]], dict):
                        prompt = "Permissible Input Values: \n"
                        for a in column_values[columns[column]]:
                            prompt += f'{a + 1}. {column_values[columns[column]][a]} ({a + 1})\n'
                        prompt += 'Your Input: '
                        value_type = 'dict'
                    elif isinstance(column_values[columns[column]], list):
                        prompt = "Permissible Input Values: \n"
                        for i, a in enumerate(column_values[columns[column]]):
                            prompt += f'{i + 1}. {str(a)} ({i + 1})\n'
                        prompt += 'Your Input: '
                        value_type = 'list'
                    elif isinstance(column_values[columns[column]], str):
                        prompt = f"Your Input (format {column_values[columns[column]]}): "
                        value_type = 'str'
                    else:
                        value_type = ''
                        prompt = "Your Input: "

                    while True:
                        value = input(prompt)
                        if value_type == 'dict' and value.isnumeric():
                            value = int(value)
                            if value in column_values[columns[column]].keys():
                                value = list(column_values[columns[column]].keys())[value - 1]
                                break
                        elif value_type == 'list' and value.isnumeric():
                            value = int(value)
                            if value < len(column_values[columns[column]]):
                                value = column_values[columns[column]][value-1]
                                break
                        elif value_type == 'str':
                            try:
                                datetime.strptime(value, '%d-%m-%Y %H:%M')
                                value = value.strip() + ":00"
                                v, value = value.split(" ")
                                v1 = "-".join(v.split('-')[::-1])
                                value = v1 + " " + value
                                datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                                break
                            except ValueError:
                                print("Input Schedule should be on the format DD-MM-YYYY HH:MM")
                                continue
                        else:
                            value = value.strip()
                            break
                        print("Invalid Input! Try Again.")

                    ud = update(company_id, columns[column], value)
            elif argc[1] == 'test' or argc[1] == 'ppt' or argc[1] == 'deadline' or argc[1] == 'interview':
                error = False
                pivot = "application_deadline"
                buffer = 0
                if len(argc) < 3:
                    print(
                        "Usage: cdcauto deadline/ppt/test/interview [today/tomorrow/yesterday/n: -2, 0, 1, 2...(means in n days)]")
                    exit()

                if argc[1] == 'test':
                    pivot = "test_time"
                elif argc[1] == 'ppt':
                    pivot = "ppt_date"
                elif argc[1] == 'interview':
                    pivot = "interview_date"
                elif argc[1] == 'deadline':
                    pivot = "application_deadline"
                else:
                    print(
                        "Usage: cdcauto deadline/ppt/test/interview [today/tomorrow/yesterday/n: -2, 0, 1, 2...(means in n days)]")
                    exit()

                if argc[2] == 'today':
                    buffer = 1
                elif argc[2] == 'tomorrow':
                    buffer = 2
                elif argc[2] == 'yesterday':
                    buffer = 0
                else:
                    if argc[2].lstrip("-").isnumeric():
                        buffer = int(argc[2])+1
                    else:
                        print(
                            "Usage: cdcauto deadline/ppt/test/interview [today/tomorrow/yesterday/n: -2, 0, 1, 2...(means in n days)]")
                        exit()

                ud = filter_by_date(pivot, buffer)
            elif argc[1] == 'show':
                if len(argc) < 3:
                    print("Usage: cdcauto set [Company ID]")
                    exit()
                if not argc[2].isnumeric():
                    print("Usage: cdcauto set [Company ID]")
                    exit()
                company_id = int(argc[2])
                ud = show(company_id)

            else:
                print(f"Oops, Unable to recognize the command : {argc[1]}\n")
                exit()

            if len(ud) > 1:
                pipe = os.popen('less', 'w')
                t = Texttable(max_width=110)
                t.add_rows(ud)
                pipe.write(t.draw())
                pipe.close()
            else:
                print("No relevant content available. Kindly try updating!")


try:
    argv = [x.lower() for x in sys.argv]
    if len(argv) < 2:
        print("Usage: cdcauto [command] [arguments]")
        exit()
    # if argv[1] == '-i':
    #     print("\n\tCDC AUTO\n")
    #     while True:
    #         print("$ ")
    #         c = sys.stdin.readline().strip()
    #         args = [None]
    #         args.extend(c.split(' '))
    #         terminal(args)
    # else:
    terminal(argv)
except KeyboardInterrupt:
    print("\nQuitting, Bye!")
except sqlite3.OperationalError:
    print("\nOops, setup is found missing!")
    print("Use: cdcauto setup [roll_number] [PLACEMENT/INTERNSHIP]")
except IOError as e:
    if e.errno == errno.EPIPE:
        pass
except ValueError:
    print("\nOops, wrong input. Quitting!")
