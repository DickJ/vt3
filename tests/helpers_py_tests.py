from app import helpers
import config


def test_is_valid_number():
    """
    Not the most robust test, but it will do for now
    """
    valid_numbers = ['8505555555', '18505555555', '(850)555-5555',
                     '1(850)555-5555', '850.555.5555']
    invalid_numbers = ['(123)555-5555', '34-567-8912', '555-5555']
    for num in valid_numbers:
        if not helpers.is_valid_number(num):
            return False
    for num in invalid_numbers:
        if helpers.is_valid_number(num):
            return False

    return True

def test_sign_up_user():
    passes_test = False

    conn, cur = helpers.get_db_conn_and_cursor({'PG_URL': config.PG_URL})
    phone = '+17085555555'
    provider = 'verizon'
    lname = 'Doe'
    fname = 'John'
    confcode = 11111111111111111111111111111111111111

    helpers.sign_up_user(cur, phone, provider, lname, fname, confcode)
    conn.commit()

    cur.execute('SELECT phone, fname, lname, provider FROM unverified WHERE phone=%s;', [phone])
    if cur.fetchall() == [(phone, fname, lname, provider)]:
        passes_test = True
    cur.execute('DELETE FROM unverified WHERE phone = %s;', [phone])

    conn.commit()
    cur.close()
    conn.close()

    return passes_test


if __name__ == '__main__':
    tests = [test_sign_up_user]

    for test in tests:
        try:
            if test():
                print(test.__name__ + ": Passed")
            else:
                print(test.__name__ + ": Failed")
        except Exception as e:
            print(test.__name__ + ": Failed with exception\n")
            print(e)