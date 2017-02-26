from datetime import datetime
from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth import authenticate, login
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from rango.forms import CategoryForm
from rango.forms import PageForm
from rango.forms import UserForm, UserProfileForm
from rango.models import Category
from rango.models import Page
from rango.models import UserProfile
from rango.webhose_search import run_query

# helper function for site counter (server side cookie version)
def visitor_cookie_handler(request):
	visits = int(get_server_side_cookie(request, 'visits', '1'))
	last_visit_cookie = get_server_side_cookie(request, 'last_visit', str(datetime.now()))
	last_visit_time = datetime.strptime(last_visit_cookie[:-7], '%Y-%m-%d %H:%M:%S')
	# If it's been more than a day since the last visit...
	if (datetime.now() - last_visit_time).seconds > 0:
		visits = visits + 1
		#update the last visit cookie now that we have updated the count
		request.session['last_visit'] = str(datetime.now())
	else:
		#I think the line below is wrong from the book 
		#visits = 1
		# set the last visit cookie
		request.session['last_visit'] = last_visit_cookie
	# Update/set the visits cookie
	request.session['visits'] = visits


# A helper method
def get_server_side_cookie(request, cookie, default_val=None):
	val = request.session.get(cookie)
	if not val:
		val = default_val
	return val


# def search(request):
# 	result_list = []
# 	query = '';
# 	if request.method == 'POST':
# 		query = request.POST['query'].strip()
# 		if query:
# 			# Run our Webhose search function to get the results list!
# 			result_list = run_query(query)
# 	context_dict = {'result_list': result_list, 'query': query}
# 	return render(request, 'rango/search.html', context_dict)

def track_url(request):
	page_id = None
	if request.method == "GET":
		if 'page_id' in request.GET:
			page_id = request.GET['page_id']
			try:
				# If we can't find anything, the .get() method raises a DoesNotExist exception.
				# So the .get() method returns one model instance or raises an exception.
				page = Page.objects.get(id=page_id)
				page.views += 1
				page.save()
				return redirect(page.url)
			except Page.DoesNotExist:
				return redirect(reverse('rango:index'))				
		else:
			return redirect(reverse('rango:index'))
	return None 

def register_profile(request):
	# A boolean value for telling the template
	# whether the registration was successful.
	# Set to False initially. Code changes value to
	# True when registration succeeds.
	registered = False

	# If it's a HTTP POST, we're interested in processing form data.
	if request.method == 'POST':
		# Attempt to grab information from the raw form information.
		profile_form = UserProfileForm(data=request.POST)

		# If the form is valid...
		if profile_form.is_valid():
			# Now sort out the UserProfile instance.
			# Since we need to set the user attribute ourselves,
			# we set commit=False. This delays saving the model
			# until we're ready to avoid integrity problems.
			profile = profile_form.save(commit=False)
			# profile.user = user

			# Did the user provide a profile picture?
			# If so, we need to get it from the input form and
			# put it in the UserProfile model.
			if 'picture' in request.FILES:
				profile.picture = request.FILES['picture']

			if request.user.is_authenticated():
				profile.user = request.user
				# Now we save the UserProfile model instance.
				profile.save()
				registered = True

		else:
			# Invalid form or forms - mistakes or something else?
			# Print problems to the terminal.
			print(profile_form.errors)

	else:
		# Not a HTTP POST, so we render our form using ModelForm instance.
		# The form will be blank, ready for user input.
		profile_form = UserProfileForm()

	# Render the template depending on the context.
	return render(request, 'rango/profile_registration.html',
	{'profile_form': profile_form,
	'registered': registered}
	)

def profile(request):
	context_dict = {}
	if request.method == 'POST':
		if request.user.is_authenticated():
			request.user.username = request.POST.get("username")
			request.user.email = request.POST.get("email")
			user_profile = UserProfile.objects.get(user=request.user)
			user_profile.website = request.POST.get("website")
			if 'picture' in request.FILES:
				user_profile.picture = request.FILES['picture']
			user_profile.save()
			context_dict['username'] = request.user.username
			context_dict['email'] = request.user.email
			context_dict['website'] = user_profile.website
			context_dict['picture'] = user_profile.picture
			context_dict['user_profile'] = user_profile
			request.user.save()
		else:
			pass
	else:
		# It's a GET request
		context_dict['username'] = request.user.username
		context_dict['email'] = request.user.email
		user_profile = UserProfile.objects.get(user=request.user)
		context_dict['website'] = user_profile.website
		context_dict['picture'] = user_profile.picture
		context_dict['user_profile'] = user_profile
	return render(request, 'rango/profile.html', context_dict)

