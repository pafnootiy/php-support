from django.shortcuts import render
from django.shortcuts import render
from django.http import HttpResponse



def index(request):
    return HttpResponse(" Тестирование !")

    # return render(request, "manager/index.html", HttpResponse)
