import unittest
from worker import main

class MainTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass


#     def test_generate_message():
#         test_data = [('PEDERSEN, KENNETH [Capt]',
#                       [(4879, 'Meetings', '08:00', '08:00', '11:00', '\xa0', 'PEDERSEN, KENNETH [Capt]', 'IP STBY', 'CONTACT FDO FOR STBY', '\xa0', 'September 1'),
#                        (4917, 'Meetings', '15:00', '15:00', '16:00', '\xa0', 'PEDERSEN, KENNETH [Capt]', 'SQUADRON PHOTO', 'SQUADRON PHOTO; 1500; FOX LINE IN FRONT OF VT-6 LINE SHACK; GREEN FLIGHT SUITS', '\xa0', 'September 1')],
#                       'IP STBY, 08:00, PEDERSEN, KENNETH [Capt], CONTACT FDO FOR STBY; SQUADRON PHOTO, 15:00, PEDERSEN, KENNETH [Capt], SQUADRON PHOTO; 1500; FOX LINE IN FRONT OF VT-6 LINE SHACK; GREEN FLIGHT SUITS'),
#                      ]
#
#         for name, data, answer in test_data:
#             #TODO Fix date
#             if main.generate_message(name, data, '') != answer:
#                 return False
#
#         return True
#
# if __name__ == '__main__':
#     tests = [test_generate_message]
#
#     for test in tests:
#         try:
#             if test():
#                 print(test.__name__ + ": Passed")
#             else:
#                 print(test.__name__ + ": Failed")
#         except Exception as e:
#             print(test.__name__ + ": Failed with exception\n")
#             print(e)