def index(request):
	#request.session.set_test_cookie()
	# Query the database for a list of ALL categories currently stored.
	# Order the categories by no. likes in descending order.
	# Retrieve the top 5 only - or all if less than 5.
	# Place the list in our context_dict dictionary
	# that will be passed to the template engine.
	category_list = Category.objects.order_by('-likes')[:5]
	page_list = Page.objects.order_by('-views')[:5]
	context_dict = {'categories': category_list, 'pages': page_list}
	
	visitor_cookie_handler(request)
	context_dict['visits'] = request.session['visits']

	# Obtain our Response object early so we can add cookie information
	response = render(request, 'rango/index.html', context_dict)

	# Call function to handle the cookies
	#visitor_cookie_handler(request, response)

	return response

def about(request):
	# if request.session.test_cookie_worked():
	# 	print("TEST COOKIE WORKED!")
	# 	request.session.delete_test_cookie()
	visitor_cookie_handler(request)
	visits = request.session.get("visits")
	context_dict = {'name': "Brian Duan", "visits": visits}
	return render(request, 'rango/about.html', context=context_dict)

def show_category(request, category_name_slug):
	# Create a context dictionary which we can pass
	# to the template rendering engine.
	context_dict = {}

	try:
		# Can we find a category name slug with the given name?
		# If we can't, the .get() method raises a DoesNotExist exception.
		# So the .get() method returns one model instance or raises an exception.
		category = Category.objects.get(slug=category_name_slug)
		
		# Retrieve all of the associated pages.
		# Note that filter() will return a list of page objects or an empty list
		pages = Page.objects.filter(category=category)
		
		# Adds our results list to the template context under name pages.
		context_dict['pages'] = pages

		# We also add the category object from
		# the database to the context dictionary.
		# We'll use this in the template to verify that the category exists.
		context_dict['category'] = category

		#handle a HTTP POST request for search functionality
		result_list = []
		query = '';
		if request.method == 'POST':
			query = request.POST['query'].strip()
			if query:
				# Run our Webhose search function to get the results list!
				result_list = run_query(query)
		context_dict['result_list'] = result_list
		context_dict['query'] = query 
		
	except Category.DoesNotExist:
		# We get here if we didn't find the specified category.
		# Don't do anything 
		# the template will display the "no category" message for us.
		context_dict['pages'] = None
		context_dict['category'] = None
		context_dict['result_list'] = None
		context_dict['query'] = None
	return render(request, 'rango/category.html', context_dict)

@login_required
def add_category(request):
	form = CategoryForm()

	#A HTTP POST?
	if request.method == 'POST':
		form = CategoryForm(request.POST)

		# Have we been provided with a valid form?
		if form.is_valid():
			# Save the new category to the database.
			form.save(commit=True)
			# Now that the category is saved
			# We could give a confirmation message
			# But since the most recent category added is on the index page
			# Then we can direct the user back to the index page.
			return index(request)
		else:
			# The supplied form contained errors -
			# just print them to the terminal.
			print(form.errors)

	# Will handle the bad form, new form, or no form supplied cases.
	# Render the form with error messages (if any).
	return render(request, 'rango/add_category.html', {'form': form})

# @login_required
def add_page(request, category_name_slug):
	try:
		category = Category.objects.get(slug=category_name_slug)
	except Category.DoesNotExist:
		category = none

	form = PageForm()
	if request.method == 'POST':
		form = PageForm(request.POST)
		if form.is_valid():
			if category:
				page = form.save(commit=False)
				page.category = category
				page.views = 0
				page.save()
			# return show_category(request, category_name_slug)
			redirect_URL = reverse('rango:show_category', kwargs={'category_name_slug':category_name_slug})
			return HttpResponseRedirect(redirect_URL)			
		else:
			print(form.errors)
	context_dict = {'form':form, 'category':category}
	return render(request, 'rango/add_page.html', context_dict)

# def register(request):
# 	# A boolean value for telling the template
# 	# whether the registration was successful.
# 	# Set to False initially. Code changes value to
# 	# True when registration succeeds.
# 	registered = False

# 	# If it's a HTTP POST, we're interested in processing form data.
# 	if request.method == 'POST':
# 		# Attempt to grab information from the raw form information.
# 		# Note that we make use of both UserForm and UserProfileForm.
# 		user_form = UserForm(data=request.POST)
# 		profile_form = UserProfileForm(data=request.POST)

