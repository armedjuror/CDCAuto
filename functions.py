import itertools
from datetime import datetime, date
import os.path
from sys import exit
import time
import sqlite3
from cryptography.fernet import Fernet
from selenium.webdriver.common.by import By

ERP_LINK = "https://erp.iitkgp.ac.in/"
CDC_COMPANY_LIST_LINK = "https://erp.iitkgp.ac.in/TrainingPlacementSSO/TPStudent.jsp"
CDC_NOTICEBOARD_LINK = "https://erp.iitkgp.ac.in/TrainingPlacementSSO/Notice.jsp"
dir_name = os.path.expanduser('~') + '/.cdcauto/data'
db = sqlite3.connect(f'{dir_name}/data.db')
cursor = db.cursor()
test_ratings = {
    0: "Missed",
    1: "Not Yet!",
    2: 'Hard for me',
    3: 'Generally Hard',
    4: 'Did somehow',
    5: 'Generally Easy',
    6: 'Easy for me'
}


def create_db():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS configs (
        id INT PRIMARY KEY NOT NULL,
        roll TEXT NOT NULL,
        `password` TEXT NOT NULL,
        question1 TEXT NOT NULL,
        answer1 TEXT NOT NULL,
        question2 TEXT NOT NULL,
        answer2 TEXT NOT NULL,
        question23 TEXT NOT NULL,
        answer3 TEXT NOT NULL,
        type TEXT CHECK ( type IN ('PLACEMENT', 'INTERNSHIP') ) DEFAULT 'PLACEMENT',
        browser TEXT CHECK (browser IN ('CHROME', 'FIREFOX', 'EDGE', 'BRAVE', 'CHROMIUM')) DEFAULT 'CHROME'
        )
    """)
    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS noticeboard 
                        (
                            id INT PRIMARY KEY NOT NULL,
                            type VARCHAR(255) NOT NULL,
                            company VARCHAR(255) NOT NULL,
                            notice VARCHAR(2048) NOT NULL,
                            posted_at DATETIME NOT NULL,
                            seen BOOL DEFAULT 0,
                            uploads VARCHAR(255) DEFAULT NULL
                        )
                        """)
    cursor.execute("""
                            CREATE TABLE IF NOT EXISTS companies 
                            (
                                id INT PRIMARY KEY NOT NULL,
                                company VARCHAR(255) NOT NULL,
                                `profile` VARCHAR(255) NOT NULL,
                                CTC VARCHAR(255) NOT NULL,
                                contract BOOL DEFAULT 0,
                                application_deadline DATETIME NOT NULL,
                                other_steps TEXT DEFAULT 'Nil',
                                applied BOOL DEFAULT 0,
                                test_time DATETIME DEFAULT NULL,
                                importance  TEXT CHECK(importance IN ('HIGH','NORMAL','LOW') ) DEFAULT 'NORMAL',
                                test_rating INTEGER CHECK(test_rating IN (0, 1, 2, 3, 4, 5, 6) ) DEFAULT 1,
                                ppt_date DATETIME DEFAULT NULL,
                                ppt_attended BOOL DEFAULT 0,
                                shortlisted BOOL DEFAULT 0,
                                interview_date DATETIME DEFAULT NULL
                            )
                            """)


def setup(
        roll_no,
        password,
        question1,
        answer1,
        question2,
        answer2,
        question3,
        answer3,
        type="PLACEMENT",
        browser='CHROME'
):
    key = Fernet.generate_key()
    # print(key)
    fernet = Fernet(key)
    line1 = fernet.encrypt(f"{roll_no.strip()}".encode()).decode()
    line2 = fernet.encrypt(f"{password.strip()}".encode()).decode()
    line3 = fernet.encrypt(f"{question1.strip()}".encode()).decode()
    line4 = fernet.encrypt(f"{answer1.strip()}".encode()).decode()
    line5 = fernet.encrypt(f"{question2.strip()}".encode()).decode()
    line6 = fernet.encrypt(f"{answer2.strip()}".encode()).decode()
    line7 = fernet.encrypt(f"{question3.strip()}".encode()).decode()
    line8 = fernet.encrypt(f"{answer3.strip()}".encode()).decode()
    with open(f"{dir_name}/secret.key", "wb") as file:
        file.write(key)
        file.close()
    create_db()
    r = cursor.execute("""SELECT * FROM configs WHERE id=1""").rowcount
    if r:
        cursor.execute("""DELETE FROM configs WHERE id=1""")
        db.commit()
    cursor.execute("""
    INSERT INTO configs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) 
    """, (1, line1, line2, line3, line4, line5, line6, line7, line8, type.upper(), browser))
    db.commit()
    db.close()


