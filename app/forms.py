from flask.ext.wtf import Form
from wtforms import StringField
from wtforms.validators import DataRequired


class SignupForm(Form):
    #phone = StringField('phone', validators=[Regexp('9 digits or 10 if the first is 1')])
    lname = StringField('lname', validators=[DataRequired()])
    fname = StringField('fname', validators=[DataRequired()])
    phone = StringField('phone', validators=[DataRequired()])