# 		# If the two forms are valid...
# 		if user_form.is_valid() and profile_form.is_valid():
# 			# Save the user's form data to the database.
# 			user = user_form.save()
# 			# Now we hash the password with the set_password method.
# 			# Once hashed, we can update the user object.
# 			user.set_password(user.password)
# 			user.save()
# 			# Now sort out the UserProfile instance.
# 			# Since we need to set the user attribute ourselves,
# 			# we set commit=False. This delays saving the model
# 			# until we're ready to avoid integrity problems.
# 			profile = profile_form.save(commit=False)
# 			profile.user = user

# 			# Did the user provide a profile picture?
# 			# If so, we need to get it from the input form and
# 			#put it in the UserProfile model.
# 			if 'picture' in request.FILES:
# 				profile.picture = request.FILES['picture']

# 			# Now we save the UserProfile model instance.
# 			profile.save()
# 			# Update our variable to indicate that the template
# 			# registration was successful.
# 			registered = True

# 		else:
# 			# Invalid form or forms - mistakes or something else?
# 			# Print problems to the terminal.
# 			print(user_form.errors, profile_form.errors)

# 	else:
# 		# Not a HTTP POST, so we render our form using two ModelForm instances.
# 		# These forms will be blank, ready for user input.
# 		user_form = UserForm()
# 		profile_form = UserProfileForm()

# 	# Render the template depending on the context.
# 	return render(request, 'rango/register.html',
# 	{'user_form': user_form,
# 	'profile_form': profile_form,
# 	'registered': registered}
# 	)

# def user_login(request):
# 	# If the request is a HTTP POST, try to pull out the relevant information.
# 	if request.method == 'POST':
# 		# Gather the username and password provided by the user.
# 		# This information is obtained from the login form.
# 		# We use request.POST.get('<variable>') as opposed
# 		# to request.POST['<variable>'], because the
# 		# request.POST.get('<variable>') returns None if the
# 		# value does not exist, while request.POST['<variable>']
# 		# will raise a KeyError exception.
# 		username = request.POST.get('username')
# 		password = request.POST.get('password')
# 		# Use Django's machinery to attempt to see if the username/password
# 		# combination is valid - a User object is returned if it is.
# 		user = authenticate(username=username, password=password)
# 		# If we have a User object, the details are correct.
# 		# If None (Python's way of representing the absence of a value), no user
# 		# with matching credentials was found.
# 		if user:
# 			# Is the account active? It could have been disabled.
# 			if user.is_active:
# 				# If the account is valid and active, we can log the user in.
# 				# We'll send the user back to the homepage.
# 				login(request, user)
# 				return HttpResponseRedirect(reverse('index'))
# 			else:
# 				# An inactive account was used - no logging in!
# 				return HttpResponse("Your Rango account is disabled.")
# 		else:
# 			# Bad login details were provided. So we can't log the user in.
# 			print("Invalid login details: {0}, {1}".format(username, password))
# 			return HttpResponse("Invalid login details supplied. Username/Password no match.")

# 	# The request is not a HTTP POST, so display the login form.
# 	# This scenario would most likely be a HTTP GET.
# 	else:	
# 		# No context variables to pass to the template system, hence the
# 		# blank dictionary object...
# 		return render(request, 'rango/login.html', {})

@login_required
def restricted(request):
	# return HttpResponse("Since you're logged in, you can see this text!")
	return render(request, 'rango/restricted.html')

# Use the login_required() decorator to ensure only those logged in can access the view.
# @login_required
# def user_logout(request):
# 	# Since we know the user is logged in, we can now just log them out.
# 	logout(request)
# 	# Take the user back to the homepage.
# 	return HttpResponseRedirect(reverse('index'))

# # helper function for site counter (client cookie version). 
#It is technically not a view - does not return a response. 
# def visitor_cookie_handler(request, response):
# 	# Get the number of visits to the site.
# 	# We use the COOKIES.get() function to obtain the visits cookie.
# 	# If the cookie exists, the value returned is casted to an integer.
# 	# If the cookie doesn't exist, then the default value of 1 is used.
# 	visits = int(request.COOKIES.get('visits', '1'))
# 	last_visit_cookie = request.COOKIES.get('last_visit', str(datetime.now()))
# 	last_visit_time = datetime.strptime(last_visit_cookie[:-7], '%Y-%m-%d %H:%M:%S') 

# 	# If it's been more than a day since the last visit...
# 	if (datetime.now() - last_visit_time).days > 0:
# 		visits = visits + 1
# 		#update the last visit cookie now that we have updated the count
# 		response.set_cookie('last_visit', str(datetime.now()))

# 	else:
# 		visits = 1
# 		# set the last visit cookie
# 		response.set_cookie('last_visit', last_visit_cookie)

# 	# Update/set the visits cookie
# 	response.set_cookie('visits', visits)