def creds():
    file = open(f'{dir_name}/secret.key', 'rb')
    res = []
    a = file.read()
    fernet = Fernet(a)
    enc_creds = cursor.execute("""SELECT * FROM configs WHERE id=1""").fetchone()
    for cipher in enc_creds[1:-2]:
        res.append(fernet.decrypt(cipher).decode())
    res.append(enc_creds[-2])
    res.append(enc_creds[-1])
    return res


def login(driver, cred):
    if len(cred) == 8:
        print("Credentials Missing. So quitting!")
        exit()

    driver.get(ERP_LINK)
    username_field = driver.find_elements(By.ID, 'user_id')
    while len(username_field) == 0:
        username_field = driver.find_elements(By.ID, 'user_id')
    username_field = username_field[0]
    username_field.send_keys(cred[0])
    driver.find_element(By.ID, 'password').send_keys(cred[1])
    question_field = []
    while True:
        question_field = driver.find_elements(By.ID, 'question')
        if len(question_field) != 0:
            if question_field[0].text:
                break

    question_field = question_field[0]
    question = question_field.text.strip()
    answer = ''
    if question == cred[2]:
        answer = cred[3]
    elif question == cred[4]:
        answer = cred[5]
    elif question == cred[6]:
        answer = cred[7]
    driver.find_element(By.ID, 'answer').send_keys(answer)
    time.sleep(2)
    driver.find_element(By.ID, 'loginFormSubmitButton').click()
    return


def cdc_update(driver, type, close_window=True):
    driver.get(CDC_COMPANY_LIST_LINK)
    time.sleep(2)
    open_companies = driver.execute_script('return jq("#grid37").getGridParam("data");')
    time.sleep(2)
    driver.get(CDC_NOTICEBOARD_LINK)
    time.sleep(3)
    all_notices = driver.execute_script('return jq("#grid54").getGridParam("data")')
    if close_window:
        driver.close()
    result1 = [["Sl. No.", 'ID', 'Company', 'Role', 'CTC', 'Appln. Deadline', 'Contract', 'Interview Date']]
    printed = 0
    companies = []
    for c in open_companies:
        today = datetime.now()
        d, t = c['resumedeadline'].split(' ')
        dr = d.split('-')
        tr = t.split(":")
        deadline = datetime(int(dr[2]), int(dr[1]), int(dr[0]), int(tr[0]), int(tr[1]))
        t += ":00"
        dt = "-".join(d.split('-')[::-1]) + " " + t
        if c['interview_date_confirmed'] is not None:
            i, t = c['interview_date_confirmed'].split(' ')
            t += ":00"
            it = "-".join(i.split('-')[::-1])+ " " + t
        else:
            it = None
        ins = [
            c['_id_'],
            c['companyname'].split("'")[1],
            c['designation'].split("'")[1],
            c['ctc'],
            False if c['contract'] == 'NO' else True,
            dt,
            True if c['apply'] == 'Y' else False,
            it,
            today - deadline,
            c['resumedeadline']
        ]
        companies.append(ins)
        cursor.execute("""
            INSERT INTO companies (id, company, `profile`, CTC, contract, application_deadline, applied, interview_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?) 
            ON CONFLICT(id) DO UPDATE SET CTC=excluded.CTC, contract=excluded.contract, application_deadline=excluded.application_deadline,
            applied = excluded.applied, interview_date=excluded.interview_date""", tuple(ins[:-2]))
    db.commit()
    companies.sort(key=lambda x: x[5])
    companies = companies[::-1]
    for co in companies:
        if (-2 <= (co[-2].total_seconds() / 86400) <= 2) and (not co[6]):
            result1.append([printed + 1, co[0], co[1], co[2], co[3], co[5],
                            "(Have a contract)" if co[4] else '', co[7]])
            printed += 1
    result2 = [['Sl. No.', '[Category] - Company', 'Posted at', 'Notice']]
    printed = 0
    notices = []

    for n in all_notices:
        if n['type'] != type:
            break
        d, t = n['noticeat'].split(' ')
        t += ":00"
        dt = "-".join(d.split('-')[::-1]) + " " + t
        download = True if n['view1'].split("'")[1] == 'Download' else False

        ins = [
            n['_id_'],
            n['category'],
            n['company'],
            n['notice'].split('>')[1].split('<')[0],
            dt,
            False,
            f'https://erp.iitkgp.ac.in/TrainingPlacementSSO/AdmFilePDF.htm?type=NOTICE&{n["upload"].split("&")[1]}&id={n["_id_"]}' if download else ""
        ]
        notices.append(ins)
    notices.sort(key=lambda x: x[4])
    notices = notices[::-1]
    for ins in notices:
        if printed < 5:
            result2.append(
                [printed + 1, f'[{ins[1]}] - {ins[2]}', ins[4], f'{ins[3]}\n\n{ins[6]}'])
            ins[5] = True  # Mark Read
            printed += 1
        cursor.execute(""" 
                INSERT INTO noticeboard
                VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) 
                DO UPDATE SET notice=excluded.notice, seen=0, uploads=excluded.uploads
            """, tuple(ins))
    db.commit()
    return {'companies': result1, 'notices': result2}


