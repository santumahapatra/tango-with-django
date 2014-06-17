# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from datetime import datetime

from rango.models import Category, Page
from rango.forms import CategoryForm, UserForm, UserProfileForm, PageForm

def encode_url(str):
  return str.replace(' ', '_')

def decode_url(str):
  return str.replace('_', ' ')

def get_category_list(max_results=0, starts_with=''):
  cat_list = []
  if starts_with:
    cat_list = Category.objects.filter(name__startswith=starts_with)
  else:
    cat_list = Category.objects.all()

  if max_results > 0:
    if len(cat_list) > max_results:
      cat_list = cat_list[:max_results]

  for cat in cat_list:
    cat.url = encode_url(cat.name)

  return cat_list

def index(request):
  context = RequestContext(request)

  category_list = Category.objects.order_by('-name')[:5]
  context_dict = {'categories': category_list}

  cat_list = get_category_list()
  context_dict['cat_list'] = cat_list

  for category in category_list:
    category.url = category.name.replace(' ', '_')

  page_list = Page.objects.order_by('-views')[:5]
  context_dict['pages'] = page_list

  if request.session.get('last_visit'):
    last_visit_time = request.session.get('last_visit')
    visits = request.session.get('visits', 0)

    if (datetime.now() - datetime.strptime(last_visit_time[:-7], "%Y-%m-%d %H:%M:%S")).days > 0:
      request.session['visits'] = visits+1
      request.session['last_visit'] = str(datetime.now())

  else:
    request.session['last_visit'] = str(datetime.now())
    request.session['visits'] = 1

  return render_to_response('rango/index.html', context_dict, context)

def about(request):
  context = RequestContext(request)
  cat_list = get_category_list()
  context_dict = {}
  context_dict['cat_list'] = cat_list

  if request.session.get('visits'):
    count = request.session.get('visits')
  else:
    count = 0

  context_dict['visits'] = count
  
  return render_to_response('rango/about.html', context_dict, context)

def category(request, category_name_url):
  context = RequestContext(request)
  cat_list = get_category_list()
  category_name = category_name_url.replace('_', ' ')

  context_dict = {'cat_list': cat_list, 'category_name': category_name}

  try:
    category = Category.objects.get(name=category_name)
    pages = Page.objects.filter(category=category).order_by('-views')
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

@login_required
def profile(request):
  context = RequestContext(request)
  cat_list = get_category_list()
  context_dict = {'cat_list': cat_list}
  u = User.objects.get(username=request.user)

  try:
    up = UserProfile.objects.get(user=u)
  except:
    up = None

  context_dict['user'] = u
  context_dict['userprofile'] = up
  return render_to_response('rango/profile.html', context_dict, context)

def track_url(request):
  context = RequestContext(request)
  page_id = None
  url = "/rango/"
  if request.method == 'GET':
    if 'page_id' in request.GET:
      page_id = request.GET['page_id']
      try:
        page = Page.objects.get(id=page_id)
        page.views = page.views + 1
        page.save()
        url = page.url
      except:
        pass
  return redirect(url)

@login_required
def like_category(request):
  context = RequestContext(request)
  cat_id = None
  if request.method == 'GET':
    cat_id = request.GET['category_id']

  likes = 0
  if cat_id:
    category = Category.objects.get(id=int(cat_id))
    if category:
      likes = category.likes + 1
      category.likes = likes
      category.save()

  return HttpResponse(likes)

def suggest_category(request):
  context = RequestContext(request)
  cat_list = []
  starts_with = ''
  if request.method == 'GET':
    starts_with = request.GET['suggestion']
  else:
    starts_with = request.POST['suggestion']

  cat_list = get_category_list(8, starts_with)
  print cat_list

  for cat in cat_list:
    print cat.name

  return render_to_response('rango/category_list.html', {'cat_list': cat_list}, context)