from pprint import pprint

from django.forms import modelformset_factory
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


def manage_developers(request):

    developers = Developer.objects.all()

    developers_formset = modelformset_factory(Developer, form=DevForm, extra=0)

    if request.method == 'POST':
        formset = developers_formset(request.POST, request.FILES, queryset=developers)
        if formset.is_valid():
            formset.save()

        context = {
            'formset': formset,
        }

        return render(request, "manager/manage_developers.html", context)

    else:
        formset = developers_formset(queryset=developers)

        context = {
            'formset': formset,
        }

        return render(request, "manager/manage_developers.html", context)
