from app import helpers


def test_is_valid_number():
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
    v_conf_code = 11111111111111111111111111111111111111
    inv_conf_code = 22222222222222222222222222222222222222
    valid = []
    invalid = []

    for i in valid:
        pass
    for i in invalid:
        pass

    # DELETE TEST USERS


if __name__ == '__main__':
    tests = [test_is_valid_number]

    for test in tests:
        try:
            if test():
                print(test.__name__ + ": Passed")
            else:
                print(test.__name__ + ": Failed")
        except Exception as e:
            print(test.__name__ + ": Failed with exception\n")
            print(e)