def unread():
    query = """SELECT * FROM noticeboard WHERE seen=0 ORDER BY posted_at DESC"""
    data = cursor.execute(query).fetchall()
    result = [["Sl.no", "[Category] - Company", 'Posted at', 'Notice']]
    printed = 0
    for d in data:
        dt = datetime.strptime(d[4], '%Y-%m-%d %H:%M:%S')
        result.append([printed + 1, f"[{d[1]}] - {d[2]}", dt.strftime("%a %d %b %y %H:%M"), f"{d[3]}\n\n{d[-1]}"])
        cursor.execute("""UPDATE noticeboard SET seen=1 WHERE id=?""", (d[0],))
        printed += 1
    db.commit()
    return result


def notices():
    query = """SELECT * FROM noticeboard ORDER BY posted_at DESC, seen"""
    data = cursor.execute(query).fetchall()
    printed = 0
    result = [["Sl.no", "[Category] - Company", 'Posted at', 'Notice']]
    for d in data:
        dt = datetime.strptime(d[4], '%Y-%m-%d %H:%M:%S')
        result.append([printed + 1, f"[{d[1]}] - {d[2]}", dt.strftime("%a %d %b %y %H:%M"), f"{d[3]}\n\n{d[-1]}"])
        printed += 1
    return result


def applied():
    query = """SELECT * FROM companies WHERE applied=1 ORDER BY test_time, application_deadline DESC"""
    data = cursor.execute(query).fetchall()
    printed = 0
    result = [['Sl. No.', 'ID', 'Company', 'Role', 'CTC', 'Appln. Deadline', 'Other Steps', 'Test Date', 'Importance',
               'Test Rating']]
    for d in data:
        at = datetime.strptime(d[5], '%Y-%m-%d %H:%M:%S')
        if d[8] is not None:
            dt = datetime.strptime(d[8], '%Y-%m-%d %H:%M:%S')
            test_at = "Test at " + dt.strftime("%a %d %b %y %H:%M")
        else:
            test_at = "NA"
        result.append([printed + 1, d[0], d[1], d[2], d[3], at.strftime("%a %d %b %y %H:%M"), d[6], test_at, d[9],
                       test_ratings[d[10]]])
        printed += 1
    return result


