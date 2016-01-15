from django.shortcuts import render, render_to_response
from django.http import HttpResponse
from django.template import loader
from django.views.decorators.csrf import csrf_exempt
from .forms import *


def index(request):
    template = loader.get_template('index.html')
    return HttpResponse(template.render(request))

@csrf_exempt
def upload_file(request):
    '''Simple view method for uploading an image
    '''
    if request.method == 'POST':
        form = ImageForm(request.POST, request.FILES)
        if form.is_valid() and form.is_multipart():
            save_file(request.FILES['docfile'])
            return HttpResponse('{[[0,0,100,200,3],[100,100,110,210,10],[100,100,11,21,23]]}')
        else:
            return HttpResponse('Invalid image')
    else:
        form = ImageForm()
    return render_to_response('index.html', {'form': form})

def save_file(file, path=''):
    ''' Little helper to save a file
    ''' 
    filename = file._get_name()
    fd = open('%s/%s' % ('./colorscope/images', str(path) + str(filename)), 'wb+')
    for chunk in file.chunks():
        fd.write(chunk)
    fd.close()

