from django.shortcuts import render, redirect
from support_bot.models import Developer
from .forms import DevForm


def index(request):
    developers=Developer.objects.all()
    form = DevForm(request.POST)
    if request.method == 'POST':
        if form.is_valid():
            dev_table = form.save()
            return redirect('index')



    return render(request, "manager/index.html", {'developers': developers,"form":form})

def add_developer(request):
    if request.method == 'POST':
        form = DevForm(request.POST)
        if form.is_valid():
            dev_table = form.save()
            return redirect('index')
    else:
        form = DevForm()

    return render(request, "manager/add_developer.html", {'form': form})