def profiles():
    query = "SELECT id, company, profile, CTC, application_deadline, applied, test_time, shortlisted, interview_date FROM companies ORDER BY test_time, application_deadline DESC"
    result = [
        ['Sl. No.', 'ID', 'Company', 'Role', 'CTC', 'Appln. Deadline', 'Applied', 'Test Time',
         'Shortlisted', 'Interview Date']]
    data = cursor.execute(query).fetchall()
    printed = 0
    for d in data:
        at = datetime.strptime(d[4], '%Y-%m-%d %H:%M:%S').strftime("%a %d %b %y %H:%M") if d[4] is not None else 'NA'
        tt = datetime.strptime(d[6], '%Y-%m-%d %H:%M:%S').strftime("%a %d %b %y %H:%M") if d[6] is not None else 'NA'
        it = datetime.strptime(d[8], '%Y-%m-%d %H:%M:%S').strftime("%a %d %b %y %H:%M") if d[8] is not None else 'NA'
        result.append(
            [printed + 1, d[0], d[1], d[2], d[3], at, "Yes" if d[4] else "No", tt,
             "Yes" if d[7] else "No", it])
        printed += 1
    return result


def search(key, key_type='company', search_type='companies', all_data=False):
    key = [('%' + x + '%') for x in key]
    if search_type == 'companies':
        if all_data:
            query = "SELECT * FROM companies WHERE " + key_type + " LIKE ? ORDER BY application_deadline DESC"
            result = [
                ['ID', 'Company', 'Role', 'CTC', 'Contract', 'Appln. Deadline', 'Other Steps', 'Applied', 'Test Time',
                 'Importance', 'Test Rating', 'PPT Time', 'PPT Attended', 'Shortlisted', 'Interview Date']]
        else:
            query = "SELECT id, company, profile, CTC, application_deadline, applied, test_time, shortlisted, interview_date FROM companies WHERE " + key_type + " LIKE ? ORDER BY application_deadline DESC"
            result = [
                ['ID', 'Company', 'Role', 'CTC', 'Appln. Deadline', 'Applied', 'Test Time',
                 'Shortlisted', 'Interview Date']]
    else:
        query = "SELECT type, company, posted_at, notice FROM noticeboard WHERE notice LIKE ? ORDER BY posted_at DESC"
        result = [["Category", "Company", 'Posted at', 'Notice']]

    for k in key:
        data = cursor.execute(query, (k,)).fetchall()
        for d in data:
            result.append(list(d))
    return result


def show(company_id):
    query = "SELECT * FROM companies WHERE id=?"
    data = cursor.execute(query, (company_id,)).fetchone()
    if not data:
        print("Oops, Company not found!")
        exit()
    data = list(data)
    data[-5] = test_ratings[data[-5]]
    if data[5] is not None:
        data[5] = datetime.strptime(data[5], '%Y-%m-%d %H:%M:%S').strftime('%a %d %b %y %H:%M')
    if data[8] is not None:
        data[8] = datetime.strptime(data[8], '%Y-%m-%d %H:%M:%S').strftime('%a %d %b %y %H:%M')
    if data[11] is not None:
        data[11] = datetime.strptime(data[11], '%Y-%m-%d %H:%M:%S').strftime('%a %d %b %y %H:%M')
    if data[14] is not None:
        data[14] = datetime.strptime(data[14], '%Y-%m-%d %H:%M:%S').strftime('%a %d %b %y %H:%M')
    r = [['ID', 'Company', 'Role', 'CTC', 'Contract', 'Appln. Deadline', 'Other Steps', 'Applied', 'Test Time',
          'Importance', 'Test Rating', 'PPT Time', 'PPT Attended', 'Shortlisted', 'Interview Date'], data]
    result = [[r[0][i], r[1][i]] for i in range(len(r[0]))]
    result.insert(0, ['Property', 'Value'])
    return result


def update(company_id, column, value):
    query = f"UPDATE companies SET {column}=? WHERE id=?"
    cursor.execute(query, (value, company_id))
    db.commit()
    return show(company_id)


def filter_by_date(pivot='application_deadline', buffer=1):
    query = f"SELECT id, company, profile, CTC, contract, application_deadline, applied, test_time, shortlisted, interview_date FROM companies WHERE (JulianDay({pivot}, 'start of day') - JulianDay('now', 'start of day'))=? ORDER BY {pivot} DESC"
    data = cursor.execute(query, (buffer,)).fetchall()
    result = [['ID', 'Company', 'Role', 'CTC', 'Contract', 'Appln. Deadline', 'Applied', 'Test Time',
               'Shortlisted', 'Interview Date']]
    for d in data:
        result.append(list(d))

    return result
