#!/usr/bin/env python

import sys
import re


functional_files_extensions = ['php','asp','aspx','asmx','soap','do','action']
functional_files_pathes = ['api','soap','graphql','rest']

def replace_literals(s):
	test = s
	while True:
		match = re.search('\`[^\`]*\`',test)
		if match is None:
			break
		inner = match.group()
		subst = re.sub('\$\{[^\}]*\}','<param>',inner).replace('`','"')
		test=test.replace(inner,subst)
	return test

def parse_api_url(js_string):
	result = ''
	s = js_string.strip()
	is_in_string = True
	start = s.find('"')
	end = -1
	if start != 0:
		result = '<param>'
	rest_string = s[start+1:]
	while True:
		if is_in_string:
			end = rest_string.find('"')
			result += rest_string[:end]
			if end+1==len(rest_string):
				break
			rest_string=rest_string[end+1:]
			is_in_string=False
		else:
			start = rest_string.find('"')
			if '+' in rest_string[:start] or 'concat' in rest_string[:start]:
				result += '<param>'
			if start == -1:
				break
			else:
				rest_string=rest_string[start+1:]
				is_in_string=True
	return result

def get_apis(data):
	regexp_funcs = '(\.get|\.post|\.put|\.patch|\.delete|[^\w]fetch|\.getJSON|[^\w]ky|[^\w]reqwest)\(\s*'
	regexp_url = 'url:\s*'
	
	stop_symbols_funcs = [')',',']
	stop_symbols_url = [',','}']
	
	flags_funcs = 0
	flags_url = re.IGNORECASE

	results = []
	for regexp,stop_symbols,flags in zip([regexp_funcs,regexp_url],
											   [stop_symbols_funcs,stop_symbols_url],
											   [flags_funcs,flags_url]):
		for match in re.finditer(regexp,data,flags):
			# Если у нас идет {, то это другой случай, на интересуют только строки
			current = match.end()
			#print (data[current])
			if data[current]=='{':
				continue
			is_in_string=False
			open_string_char = ''
			opened_parenthesis = 0
			while True:
				if not is_in_string and opened_parenthesis==0:
					if data[current] in stop_symbols:
						break
				if is_in_string:
					if data[current]==open_string_char:
						#string closed
						is_in_string=False
						open_string_char = ''
						current+=1
						continue
					elif data[current] == '\\':
						current+=2
						continue
					else:
						current+=1
						continue
				else:
					if data[current]=='(':
						opened_parenthesis+=1
					elif data[current]==')':
						opened_parenthesis-=1
					current+=1
					continue
			result=(data[match.end():current])			
			results.append(result)
	# должна быть хотя бы одна кавычка
	l = filter(lambda x: re.search('("|\'|`)',x) is not None,results)
	#должен быть хотя бы один / или .
	l = filter(lambda x: re.search('(\/|\.)',x) is not None,l)
	#заменим кавычки
	l = map(lambda x: x.replace('\'','"'),l)
	# заменить `xxxx/${ID}/xxx` на "xxxx/<param>/xxx"
	l = [replace_literals(s) for s in l]
	# спарсим именно ссылочки из строк
	apis =[parse_api_url(s) for s in l]
	#уберем те, что начинаются с <param> а потом не имеют /, т.к. это не API.
	apis = filter(lambda x: re.match('<param>($|[^\/])',x) is None,apis)
	return list(apis)

regex_str = r"""
  (?:"|')                               # Start newline delimiter
  (
    ((?:[a-zA-Z]{1,10}://|//)           # Match a scheme [a-Z]*1-10 or //
    [^"'/]{1,}\.                        # Match a domainname (any character + dot)
    [a-zA-Z]{2,}[^"']{0,})              # The domainextension and/or path
    |
    ((?:/|\.\./|\./)                    # Start with /,../,./
    [^"'><,;| *()(%%$^/\\\[\]]          # Next character can't be...
    [^"'><,;|()]{1,}/                   # Rest of the characters can't be
    [^"'><,;|()]{1,})                   # At least 2 `/`
    |
    ([a-zA-Z0-9_\-/]{1,}/               # Relative endpoint with /
    [a-zA-Z0-9_\-/]{1,}/                # Resource name
    [a-zA-Z0-9_\-/]{1,}                 # At least 2`/`
    \.(?:[a-zA-Z]{1,4}|action)          # Rest + extension (length 1-4 or action)
    (?:[\?|#][^"|']{0,}|))              # ? or # mark with parameters
    |
    ([a-zA-Z0-9_\-/]{1,}/               # REST API (no extension) with /
    [a-zA-Z0-9_\-/]{2,}/                 # Proper REST endpoints usually have 3+ chars
    [a-zA-Z0-9_\-/]{2,}/                # At least 2 `/`
    (?:[\?|#][^"|']{0,}|))              # ? or # mark with parameters
    |
    ([a-zA-Z0-9_\-]{1,}                 # filename
    \.(?:%s)        # . + extension
    (?:[\?|#][^"|']{0,}|))              # ? or # mark with parameters
  )
  (?:"|')                               # End newline delimiter
"""%('|'.join(functional_files_extensions))
regex = re.compile(regex_str, re.VERBOSE)
bad_extensions = ['.svg','.jpg','.gif','.png','.jpeg','.txt','.js','.swf','.woff','.css']

def get_regexp_apis(data):
	#применим регулярку
    links = [x[0] for x in re.findall(regex,data)]
    #уберем все то заканчивается на bad_extensions, т.к. это не API
    #print ('regexp_apis ',links)
    return list(filter(lambda x: sum([x.endswith(ext) for ext in bad_extensions])==0,links))

def main():
	if len(sys.argv)<2:
		print ('extractor.py <filename.js>')
		exit(1)
	data = open(sys.argv[1]).read()
	print ("Clever search:")
	print (get_apis(data))
	print ("Regexp:")
	print (get_regexp_apis(data))


if __name__ == '__main__':
	main()