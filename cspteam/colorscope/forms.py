from django import forms

class ImageForm(forms.Form):
    docfile = forms.FileField()
