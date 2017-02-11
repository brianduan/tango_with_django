import json 
import urllib.parse # Py3
import urllib.request # Py3

def read_webhose_key():
	"""
	Reads the Webhose API key from a file called 'search.key'.
	Returns either None (no key found), or a string representing the key.
	Remember: put search.key in your .gitignore file to avoid committing it!
	"""
	# See Python Anti-Patterns - it's an awesome resource!
	# Here we are using "with" when opening files.
	# http://docs.quantifiedcode.com/python-anti-patterns/maintainability/
	webhose_api_key = None
	
	