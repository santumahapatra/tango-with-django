# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from rango.models import Category, Page
from rango.forms import CategoryForm, UserForm, UserProfileForm, PageForm

def encode_url(str):
  return str.replace(' ', '_')

def decode_url(str):
  return str.replace('_', ' ')

def index(request):
  request.session.set_test_cookie()
  context = RequestContext(request)

  category_list = Category.objects.order_by('-name')[:5]
  context_dict = {'categories': category_list}

  for category in category_list:
    category.url = category.name.replace(' ', '_')

  return render_to_response('rango/index.html', context_dict, context)

def category(request, category_name_url):
  context = RequestContext(request)

  category_name = category_name_url.replace('_', ' ')

  context_dict = {'category_name': category_name}

  try:
    category = Category.objects.get(name=category_name)
    pages = Page.objects.filter(category=category)
    context_dict['pages'] = pages
    context_dict['category'] = category
  except Category.DoesNotExist:
    pass

  return render_to_response('rango/category.html', context_dict, context)

def add_category(request):
  context = RequestContext(request)

  if request.method == 'POST':
    form = CategoryForm(request.POST)

    if form.is_valid():
      form.save(commit=True)

      return index(request)
    else:
      print form.errors

  else:
    form = CategoryForm()

  return render_to_response('rango/add_category.html', {'form': form}, context)

def register(request):
  if request.session.test_cookie_worked():
    print ">>>>> TEST COOKIE WORKED!"
    request.session.delete_test_cookie()
  context = RequestContext(request)
  registered = False

  if request.method == 'POST':
    user_form = UserForm(data=request.POST)
    profile_form = UserProfileForm(data=request.POST)

    if user_form.is_valid() and profile_form.is_valid():
      user = user_form.save()
      user.set_password(user.password)
      user.save()

      profile = profile_form.save(commit=False)
      profile.user = user

      if 'picture' in request.FILES:
        profile.picture = request.FILES['picture']

      profile.save()

      registered = True

    else:
      print user_form.errors, profile_form.errors

  else:
    user_form = UserForm()
    profile_form = UserProfileForm()

  return render_to_response(
    'rango/register.html',
    {'user_form':user_form, 'profile_form':profile_form, 'registered':registered},
    context)

def user_login(request):
  context = RequestContext(request)

  if request.method == 'POST':
    username = request.POST['username']
    password = request.POST['password']

    user = authenticate(username=username, password=password)

    if user:
      if user.is_active:
        login(request, user)
        return HttpResponseRedirect('/rango/')
      else:
        return HttpResponse("Your Rango account is disabled.")
    else:
      print "Invalid login details: {0} {1}".format(username, password)
      return HttpResponse("Invalid login details supplied.")

  else:
    return render_to_response('rango/login.html', {}, context)

@login_required
def restricted(request):
  context = RequestContext(request)  
  return render_to_response('rango/restricted.html', {}, context)

@login_required
def user_logout(request):
  logout(request)
  return HttpResponseRedirect('/rango/')

@login_required
def add_page(request, category_name_url):
  context = RequestContext(request)

  category_name = decode_url(category_name_url)
  if request.method == 'POST':
    form = PageForm(request.POST)

    if form.is_valid():
      # This time we cannot commit straight away.
      # Not all fields are automatically populated!
      page = form.save(commit=False)

      # Retrieve the associated Category object so we can add it.
      cat = Category.objects.get(name=category_name)
      page.category = cat

      # Also, create a default value for the number of views.
      page.views = 0

      # With this, we can then save our new model instance.
      page.save()

      # Now that the page is saved, display the category instead.
      return category(request, category_name)
    else:
      print form.errors
  else:
    form = PageForm()

  return render_to_response( 'rango/add_page.html', 
    {'category_name_url': category_name_url, 'category_name': category_name, 'form': form}, 
    context)