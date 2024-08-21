from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, FileField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Optional
from flask_wtf.file import FileAllowed, FileRequired

class OrderForm(FlaskForm):
    hd_picture = FileField('HD Picture', validators=[FileRequired(), FileAllowed(['jpg', 'png'], 'Images only!')])
    include_pet = BooleanField('Include Pet')
    pet_picture = FileField('Pet Picture', validators=[Optional(), FileAllowed(['jpg', 'png'], 'Images only!')])
    gender = SelectField('Gender (for baby images)', choices=[('Male', 'Male'), ('Female', 'Female')], validators=[Optional()])
    name = StringField('Name (if required in the image)', validators=[Optional()])
    message_to_designer = TextAreaField('Message to Designer', validators=[DataRequired()])
    style = SelectField('Style', choices=[
        ('creative', 'Creative'),
        ('cinematic', 'Cinematic'),
        ('comic', 'Comic'),
        ('realistic', 'Realistic'),
        ('disney', 'Disney'),
        ('lineart', 'Lineart'),
        ('designers_touch', 'Designer\'s Touch')
    ], validators=[DataRequired()])
    submit = SubmitField('Place Order')
