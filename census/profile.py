import json
import math
import operator
import requests

from collections import OrderedDict
from django.conf import settings
from .utils import get_ratio, get_division, SUMMARY_LEVEL_DICT


import logging
logging.basicConfig()
logger = logging.getLogger(__name__)


class ApiClient(object):
	def __init__(self, base_url):
		self.base_url = base_url

	def _get(self, path, params=None):
		url = self.base_url + path
		r = requests.get(url, params=params)
		data = None
		if r.status_code == 200:
			data = r.json(object_pairs_hook=OrderedDict)
		else:
			raise Exception("Error fetching data: " + r.json().get("error"))

		return data

	def get_parent_geoids(self, geoid):
		return self._get('/1.0/geo/tiger2015/{}/parents'.format(geoid))

	def get_geoid_data(self, geoid):
		return self._get('/1.0/geo/tiger2015/{}'.format(geoid))

	def get_data(self, table_ids, geo_ids, acs='latest'):
		if hasattr(table_ids, '__iter__'):
			table_ids = ','.join(table_ids)

		if hasattr(geo_ids, '__iter__'):
			geo_ids = ','.join(geo_ids)

		return self._get('/1.0/data/show/{}'.format(acs), params=dict(table_ids=table_ids, geo_ids=geo_ids))

class D3ApiClient(object):
	def __init__(self, base_url):
		self.base_url = base_url

	def _get(self, table_id, field_name, geo_ids):
		#https://services2.arcgis.com/HsXtOCMp1Nis1Ogr/arcgis/rest/services/Births_bySD_2014/FeatureServer/0/query?outFields=*&where=GEOID10%20in%20(2636660,2636630)&f=pgeojson
		url = self.base_url + '/' + table_id + '/FeatureServer/0/query?outFields=*&where='+ field_name +'%20in%20(' + geo_ids + ')&f=json'
		# using post
		r = requests.post(url)
		data = None
		if r.status_code == 200:
			data = r.json(object_pairs_hook=OrderedDict)
		else:
			raise Exception("Error fetching data: " + r.json().get("error"))

		return data

	def get_data(self, table_id, field_name, geo_ids):

		if hasattr(geo_ids, '__iter__'):
			geo_ids = ','.join(geo_ids)

		return self._get(table_id, field_name, geo_ids)


def format_d3_data(years, table_name, title, universe, denominator_column_id, fields, state_data, county_data, tract_data, county_sd_data, msa_data, school_district_data, zcta_data, d3_item_levels,
		):
	data = OrderedDict()
	# release notes
	data['release'] = OrderedDict()
	data['release']['id'] = "d3_open_data"
	data['release']['name'] = "Data Driven Detroit Open Data Portal"
	data['release']['years'] = years

	#table headings
	data['tables'] = OrderedDict()
	data['tables'][table_name] = OrderedDict()
	data['tables'][table_name]['title'] = title
	data['tables'][table_name]['universe'] = universe
	data['tables'][table_name]['denominator_column_id'] = denominator_column_id

	# column headings
	data['tables'][table_name]['columns'] = OrderedDict()

	for key, field in fields.iteritems():
		key = 'D3-' + key
		data['tables'][table_name]['columns'][key] = OrderedDict()
		data['tables'][table_name]['columns'][key]['name'] = field['name']
		data['tables'][table_name]['columns'][key]['indent'] = field['indent']

	# data and geography
	data['data'] = OrderedDict()
	data['geography'] = OrderedDict()
	for geo in d3_item_levels:
		data['geography'][geo['geoid']] = OrderedDict()
		data['geography'][geo['geoid']]['name'] = geo['display_name']
		data['data'][geo['geoid']] = OrderedDict()
		data['data'][geo['geoid']][table_name] = OrderedDict()
		data['data'][geo['geoid']][table_name]['estimate'] = OrderedDict()
		data['data'][geo['geoid']][table_name]['error'] = OrderedDict()
		if geo['sumlevel'] == '040':
			for feature in state_data['features']:
				for key, value in feature['attributes'].iteritems():
					key = 'D3-' + key
					data['data'][geo['geoid']][table_name]['estimate'][key] = value
					data['data'][geo['geoid']][table_name]['error'][key] = 0

		if geo['sumlevel'] == '050':
			for feature in county_data['features']:
				for key, value in feature['attributes'].iteritems():
					key = 'D3-' + key
					data['data'][geo['geoid']][table_name]['estimate'][key] = value
					data['data'][geo['geoid']][table_name]['error'][key] = 0

		if geo['sumlevel'] == '060':
			for feature in county_sd_data['features']:
				for key, value in feature['attributes'].iteritems():
					key = 'D3-' + key
					data['data'][geo['geoid']][table_name]['estimate'][key] = value
					data['data'][geo['geoid']][table_name]['error'][key] = 0

		if geo['sumlevel'] == '140':
			for feature in tract_data['features']:
				for key, value in feature['attributes'].iteritems():
					key = 'D3-' + key
					data['data'][geo['geoid']][table_name]['estimate'][key] = value
					data['data'][geo['geoid']][table_name]['error'][key] = 0

		if geo['sumlevel'] == '310':
			for feature in msa_data['features']:
				for key, value in feature['attributes'].iteritems():
					key = 'D3-' + key
					data['data'][geo['geoid']][table_name]['estimate'][key] = value
					data['data'][geo['geoid']][table_name]['error'][key] = 0

		if geo['sumlevel'] == '860':
			for feature in zcta_data['features']:
				for key, value in feature['attributes'].iteritems():
					key = 'D3-' + key
					data['data'][geo['geoid']][table_name]['estimate'][key] = value
					data['data'][geo['geoid']][table_name]['error'][key] = 0
		
		if geo['sumlevel'] == '950' or geo['sumlevel'] == '960' or geo['sumlevel'] == '970':
			for feature in school_district_data['features']:
				for key, value in feature['attributes'].iteritems():
					key = 'D3-' + key
					data['data'][geo['geoid']][table_name]['estimate'][key] = value
					data['data'][geo['geoid']][table_name]['error'][key] = 0


	return data

def _maybe_int(i):
	return int(i) if i else i

def percentify(val):
	return val * 100

def rateify(val):
	return val * 1000

def moe_add(moe_a, moe_b):
	# From http://www.census.gov/acs/www/Downloads/handbooks/ACSGeneralHandbook.pdf
	return math.sqrt(moe_a**2 + moe_b**2)

def moe_proportion(numerator, denominator, numerator_moe, denominator_moe):
	# From http://www.census.gov/acs/www/Downloads/handbooks/ACSGeneralHandbook.pdf
	# "Calculating MOEs for Derived Proportions" A-14 / A-15
	proportion = float(numerator) / denominator
	try:
		return math.sqrt(numerator_moe**2 - (proportion**2 * denominator_moe**2)) / float(denominator)
	except ValueError, e:
		return moe_ratio(numerator, denominator, numerator_moe, denominator_moe)

def moe_ratio(numerator, denominator, numerator_moe, denominator_moe):
	# From http://www.census.gov/acs/www/Downloads/handbooks/ACSGeneralHandbook.pdf
	# "Calculating MOEs for Derived Ratios" A-14 / A-15
	ratio = float(numerator) / denominator
	return math.sqrt(numerator_moe**2 + (ratio**2 * denominator_moe**2)) / float(denominator)

ops = {
	'+': operator.add,
	'-': operator.sub,
	'/': operator.div,
	'%': percentify,
	'%%': rateify,
}
moe_ops = {
	'+': moe_add,
	'-': moe_add,
	'/': moe_proportion,
	'%': percentify,
	'%%': rateify,
}
def value_rpn_calc(data, rpn_string):
	stack = []
	moe_stack = []
	numerator = None
	numerator_moe = None

	for token in rpn_string.split():

		if token in ops:
			b = stack.pop()
			b_moe = moe_stack.pop()

			if token in ('%', '%%'):
				# Single-argument operators
				if b is None:
					c = None
					c_moe = None
				else:
					c = ops[token](b)
					c_moe = moe_ops[token](b_moe)
			else:
				a = stack.pop()
				a_moe = moe_stack.pop()

				if a is None or b is None:
					c = None
					c_moe = None
				elif token == '/':
					# Broken out because MOE proportion needs both MOE and estimates
					# We're dealing with ratios, not pure division.
					if a == 0 or b == 0:
						c = 0
						c_moe = 0
					else:
						a = float(a)
						b = float(b)
						c = ops[token](a, b)
						c_moe = moe_proportion(a, b, a_moe, b_moe)
					numerator = a
					numerator_moe = round(a_moe, 1)
				else:
					c = ops[token](a, b)
					c_moe = moe_ops[token](a_moe, b_moe)
		elif token.startswith('B') or token.startswith('D3-'):
			c = data['estimate'][token]
			c_moe = data['error'][token]
		else:
			c = float(token)
			c_moe = float(token)
		stack.append(c)
		moe_stack.append(c_moe)

	value = stack.pop()
	error = moe_stack.pop()

	return (value, error, numerator, numerator_moe)

def build_item(name, data, parents, rpn_string):
	val = OrderedDict([('name', name),
		('values', dict()),
		('error', dict()),
		('numerators', dict()),
		('numerator_errors', dict())])

	for parent in parents:
		label = parent['relation']
		geoid = parent['geoid']
		data_for_geoid = dict(estimate={}, error={})
		for table_id, table_data in data['data'][geoid].iteritems():
			data_for_geoid['estimate'].update(table_data['estimate'])
			data_for_geoid['error'].update(table_data['error'])

		value = None
		error = None
		numerator = None
		numerator_moe = None

		if data_for_geoid:
			(value, error, numerator, numerator_moe) = value_rpn_calc(data_for_geoid, rpn_string)

		# provide 2 decimals of precision, let client decide how much to use
		if value is not None:
			value = round(value, 2)
			# if error is 'None' should it be 0?
			error = round(error, 2) if error else 0

		if numerator is not None:
			numerator = round(numerator, 2)
			numerator_moe = round(numerator_moe, 2)

		val['values'][label] = value
		val['error'][label] = error
		val['numerators'][label] = numerator
		val['numerator_errors'][label] = numerator_moe

	return val

def add_metadata(dictionary, table_id, universe, acs_release):
	val = dict(table_id=table_id,
		universe=universe,
		acs_release=acs_release,)

	dictionary['metadata'] = val

def geo_profile(geoid, acs='latest'):
	api = ApiClient(settings.API_URL)
	d3_api = D3ApiClient(settings.D3_API_URL)

	item_levels = api.get_parent_geoids(geoid)['parents']
	comparison_geoids = [level['geoid'] for level in item_levels]

	# for D3 Open Data Portal pulls
	state_geoids = []
	county_geoids = []
	county_sd_geoids = []
	tract_geoids = []
	msa_geoids = []
	school_district_geoids = []
	zcta_geoids = []
	d3_item_levels = []
	# iterate over levels and create geoids useful for d3 API
	for level in item_levels:
		#split geoid to remove the not useful part
		split_geoid = level['geoid'].split('US')
		if level['sumlevel'] == '040':
			d3_item_levels.append(level)
			state_geoids.append(split_geoid[1])
		if level['sumlevel'] == '050':
			d3_item_levels.append(level)
			county_geoids.append(split_geoid[1])
		if level['sumlevel'] == '060':
			d3_item_levels.append(level)
			county_sd_geoids.append(split_geoid[1])
		if level['sumlevel'] == '140':
			d3_item_levels.append(level)
			tract_geoids.append(split_geoid[1])
		if level['sumlevel'] == '310':
			d3_item_levels.append(level)
			msa_geoids.append(split_geoid[1])
		if level['sumlevel'] == '860':
			d3_item_levels.append(level)
			zcta_geoids.append(split_geoid[1])
		if level['sumlevel'] == '950' or level['sumlevel'] == '960' or level['sumlevel'] == '970':
			d3_item_levels.append(level)
			school_district_geoids.append(split_geoid[1])


	doc = OrderedDict([('geography', OrderedDict()),
					   ('demographics', dict()),
					   ('economics', dict()),
					   ('families', dict()),
					   ('housing', dict()),
					   ('social', dict()),])

	# get D3 data on births
	state_data = []
	county_data = []
	county_sd_data = []
	tract_data = []
	msa_data = []
	school_district_data = []
	zcta_data = []	
	if state_geoids:
		state_data = d3_api.get_data('Births_StateofMichigan_2014', 'StateID', state_geoids)

	if county_geoids:
		county_data = d3_api.get_data('Births_byCounty_2014', 'GeoID10_1', county_geoids)

	if county_sd_geoids:
		county_sd_data = d3_api.get_data('Births_byCity_2014', 'GeoID10_1', county_sd_geoids)

	if tract_geoids:
		tract_data = d3_api.get_data('Births_byTract_2014', 'GEOID10', tract_geoids)

	if msa_geoids:
		msa_data = d3_api.get_data('Births_byMSA_2014', 'GeoID10_1', msa_geoids)

	if school_district_geoids:
	 	school_district_data = d3_api.get_data('Births_bySD_2014', 'GEOID10', school_district_geoids)

	if zcta_geoids:
		zcta_data = d3_api.get_data('Births_byZCTA_2014', 'ZCTA5CE10', zcta_geoids)

	# take D3 ODP data and create structure like census_reporter structure

	fields = OrderedDict();
	fields['TotalBirths'] = OrderedDict();
	fields['TotalBirths']['name'] = "Total Births"
	fields['TotalBirths']['indent'] = 0

	fields['NonHispWhite'] = OrderedDict();
	fields['NonHispWhite']['name'] = "Non-Hispanic White Births"
	fields['NonHispWhite']['indent'] = 1

	fields['NonHispBlack'] = OrderedDict();
	fields['NonHispBlack']['name'] = "Non-Hispanic Black Births"
	fields['NonHispBlack']['indent'] = 1

	fields['NonHIspOther'] = OrderedDict();
	fields['NonHIspOther']['name'] = "Non-Hispanic Other Race Births"
	fields['NonHIspOther']['indent'] = 1

	fields['Hispanic'] = OrderedDict();
	fields['Hispanic']['name'] = "Hispanic Births"
	fields['Hispanic']['indent'] = 1

	fields['InadequatePrenatal'] = OrderedDict();
	fields['InadequatePrenatal']['name'] = "Births with Inadequate Prenatal Care"
	fields['InadequatePrenatal']['indent'] = 1

	fields['LowBirthWeight'] = OrderedDict();
	fields['LowBirthWeight']['name'] = "Low Birth Weight Births"
	fields['LowBirthWeight']['indent'] = 1

	fields['TeenMothers'] = OrderedDict();
	fields['TeenMothers']['name'] = "Births to Teen Mothers"
	fields['TeenMothers']['indent'] = 1

	data = format_d3_data("2014", "D3-Births", "Births by Race and Ethnicity and Characteristic", "Total Births", "TotalBirths", fields, state_data, county_data, tract_data, county_sd_data, msa_data, school_district_data, zcta_data, d3_item_levels,
		)
	births_dict = dict()
	doc['families']['births'] = births_dict
	births_dict['total'] = build_item('Total births', data, d3_item_levels,
		'D3-TotalBirths')
	add_metadata(births_dict['total'], 'D3-Births', 'Total births', 'D3 Open Data Portal, State of Michigan Office of Vital Statistics')

	births_race_distribution_dict = OrderedDict()
	doc['families']['births']['race_distribution'] = births_race_distribution_dict
	add_metadata(births_race_distribution_dict, 'D3-Births', 'Total Births', 'D3 Open Data Portal, State of Michigan Office of Vital Statistics')

	births_race_distribution_dict['white'] = build_item('White', data, d3_item_levels,
		'D3-NonHispWhite D3-TotalBirths / %')

	births_race_distribution_dict['black'] = build_item('Black', data, d3_item_levels,
		'D3-NonHispBlack D3-TotalBirths / %')

	births_race_distribution_dict['other'] = build_item('Other', data, d3_item_levels,
		'D3-NonHIspOther D3-TotalBirths / %')

	births_race_distribution_dict['hispanic'] = build_item('Hispanic', data, d3_item_levels,
		'D3-Hispanic D3-TotalBirths / %')

	births_by_characteristic_dict = OrderedDict()
	doc['families']['births']['by_characteristic'] = births_by_characteristic_dict
	add_metadata(births_by_characteristic_dict, 'D3-Births', 'Total Births', 'D3 Open Data Portal, State of Michigan Office of Vital Statistics')	

	births_by_characteristic_dict['InadequatePrenatal'] = build_item('Inadequate Prenatal Care', data, d3_item_levels,
		'D3-InadequatePrenatal D3-TotalBirths / %')

	births_by_characteristic_dict['LowBirthWeight'] = build_item('Low Birth Weight', data, d3_item_levels,
		'D3-LowBirthWeight D3-TotalBirths / %')

	births_by_characteristic_dict['TeenMothers'] = build_item('Teen Mothers', data, d3_item_levels,
		'D3-TeenMothers D3-TotalBirths / %')


	# get D3 data on Third grade English Language Arts and Math test results
	state_data = []
	county_data = []
	county_sd_data = []
	tract_data = []
	msa_data = []
	school_district_data = []
	zcta_data = []	
	if state_geoids:
		state_data = d3_api.get_data('StateofMichigan_ThirdGrade_ELA_MTH_Data_08032017', 'GEOID10', state_geoids)

	if county_geoids:
		county_data = d3_api.get_data('ThirdGrade_ELA_MTH_Data_byCounty_08032017', 'GEOID10', county_geoids)

	if county_sd_geoids:
		county_sd_data = d3_api.get_data('ThirdGrade_ELA_MTH_Data_byCity_08032017', 'GEOID10', county_sd_geoids)

	if tract_geoids:
		tract_data = d3_api.get_data('ThirdGrade_ELA_MTH_Data_byTract_08032017', 'GEOID10', tract_geoids)

	if msa_geoids:
		msa_data = d3_api.get_data('ThirdGrade_ELA_MTH_Data_byMSA_08032017', 'GeoID10_1', msa_geoids)

	if school_district_geoids:
	 	school_district_data = d3_api.get_data('ThirdGrade_ELA_MTH_Data_bySchoolDistrict_08032017', 'GEOID10', school_district_geoids)

	if zcta_geoids:
		zcta_data = d3_api.get_data('ThirdGrade_ELA_MTH_Data_by_Zip_08032017', 'ZCTA5CE10', zcta_geoids)


	# take D3 ODP data and create structure like census_reporter structure

	fields = OrderedDict();
	fields['MTHTotAssessed'] = OrderedDict();
	fields['MTHTotAssessed']['name'] = "Total students taking Math Assessment"
	fields['MTHTotAssessed']['indent'] = 0

	fields['MTHProf'] = OrderedDict();
	fields['MTHProf']['name'] = "Number of students who were proficient in Math"
	fields['MTHProf']['indent'] = 1

	fields['MTHPartProf'] = OrderedDict();
	fields['MTHPartProf']['name'] = "Number of students who were partially proficient in Math"
	fields['MTHPartProf']['indent'] = 1

	fields['MTHNotProf'] = OrderedDict();
	fields['MTHNotProf']['name'] = "Number of students who were not proficient in Math"
	fields['MTHNotProf']['indent'] = 1

	fields['MTHMet'] = OrderedDict();
	fields['MTHMet']['name'] = "Number of students who met or exceeded expectations in Math"
	fields['MTHMet']['indent'] = 1

	fields['MTHNotMet'] = OrderedDict();
	fields['MTHNotMet']['name'] = "Number of students who did not meet expectations in Math"
	fields['MTHNotMet']['indent'] = 1

	fields['MTHAdv'] = OrderedDict();
	fields['MTHAdv']['name'] = "Number of students who were advanced in Math"
	fields['MTHAdv']['indent'] = 1

	fields['MTHMetPct'] = OrderedDict();
	fields['MTHMetPct']['name'] = "Percentage of students who met Math expectations"
	fields['MTHMetPct']['indent'] = 1
	
	fields['ELATotAssessed'] = OrderedDict();
	fields['ELATotAssessed']['name'] = "Total students taking ELA Assessment"
	fields['ELATotAssessed']['indent'] = 0

	fields['ELAProf'] = OrderedDict();
	fields['ELAProf']['name'] = "Number of students who were proficient in ELA"
	fields['ELAProf']['indent'] = 1

	fields['ELAPartProf'] = OrderedDict();
	fields['ELAPartProf']['name'] = "Number of students who were partially proficient in ELA"
	fields['ELAPartProf']['indent'] = 1

	fields['ELANotProf'] = OrderedDict();
	fields['ELANotProf']['name'] = "Number of students who were not proficient in ELA"
	fields['ELANotProf']['indent'] = 1

	fields['ELAMet'] = OrderedDict();
	fields['ELAMet']['name'] = "Number of students who met or exceeded expectations in ELA"
	fields['ELAMet']['indent'] = 1

	fields['ELANotMet'] = OrderedDict();
	fields['ELANotMet']['name'] = "Number of students who did not meet expectations in ELA"
	fields['ELANotMet']['indent'] = 1

	fields['ELAAdv'] = OrderedDict();
	fields['ELAAdv']['name'] = "Number of students who were advanced in ELA"
	fields['ELAAdv']['indent'] = 1

	fields['ELAMetPct'] = OrderedDict();
	fields['ELAMetPct']['name'] = "Percentage of students who met ELA expectations"
	fields['ELAMetPct']['indent'] = 1

	data = format_d3_data("2017", "D3-Math-Proficiency", "Third Grade Proficiency in ELA and Math", "Total students taking Math Assessment", "MTHTotAssessed", fields, state_data, county_data, tract_data, county_sd_data, msa_data, school_district_data, zcta_data, d3_item_levels,
		)

	ela_math_dict = dict()
	doc['social']['ela_math'] = ela_math_dict

	ela_math_dict['percent_met_expectaions_in_math'] = build_item('Students who met or exceeded expectations in Math', data, d3_item_levels,
		'D3-MTHMet D3-MTHTotAssessed / %')
	add_metadata(ela_math_dict['percent_met_expectaions_in_math'], 'D3-Math-Proficiency', 'Total students taking Math Assessment', 'D3 Open Data Portal, State of Michigan Center for Educational Performance and Information')

	ela_math_dict['percent_met_expectaions_in_ela'] = build_item('Students who met or exceeded expectations in ELA', data, d3_item_levels,
		'D3-ELAMet D3-ELATotAssessed / %')
	add_metadata(ela_math_dict['percent_met_expectaions_in_ela'], 'D3-ELA-Proficiency', 'Total students taking ELA Assessment', 'D3 Open Data Portal, State of Michigan Center for Educational Performance and Information')


	ela_distribution_dict = OrderedDict()
	doc['social']['ela_distribution'] = ela_distribution_dict
	add_metadata(ela_distribution_dict, 'D3-ELA-Proficiency', 'Total students taking ELA Assessment', 'D3 Open Data Portal, State of Michigan Center for Educational Performance and Information')

	ela_distribution_dict['ELAProf'] = build_item('Proficient', data, d3_item_levels,
		'D3-ELAProf D3-ELATotAssessed / %')

	ela_distribution_dict['ELAPartProf'] = build_item('Partially proficient', data, d3_item_levels,
		'D3-ELAPartProf D3-ELATotAssessed / %')

	ela_distribution_dict['ELANotProf'] = build_item('Not proficient', data, d3_item_levels,
		'D3-ELANotProf D3-ELATotAssessed / %')

	ela_distribution_dict['ELAMet'] = build_item('Met expectations', data, d3_item_levels,
		'D3-ELAMet D3-ELATotAssessed / %')

	ela_distribution_dict['ELANotMet'] = build_item('Not met expectations', data, d3_item_levels,
		'D3-ELANotMet D3-ELATotAssessed / %')

	ela_distribution_dict['ELAAdv'] = build_item('Advanced', data, d3_item_levels,
		'D3-ELAAdv D3-ELATotAssessed / %')

	math_distribution_dict = OrderedDict()
	doc['social']['math_distribution'] = math_distribution_dict
	add_metadata(math_distribution_dict, 'D3-Math-Proficiency', 'Total students taking Math Assessment', 'D3 Open Data Portal, State of Michigan Center for Educational Performance and Information')

	math_distribution_dict['MTHProf'] = build_item('Proficient', data, d3_item_levels,
		'D3-MTHProf D3-MTHTotAssessed / %')

	math_distribution_dict['MTHPartProf'] = build_item('Partially proficient', data, d3_item_levels,
		'D3-MTHPartProf D3-MTHTotAssessed / %')

	math_distribution_dict['MTHNotProf'] = build_item('Not proficient', data, d3_item_levels,
		'D3-MTHNotProf D3-MTHTotAssessed / %')

	math_distribution_dict['MTHMet'] = build_item('Met expectations', data, d3_item_levels,
		'D3-MTHMet D3-MTHTotAssessed / %')

	math_distribution_dict['MTHNotMet'] = build_item('Not met expectations', data, d3_item_levels,
		'D3-MTHNotMet D3-MTHTotAssessed / %')

	math_distribution_dict['MTHAdv'] = build_item('Advanced', data, d3_item_levels,
		'D3-MTHAdv D3-MTHTotAssessed / %')



	# get D3 data on Graduation Rates
	state_data = []
	county_data = []
	county_sd_data = []
	tract_data = []
	msa_data = []
	school_district_data = []
	zcta_data = []	
	if state_geoids:
		state_data = d3_api.get_data('StateofMichigan_GraduationRate_07312017', 'GEOID10', state_geoids)

	if county_geoids:
		county_data = d3_api.get_data('GraduationRates_byCounty_07312017', 'GEOID10', county_geoids)

	if county_sd_geoids:
		county_sd_data = d3_api.get_data('GraduationRates_byCity_07312017', 'GEOID10', county_sd_geoids)

	if tract_geoids:
		tract_data = d3_api.get_data('GraduationRates_byTract_07312017', 'GEOID10', tract_geoids)

	if msa_geoids:
		msa_data = d3_api.get_data('GraduationRates_byMSA_07312017', 'GeoID10_1', msa_geoids)

	if school_district_geoids:
	 	school_district_data = d3_api.get_data('GraduationRates_bySchoolDistrict_07312017', 'GEOID10', school_district_geoids)

	if zcta_geoids:
		zcta_data = d3_api.get_data('GraduationRates_byZip_07312017', 'ZCTA5CE10', zcta_geoids)


	# take D3 ODP data and create structure like census_reporter structure

	fields = OrderedDict();
	fields['CohortCount'] = OrderedDict();
	fields['CohortCount']['name'] = "Number of Students"
	fields['CohortCount']['indent'] = 0

	fields['GradCount'] = OrderedDict();
	fields['GradCount']['name'] = "Number of Graduates"
	fields['GradCount']['indent'] = 1

	fields['GradRate'] = OrderedDict();
	fields['GradRate']['name'] = "Graduation Rate"
	fields['GradRate']['indent'] = 1


	data = format_d3_data("2017", "D3-Graduation-Rates", "Graduation Rate", "Total Students", "CohortCount", fields, state_data, county_data, tract_data, county_sd_data, msa_data, school_district_data, zcta_data, d3_item_levels,
		)

	graduation_dict = dict()
	doc['social']['graduation'] = graduation_dict

	graduation_dict['graduation_rate'] = build_item('Graduation Rate', data, d3_item_levels,
		'D3-GradCount D3-CohortCount / %')
	add_metadata(graduation_dict['graduation_rate'], 'D3-Graduation-Rate', 'Total number of students', 'D3 Open Data Portal, State of Michigan Center for Educational Performance and Information')



	data = api.get_data('B01001', comparison_geoids, acs)
	acs_name = data['release']['name']
	doc['geography']['census_release'] = acs_name

	def convert_geography_data(row):
		return dict(full_name=row['display_name'],
					short_name=row['simple_name'],
					sumlevel=row['sumlevel'],
					land_area=row['aland'],
					full_geoid=row['full_geoid'])

	doc['geography']['parents'] = OrderedDict()

	for item_level in item_levels:
		name = item_level['relation']
		the_geoid = item_level['geoid']
		geoid_data = api.get_geoid_data(the_geoid)['properties']

		if name == 'this':
			doc['geography'][name] = convert_geography_data(geoid_data)
			doc['geography'][name]['total_population'] = _maybe_int(data['data'][the_geoid]['B01001']['estimate']['B01001001'])
		else:
			doc['geography']['parents'][name] = convert_geography_data(geoid_data)
			doc['geography']['parents'][name]['total_population'] = _maybe_int(data['data'][the_geoid]['B01001']['estimate']['B01001001'])


	# Demographics: Total number of Children
	child_pop_dict = dict()
	doc['demographics']['child_pop'] = child_pop_dict
	child_pop_dict['total'] = build_item('Number of children under 18', data, item_levels,
		'B01001003 B01001004 + B01001005 + B01001006 + B01001027 + B01001028 + B01001029 + B01001030 +')
	add_metadata(child_pop_dict['total'], 'B01001', 'Total population', acs_name)

	# Demographics: Child Gender
	child_gender_dict = OrderedDict()
	doc['demographics']['child_gender'] = child_gender_dict
	add_metadata(child_gender_dict, 'B01001', 'Population under 18 years of age', acs_name)
	child_gender_dict['percent_male'] = build_item('Male', data, item_levels,
		'B01001003 B01001004 + B01001005 + B01001006 + B01001003 B01001004 + B01001005 + B01001006 + B01001027 + B01001028 + B01001029 + B01001030 + / %')
	child_gender_dict['percent_female'] = build_item('Female', data, item_levels,
		'B01001027 B01001028 + B01001029 + B01001030 + B01001003 B01001004 + B01001005 + B01001006 + B01001027 + B01001028 + B01001029 + B01001030 + / %')

	# Demographics: Age
	#### SODC ####
	child_age_dict = dict()
	doc['demographics']['child_age'] = child_age_dict

	child_cat_dict = OrderedDict()
	child_age_dict['distribution_by_category'] = child_cat_dict
	# this isn't the correct metadata
	add_metadata(child_age_dict['distribution_by_category'], 'B01001', 'Population under 18 years of age', acs_name)
	child_cat_dict['percent_under_5'] = build_item('Under 5', data, item_levels,
		'B01001003 B01001027 + B01001003 B01001004 + B01001005 + B01001006 + B01001027 + B01001028 + B01001029 + B01001030 + / %')
	child_cat_dict['percent_5_to_9'] = build_item('5 to 9', data, item_levels,
		'B01001004 B01001028 + B01001003 B01001004 + B01001005 + B01001006 + B01001027 + B01001028 + B01001029 + B01001030 + / %')
	child_cat_dict['percent_10_to_14'] = build_item('10 to 14', data, item_levels,
		'B01001005 B01001029 + B01001003 B01001004 + B01001005 + B01001006 + B01001027 + B01001028 + B01001029 + B01001030 + / %')
	child_cat_dict['percent_15_to_17'] = build_item('15 to 17', data, item_levels,
		'B01001006 B01001030 + B01001003 B01001004 + B01001005 + B01001006 + B01001027 + B01001028 + B01001029 + B01001030 + / %')

	age_dict = dict()
	doc['demographics']['age'] = age_dict

	cat_dict = OrderedDict()
	age_dict['distribution_by_category'] = cat_dict
	add_metadata(age_dict['distribution_by_category'], 'B01001', 'Total population', acs_name)

	cat_dict['percent_under_18'] = build_item('Under 18', data, item_levels,
		'B01001003 B01001004 + B01001005 + B01001006 + B01001027 + B01001028 + B01001029 + B01001030 + B01001001 / %')
	cat_dict['percent_18_to_64'] = build_item('18 to 64', data, item_levels,
		'B01001007 B01001008 + B01001009 + B01001010 + B01001011 + B01001012 + B01001013 + B01001014 + B01001015 + B01001016 + B01001017 + B01001018 + B01001019 + B01001031 + B01001032 + B01001033 + B01001034 + B01001035 + B01001036 + B01001037 + B01001038 + B01001039 + B01001040 + B01001041 + B01001042 + B01001043 + B01001001 / %')
	cat_dict['percent_over_65'] = build_item('65 and over', data, item_levels,
		'B01001020 B01001021 + B01001022 + B01001023 + B01001024 + B01001025 + B01001044 + B01001045 + B01001046 + B01001047 + B01001048 + B01001049 + B01001001 / %')

	pop_dict = dict()
	age_dict['distribution_by_decade'] = pop_dict
	population_by_age_total = OrderedDict()
	population_by_age_male = OrderedDict()
	population_by_age_female = OrderedDict()
	pop_dict['total'] = population_by_age_total
	add_metadata(pop_dict['total'], 'B01001', 'Total population', acs_name)
	pop_dict['male'] = population_by_age_male
	add_metadata(pop_dict['male'], 'B01001', 'Total population', acs_name)
	pop_dict['female'] = population_by_age_female
	add_metadata(pop_dict['female'], 'B01001', 'Total population', acs_name)

	population_by_age_male['0-9'] = build_item('0-9', data, item_levels,
		'B01001003 B01001004 + B01001002 / %')
	population_by_age_female['0-9'] = build_item('0-9', data, item_levels,
		'B01001027 B01001028 + B01001026 / %')
	population_by_age_total['0-9'] = build_item('0-9', data, item_levels,
		'B01001003 B01001004 + B01001027 + B01001028 + B01001001 / %')

	population_by_age_male['10-19'] = build_item('10-19', data, item_levels,
		'B01001005 B01001006 + B01001007 + B01001002 / %')
	population_by_age_female['10-19'] = build_item('10-19', data, item_levels,
		'B01001029 B01001030 + B01001031 + B01001026 / %')
	population_by_age_total['10-19'] = build_item('10-19', data, item_levels,
		'B01001005 B01001006 + B01001007 + B01001029 + B01001030 + B01001031 + B01001001 / %')

	population_by_age_male['20-29'] = build_item('20-29', data, item_levels,
		'B01001008 B01001009 + B01001010 + B01001011 + B01001002 / %')
	population_by_age_female['20-29'] = build_item('20-29', data, item_levels,
		'B01001032 B01001033 + B01001034 + B01001035 + B01001026 / %')
	population_by_age_total['20-29'] = build_item('20-29', data, item_levels,
		'B01001008 B01001009 + B01001010 + B01001011 + B01001032 + B01001033 + B01001034 + B01001035 + B01001001 / %')

	population_by_age_male['30-39'] = build_item('30-39', data, item_levels,
		'B01001012 B01001013 + B01001002 / %')
	population_by_age_female['30-39'] = build_item('30-39', data, item_levels,
		'B01001036 B01001037 + B01001026 / %')
	population_by_age_total['30-39'] = build_item('30-39', data, item_levels,
		'B01001012 B01001013 + B01001036 + B01001037 + B01001001 / %')

	population_by_age_male['40-49'] = build_item('40-49', data, item_levels,
		'B01001014 B01001015 + B01001002 / %')
	population_by_age_female['40-49'] = build_item('40-49', data, item_levels,
		'B01001038 B01001039 + B01001026 / %')
	population_by_age_total['40-49'] = build_item('40-49', data, item_levels,
		'B01001014 B01001015 + B01001038 + B01001039 + B01001001 / %')

	population_by_age_male['50-59'] = build_item('50-59', data, item_levels,
		'B01001016 B01001017 + B01001002 / %')
	population_by_age_female['50-59'] = build_item('50-59', data, item_levels,
		'B01001040 B01001041 + B01001026 / %')
	population_by_age_total['50-59'] = build_item('50-59', data, item_levels,
		'B01001016 B01001017 + B01001040 + B01001041 + B01001001 / %')

	population_by_age_male['60-69'] = build_item('60-69', data, item_levels,
		'B01001018 B01001019 + B01001020 + B01001021 + B01001002 / %')
	population_by_age_female['60-69'] = build_item('60-69', data, item_levels,
		'B01001042 B01001043 + B01001044 + B01001045 + B01001026 / %')
	population_by_age_total['60-69'] = build_item('60-69', data, item_levels,
		'B01001018 B01001019 + B01001020 + B01001021 + B01001042 + B01001043 + B01001044 + B01001045 + B01001001 / %')

	population_by_age_male['70-79'] = build_item('70-79', data, item_levels,
		'B01001022 B01001023 + B01001002 / %')
	population_by_age_female['70-79'] = build_item('70-79', data, item_levels,
		'B01001046 B01001047 + B01001026 / %')
	population_by_age_total['70-79'] = build_item('70-79', data, item_levels,
		'B01001022 B01001023 + B01001046 + B01001047 + B01001001 / %')

	population_by_age_male['80+'] = build_item('80+', data, item_levels,
		'B01001024 B01001025 + B01001002 / %')
	population_by_age_female['80+'] = build_item('80+', data, item_levels,
		'B01001048 B01001049 + B01001026 / %')
	population_by_age_total['80+'] = build_item('80+', data, item_levels,
		'B01001024 B01001025 + B01001048 + B01001049 + B01001001 / %')

	# Demographics: Sex
	sex_dict = OrderedDict()
	doc['demographics']['sex'] = sex_dict
	add_metadata(sex_dict, 'B01001', 'Total population', acs_name)
	sex_dict['percent_male'] = build_item('Male', data, item_levels,
		'B01001002 B01001001 / %')
	sex_dict['percent_female'] = build_item('Female', data, item_levels,
		'B01001026 B01001001 / %')

	data = api.get_data('B01002', comparison_geoids, acs)
	acs_name = data['release']['name']

	median_age_dict = dict()
	age_dict['median_age'] = median_age_dict
	median_age_dict['total'] = build_item('Median age', data, item_levels,
		'B01002001')
	add_metadata(median_age_dict['total'], 'B01002', 'Total population', acs_name)
	median_age_dict['male'] = build_item('Median age male', data, item_levels,
		'B01002002')
	add_metadata(median_age_dict['male'], 'B01002', 'Total population', acs_name)
	median_age_dict['female'] = build_item('Median age female', data, item_levels,
		'B01002003')
	add_metadata(median_age_dict['female'], 'B01002', 'Total population', acs_name)

	# Demographics: Race
	data = api.get_data('B03002', comparison_geoids, acs)
	acs_name = data['release']['name']

	race_dict = OrderedDict()
	doc['demographics']['race'] = race_dict
	add_metadata(race_dict, 'B03002', 'Total population', acs_name)

	race_dict['percent_white'] = build_item('White', data, item_levels,
		'B03002003 B03002001 / %')

	race_dict['percent_black'] = build_item('Black', data, item_levels,
		'B03002004 B03002001 / %')

	race_dict['percent_native'] = build_item('Native American', data, item_levels,
		'B03002005 B03002001 / %')

	race_dict['percent_asian'] = build_item('Asian', data, item_levels,
		'B03002006 B03002001 / %')

	race_dict['percent_islander'] = build_item('Pacific Islander', data, item_levels,
		'B03002007 B03002001 / %')

	race_dict['percent_other'] = build_item('Other', data, item_levels,
		'B03002008 B03002001 / %')

	race_dict['percent_two_or_more'] = build_item('Two+', data, item_levels,
		'B03002009 B03002001 / %')

	race_dict['percent_hispanic'] = build_item('Hispanic', data, item_levels,
		'B03002012 B03002001 / %')

	#### Race by age for youth ####
	#### SODC ####
	data = api.get_data(['B01001A', 'B01001B', 'B01001C', 'B01001D', 'B01001E', 'B01001F', 'B01001G', 'B01001I', 'B01001'], comparison_geoids, acs)
	acs_name = data['release']['name']
	
	child_race_grouped_under_9 = OrderedDict()
	doc['demographics']['child_race_grouped_under_9'] = child_race_grouped_under_9
	add_metadata(child_race_grouped_under_9, 'B01001', 'Population under 5 years old and 5-9 years old', acs_name)

	# Race by age under 5
	child_race_grouped_under_9['under_5'] = OrderedDict()
	child_race_grouped_under_9['under_5']['acs_release'] = acs_name
	child_race_grouped_under_9['under_5']['metadata'] = {
		'universe': 'Population under 5 years old',
		'table_id': 'B01001',
		'name': 'Under 5'
	}
	child_race_grouped_under_9['under_5']['white'] = build_item('White Under 5', data, item_levels,
		'B01001A003 B01001A018 + B01001003 B01001027 + / %')

	child_race_grouped_under_9['under_5']['black'] = build_item('Black Under 5', data, item_levels,
		'B01001B003 B01001B018 + B01001003 B01001027 + / %')

	child_race_grouped_under_9['under_5']['native'] = build_item('Native American Under 5', data, item_levels,
		'B01001C003 B01001C018 + B01001003 B01001027 + / %')

	child_race_grouped_under_9['under_5']['asian'] = build_item('Asian Under 5', data, item_levels,
		'B01001D003 B01001D018 + B01001003 B01001027 + / %')

	child_race_grouped_under_9['under_5']['islander'] = build_item('Pacific Islander Under 5', data, item_levels,
		'B01001E003 B01001E018 + B01001003 B01001027 + / %')

	child_race_grouped_under_9['under_5']['other'] = build_item('Other Under 5', data, item_levels,
		'B01001F003 B01001F018 + B01001003 B01001027 + / %')

	child_race_grouped_under_9['under_5']['two+'] = build_item('Two+ Under 5', data, item_levels,
		'B01001G003 B01001G018 + B01001003 B01001027 + / %')

	child_race_grouped_under_9['under_5']['hispanic'] = build_item('Hispanic Under 5', data, item_levels,
		'B01001I003 B01001I018 + B01001003 B01001027 + / %')

	# Race by age 5 - 9
	child_race_grouped_under_9['5_to_9'] = OrderedDict()
	child_race_grouped_under_9['5_to_9']['acs_release'] = acs_name
	child_race_grouped_under_9['5_to_9']['metadata'] = {
		'universe': 'Total population',
		'table_id': 'B01001',
		'name': '5 to 9'
	}
	child_race_grouped_under_9['5_to_9']['white'] = build_item('White 5 to 9', data, item_levels,
		'B01001A004 B01001A019 + B01001004 B01001028 + / %')

	child_race_grouped_under_9['5_to_9']['black'] = build_item('Black 5 to 9', data, item_levels,
		'B01001B004 B01001B019 + B01001004 B01001028 + / %')

	child_race_grouped_under_9['5_to_9']['native'] = build_item('Native American 5 to 9', data, item_levels,
		'B01001C004 B01001C019 + B01001004 B01001028 + / %')

	child_race_grouped_under_9['5_to_9']['asian'] = build_item('Asian 5 to 9', data, item_levels,
		'B01001D004 B01001D019 + B01001004 B01001028 + / %')

	child_race_grouped_under_9['5_to_9']['islander'] = build_item('Pacific Islander 5 to 9', data, item_levels,
		'B01001E004 B01001E019 + B01001004 B01001028 + / %')

	child_race_grouped_under_9['5_to_9']['other'] = build_item('Other 5 to 9', data, item_levels,
		'B01001F004 B01001F019 + B01001004 B01001028 + / %')

	child_race_grouped_under_9['5_to_9']['two+'] = build_item('Two+ 5 to 9', data, item_levels,
		'B01001G004 B01001G019 + B01001004 B01001028 + / %')

	child_race_grouped_under_9['5_to_9']['hispanic'] = build_item('Hispanic 5 to 9', data, item_levels,
		'B01001I004 B01001I019 + B01001004 B01001028 + / %')

	# Race by age 10 - 14
	child_race_grouped_10_to_17 = OrderedDict()
	doc['demographics']['child_race_grouped_10_to_17'] = child_race_grouped_10_to_17
	add_metadata(child_race_grouped_10_to_17, 'B01001', 'Population 10-14 years old and 15-17 years old', acs_name)

	child_race_grouped_10_to_17['10_to_14'] = OrderedDict()
	child_race_grouped_10_to_17['10_to_14']['acs_release'] = acs_name
	child_race_grouped_10_to_17['10_to_14']['metadata'] = {
		'universe': 'Total population',
		'table_id': 'B01001',
		'name': '10 to 14'
	}
	child_race_grouped_10_to_17['10_to_14']['white'] = build_item('White 10 to 14', data, item_levels,
		'B01001A005 B01001A020 + B01001005 B01001029 + / %')

	child_race_grouped_10_to_17['10_to_14']['black'] = build_item('Black 10 to 14', data, item_levels,
		'B01001B005 B01001B020 + B01001005 B01001029 + / %')

	child_race_grouped_10_to_17['10_to_14']['native'] = build_item('Native American 10 to 14', data, item_levels,
		'B01001C005 B01001C020 + B01001005 B01001029 + / %')

	child_race_grouped_10_to_17['10_to_14']['asian'] = build_item('Asian 10 to 14', data, item_levels,
		'B01001D005 B01001D020 + B01001005 B01001029 + / %')

	child_race_grouped_10_to_17['10_to_14']['islander'] = build_item('Pacific Islander 10 to 14', data, item_levels,
		'B01001E005 B01001E020 + B01001005 B01001029 + / %')

	child_race_grouped_10_to_17['10_to_14']['other'] = build_item('Other 10 to 14', data, item_levels,
		'B01001F005 B01001F020 + B01001005 B01001029 + / %')

	child_race_grouped_10_to_17['10_to_14']['two+'] = build_item('Two+ 10 to 14', data, item_levels,
		'B01001G005 B01001G020 + B01001005 B01001029 + / %')

	child_race_grouped_10_to_17['10_to_14']['hispanic'] = build_item('Hispanic 10 to 14', data, item_levels,
		'B01001I005 B01001I020 + B01001005 B01001029 + / %')

	# Race by age 15 - 17
	child_race_grouped_10_to_17['15_to_17'] = OrderedDict()
	child_race_grouped_10_to_17['15_to_17']['acs_release'] = acs_name
	child_race_grouped_10_to_17['15_to_17']['metadata'] = {
		'universe': 'Total population',
		'table_id': 'B01001',
		'name': '15 to 17'
	}

	child_race_grouped_10_to_17['15_to_17']['white'] = build_item('White 15 to 17', data, item_levels,
		'B01001A006 B01001A021 + B01001006 B01001030 + / %')

	child_race_grouped_10_to_17['15_to_17']['black'] = build_item('Black 15 to 17', data, item_levels,
		'B01001B006 B01001B021 + B01001006 B01001030 + / %')

	child_race_grouped_10_to_17['15_to_17']['native'] = build_item('Native American 15 to 17', data, item_levels,
		'B01001C006 B01001C021 + B01001006 B01001030 + / %')

	child_race_grouped_10_to_17['15_to_17']['asian'] = build_item('Asian 15 to 17', data, item_levels,
		'B01001D006 B01001D021 + B01001006 B01001030 + / %')

	child_race_grouped_10_to_17['15_to_17']['islander'] = build_item('Pacific Islander 15 to 17', data, item_levels,
		'B01001E006 B01001E021 + B01001006 B01001030 + / %')

	child_race_grouped_10_to_17['15_to_17']['other'] = build_item('Other 15 to 17', data, item_levels,
		'B01001F006 B01001F021 + B01001006 B01001030 + / %')

	child_race_grouped_10_to_17['15_to_17']['two+'] = build_item('Two+ 15 to 17', data, item_levels,
		'B01001G006 B01001G021 + B01001006 B01001030 + / %')

	child_race_grouped_10_to_17['15_to_17']['hispanic'] = build_item('Hispanic 15 to 17', data, item_levels,
		'B01001I006 B01001I021 + B01001006 B01001030 + / %')


	# Male Children: Total number of male youth
	#### SODC ####
	male_child_pop_dict = dict()
	doc['demographics']['male_child_pop'] = male_child_pop_dict
	male_child_pop_dict['total'] = build_item('Number of male children under 18', data, item_levels,
		'B01001003 B01001004 + B01001005 + B01001006 + ')
	add_metadata(male_child_pop_dict['total'], 'B01001', 'Total population', acs_name)    

	# # Male Children: Distribution of white male youth 
	# #### SODC ####
	# male_child_age_white_distribution_dict = OrderedDict()
	# doc['demographics']['male_child_age_white_distribution'] = male_child_age_white_distribution_dict
	# add_metadata(male_child_age_white_distribution_dict, 'B01001A', 'People who are White alone', acs_name)

	# male_child_age_white_distribution_dict['percent_under_5'] = build_item('Under 5', data, item_levels,
	#     'B01001A003 B01001A003 B01001A004 + B01001A005 + B01001A006 + / %')

	# male_child_age_white_distribution_dict['percent_5_to_9'] = build_item('5 to 9', data, item_levels,
	#     'B01001A004 B01001A003 B01001A004 + B01001A005 + B01001A006 + / %')

	# male_child_age_white_distribution_dict['percent_10_to_14'] = build_item('10 to 14', data, item_levels,
	#     'B01001A005 B01001A003 B01001A004 + B01001A005 + B01001A006 + / %')

	# male_child_age_white_distribution_dict['percent_15_to_17'] = build_item('15 to 17', data, item_levels,
	#     'B01001A006 B01001A003 B01001A004 + B01001A005 + B01001A006 + / %')

	# # Male Children: Distribution of black male youth
	# #### SODC #### 
	# male_child_age_black_distribution_dict = OrderedDict()
	# doc['demographics']['male_child_age_black_distribution'] = male_child_age_black_distribution_dict
	# add_metadata(male_child_age_black_distribution_dict, 'B01001B', 'People who are Black alone', acs_name)

	# male_child_age_black_distribution_dict['percent_under_5'] = build_item('Under 5', data, item_levels,
	#     'B01001B003 B01001B003 B01001B004 + B01001B005 + B01001B006 + / %')

	# male_child_age_black_distribution_dict['percent_5_to_9'] = build_item('5 to 9', data, item_levels,
	#     'B01001B004 B01001B003 B01001B004 + B01001B005 + B01001B006 + / %')

	# male_child_age_black_distribution_dict['percent_10_to_14'] = build_item('10 to 14', data, item_levels,
	#     'B01001B005 B01001B003 B01001B004 + B01001B005 + B01001B006 + / %')

	# male_child_age_black_distribution_dict['percent_15_to_17'] = build_item('15 to 17', data, item_levels,
	#     'B01001B006 B01001B003 B01001B004 + B01001B005 + B01001B006 + / %')

	# # Male Children: Distribution of Native American male youth
	# #### SODC ####
	# male_child_age_native_distribution_dict = OrderedDict()
	# doc['demographics']['male_child_age_native_distribution'] = male_child_age_native_distribution_dict
	# add_metadata(male_child_age_native_distribution_dict, 'B01001C', 'People Who Are American Indian and Alaska Native American Alone', acs_name)

	# male_child_age_native_distribution_dict['percent_under_5'] = build_item('Under 5', data, item_levels,
	#     'B01001C003 B01001C003 B01001C004 + B01001C005 + B01001C006 + / %')

	# male_child_age_native_distribution_dict['percent_5_to_9'] = build_item('5 to 9', data, item_levels,
	#     'B01001C004 B01001C003 B01001C004 + B01001C005 + B01001C006 + / %')

	# male_child_age_native_distribution_dict['percent_10_to_14'] = build_item('10 to 14', data, item_levels,
	#     'B01001C005 B01001C003 B01001C004 + B01001C005 + B01001C006 + / %')

	# male_child_age_native_distribution_dict['percent_15_to_17'] = build_item('15 to 17', data, item_levels,
	#     'B01001C006 B01001C003 B01001C004 + B01001C005 + B01001C006 + / %')

	# # Male Children: Distribution of Asian male youth
	# #### SODC ####
	# male_child_age_asian_distribution_dict = OrderedDict()
	# doc['demographics']['male_child_age_asian_distribution'] = male_child_age_asian_distribution_dict
	# add_metadata(male_child_age_asian_distribution_dict, 'B01001D', 'People Who Are Asian Alone', acs_name)

	# male_child_age_asian_distribution_dict['percent_under_5'] = build_item('Under 5', data, item_levels,
	#     'B01001D003 B01001D003 B01001D004 + B01001D005 + B01001D006 + / %')

	# male_child_age_asian_distribution_dict['percent_5_to_9'] = build_item('5 to 9', data, item_levels,
	#     'B01001D004 B01001D003 B01001D004 + B01001D005 + B01001D006 + / %')

	# male_child_age_asian_distribution_dict['percent_10_to_14'] = build_item('10 to 14', data, item_levels,
	#     'B01001D005 B01001D003 B01001D004 + B01001D005 + B01001D006 + / %')

	# male_child_age_asian_distribution_dict['percent_15_to_17'] = build_item('15 to 17', data, item_levels,
	#     'B01001D006 B01001D003 B01001D004 + B01001D005 + B01001D006 + / %')

	# # Male Children: Distribution of Pacific Islander male youth
	# #### SODC ####
	# male_child_age_islander_distribution_dict = OrderedDict()
	# doc['demographics']['male_child_age_islander_distribution'] = male_child_age_islander_distribution_dict
	# add_metadata(male_child_age_islander_distribution_dict, 'B01001E', 'People Who Are Native Hawaiian and Other Pacific Islander Alone', acs_name)

	# male_child_age_islander_distribution_dict['percent_under_5'] = build_item('Under 5', data, item_levels,
	#     'B01001E003 B01001E003 B01001E004 + B01001E005 + B01001E006 + / %')

	# male_child_age_islander_distribution_dict['percent_5_to_9'] = build_item('5 to 9', data, item_levels,
	#     'B01001E004 B01001E003 B01001E004 + B01001E005 + B01001E006 + / %')

	# male_child_age_islander_distribution_dict['percent_10_to_14'] = build_item('10 to 14', data, item_levels,
	#     'B01001E005 B01001E003 B01001E004 + B01001E005 + B01001E006 + / %')

	# male_child_age_islander_distribution_dict['percent_15_to_17'] = build_item('15 to 17', data, item_levels,
	#     'B01001E006 B01001E003 B01001E004 + B01001E005 + B01001E006 + / %')

	# # Male Children: Distribution of Other male youth
	# #### SODC ####
	# male_child_age_other_distribution_dict = OrderedDict()
	# doc['demographics']['male_child_age_other_distribution'] = male_child_age_other_distribution_dict
	# add_metadata(male_child_age_other_distribution_dict, 'B01001F', 'People Who Are Some Other Race Alone', acs_name)

	# male_child_age_other_distribution_dict['percent_under_5'] = build_item('Under 5', data, item_levels,
	#     'B01001F003 B01001F003 B01001F004 + B01001F005 + B01001F006 + / %')

	# male_child_age_other_distribution_dict['percent_5_to_9'] = build_item('5 to 9', data, item_levels,
	#     'B01001F004 B01001F003 B01001F004 + B01001F005 + B01001F006 + / %')

	# male_child_age_other_distribution_dict['percent_10_to_14'] = build_item('10 to 14', data, item_levels,
	#     'B01001F005 B01001F003 B01001F004 + B01001F005 + B01001F006 + / %')

	# male_child_age_other_distribution_dict['percent_15_to_17'] = build_item('15 to 17', data, item_levels,
	#     'B01001F006 B01001F003 B01001F004 + B01001F005 + B01001F006 + / %')

	# # Male Children: Distribution of Two or More Races male youth
	# #### SODC ####
	# male_child_age_two_or_more_distribution_dict = OrderedDict()
	# doc['demographics']['male_child_age_two_or_more_distribution'] = male_child_age_two_or_more_distribution_dict
	# add_metadata(male_child_age_two_or_more_distribution_dict, 'B01001G', 'People Who Are Two or More Races', acs_name)

	# male_child_age_two_or_more_distribution_dict['percent_under_5'] = build_item('Under 5', data, item_levels,
	#     'B01001G003 B01001G003 B01001G004 + B01001G005 + B01001G006 + / %')

	# male_child_age_two_or_more_distribution_dict['percent_5_to_9'] = build_item('5 to 9', data, item_levels,
	#     'B01001G004 B01001G003 B01001G004 + B01001G005 + B01001G006 + / %')

	# male_child_age_two_or_more_distribution_dict['percent_10_to_14'] = build_item('10 to 14', data, item_levels,
	#     'B01001G005 B01001G003 B01001G004 + B01001G005 + B01001G006 + / %')

	# male_child_age_two_or_more_distribution_dict['percent_15_to_17'] = build_item('15 to 17', data, item_levels,
	#     'B01001G006 B01001G003 B01001G004 + B01001G005 + B01001G006 + / %')

	# # Male Children: Distribution of Hispanic male youth
	# #### SODC ####
	# male_child_age_hispanic_distribution_dict = OrderedDict()
	# doc['demographics']['male_child_age_hispanic_distribution'] = male_child_age_hispanic_distribution_dict
	# add_metadata(male_child_age_hispanic_distribution_dict, 'B01001I', 'People Who Are Two or More Races', acs_name)

	# male_child_age_hispanic_distribution_dict['percent_under_5'] = build_item('Under 5', data, item_levels,
	#     'B01001I003 B01001I003 B01001I004 + B01001I005 + B01001I006 + / %')

	# male_child_age_hispanic_distribution_dict['percent_5_to_9'] = build_item('5 to 9', data, item_levels,
	#     'B01001I004 B01001I003 B01001I004 + B01001I005 + B01001I006 + / %')

	# male_child_age_hispanic_distribution_dict['percent_10_to_14'] = build_item('10 to 14', data, item_levels,
	#     'B01001I005 B01001I003 B01001I004 + B01001I005 + B01001I006 + / %')

	# male_child_age_two_or_more_distribution_dict['percent_15_to_17'] = build_item('15 to 17', data, item_levels,
	#     'B01001I006 B01001I003 B01001I004 + B01001I005 + B01001I006 + / %')

	# Male Children: Total Distribution by Age
	#### SODC ####
	male_child_age_total_distribution_dict = OrderedDict()
	doc['demographics']['male_child_age_total_distribution'] = male_child_age_total_distribution_dict
	add_metadata(male_child_age_total_distribution_dict, 'B01001', 'Population of males under 18 years of age', acs_name)

	male_child_age_total_distribution_dict['percent_under_5'] = build_item('Under 5', data, item_levels,
		'B01001003 B01001003 B01001004 + B01001005 + B01001006 + / %')

	male_child_age_total_distribution_dict['percent_5_to_9'] = build_item('5 to 9', data, item_levels,
		'B01001004 B01001003 B01001004 + B01001005 + B01001006 + / %')

	male_child_age_total_distribution_dict['percent_10_to_14'] = build_item('10 to 14', data, item_levels,
		'B01001005 B01001003 B01001004 + B01001005 + B01001006 + / %')

	male_child_age_total_distribution_dict['percent_15_to_17'] = build_item('15 to 17', data, item_levels,
		'B01001006 B01001003 B01001004 + B01001005 + B01001006 + / %')

	# Male Children: Distribution by Race
	#### SODC ####
	male_child_age_race_distribution_dict = OrderedDict()
	doc['demographics']['male_child_age_race_distribution'] = male_child_age_race_distribution_dict
	add_metadata(male_child_age_race_distribution_dict, 'B01001B', 'Population of males under 18 years of age', acs_name)

	male_child_age_race_distribution_dict['percent_white'] = build_item('White', data, item_levels,
		'B01001A003 B01001A004 + B01001A005 + B01001A006 + B01001003 B01001004 + B01001005 + B01001006 + / %')

	male_child_age_race_distribution_dict['percent_black'] = build_item('Black', data, item_levels,
		'B01001B003 B01001B004 + B01001B005 + B01001B006 + B01001003 B01001004 + B01001005 + B01001006 + / %')

	male_child_age_race_distribution_dict['percent_native'] = build_item('Native American', data, item_levels,
		'B01001C003 B01001C004 + B01001C005 + B01001C006 + B01001003 B01001004 + B01001005 + B01001006 + / %')

	male_child_age_race_distribution_dict['percent_asian'] = build_item('Asian', data, item_levels,
		'B01001D003 B01001D004 + B01001D005 + B01001D006 + B01001003 B01001004 + B01001005 + B01001006 + / %')

	male_child_age_race_distribution_dict['percent_islander'] = build_item('Pacific Islander', data, item_levels,
		'B01001E003 B01001E004 + B01001E005 + B01001E006 + B01001003 B01001004 + B01001005 + B01001006 + / %')

	male_child_age_race_distribution_dict['percent_other'] = build_item('Other', data, item_levels,
		'B01001F003 B01001F004 + B01001F005 + B01001F006 + B01001003 B01001004 + B01001005 + B01001006 + / %')

	male_child_age_race_distribution_dict['percent_two_or_more'] = build_item('Two+', data, item_levels,
		'B01001G003 B01001G004 + B01001G005 + B01001G006 + B01001003 B01001004 + B01001005 + B01001006 + / %')

	male_child_age_race_distribution_dict['percent_hispanic'] = build_item('Hispanic', data, item_levels,
		'B01001I003 B01001I004 + B01001I005 + B01001I006 + B01001003 B01001004 + B01001005 + B01001006 + / %')



	# Economics: Per-Capita Income
	data = api.get_data('B19301', comparison_geoids, acs)
	acs_name = data['release']['name']

	income_dict = dict()
	doc['economics']['income'] = income_dict

	income_dict['per_capita_income_in_the_last_12_months'] = build_item('Per capita income', data, item_levels,
		'B19301001')
	add_metadata(income_dict['per_capita_income_in_the_last_12_months'], 'B19301', 'Total population', acs_name)

	# Economics: Median Household Income
	data = api.get_data('B19013', comparison_geoids, acs)
	acs_name = data['release']['name']

	income_dict['median_household_income'] = build_item('Median household income', data, item_levels,
		'B19013001')
	add_metadata(income_dict['median_household_income'], 'B19013', 'Households', acs_name)

	# Economics: Household Income Distribution
	data = api.get_data('B19001', comparison_geoids, acs)
	acs_name = data['release']['name']

	income_distribution = OrderedDict()
	income_dict['household_distribution'] = income_distribution
	add_metadata(income_dict['household_distribution'], 'B19001', 'Households', acs_name)

	income_distribution['under_50'] = build_item('Under $50K', data, item_levels,
		'B19001002 B19001003 + B19001004 + B19001005 + B19001006 + B19001007 + B19001008 + B19001009 + B19001010 + B19001001 / %')
	income_distribution['50_to_100'] = build_item('$50K - $100K', data, item_levels,
		'B19001011 B19001012 + B19001013 + B19001001 / %')
	income_distribution['100_to_200'] = build_item('$100K - $200K', data, item_levels,
		'B19001014 B19001015 + B19001016 + B19001001 / %')
	income_distribution['over_200'] = build_item('Over $200K', data, item_levels,
		'B19001017 B19001001 / %')

	# Economics: Poverty Rate
	data = api.get_data('B17001', comparison_geoids, acs)
	acs_name = data['release']['name']

	poverty_dict = dict()
	doc['economics']['poverty'] = poverty_dict

	poverty_dict['percent_below_poverty_line'] = build_item('Persons below poverty line', data, item_levels,
		'B17001002 B17001001 / %')
	add_metadata(poverty_dict['percent_below_poverty_line'], 'B17001', 'Population for whom poverty status is determined', acs_name)

	poverty_children = OrderedDict()
	poverty_seniors = OrderedDict()
	poverty_dict['children'] = poverty_children
	add_metadata(poverty_dict['children'], 'B17001', 'Population for whom poverty status is determined', acs_name)
	poverty_dict['seniors'] = poverty_seniors
	add_metadata(poverty_dict['seniors'], 'B17001', 'Population for whom poverty status is determined', acs_name)

	poverty_children['Below'] = build_item('Children (Under 18) below poverty line', data, item_levels,
		'B17001004 B17001005 + B17001006 + B17001007 + B17001008 + B17001009 + B17001018 + B17001019 + B17001020 + B17001021 + B17001022 + B17001023 + B17001004 B17001005 + B17001006 + B17001007 + B17001008 + B17001009 + B17001018 + B17001019 + B17001020 + B17001021 + B17001022 + B17001023 + B17001033 + B17001034 + B17001035 + B17001036 + B17001037 + B17001038 + B17001047 + B17001048 + B17001049 + B17001050 + B17001051 + B17001052 + / %')
	add_metadata(poverty_children['Below'], 'B17001', 'Population for whom poverty status is determined', acs_name)	
	poverty_children['above'] = build_item('Non-poverty', data, item_levels,
		'B17001033 B17001034 + B17001035 + B17001036 + B17001037 + B17001038 + B17001047 + B17001048 + B17001049 + B17001050 + B17001051 + B17001052 + B17001004 B17001005 + B17001006 + B17001007 + B17001008 + B17001009 + B17001018 + B17001019 + B17001020 + B17001021 + B17001022 + B17001023 + B17001033 + B17001034 + B17001035 + B17001036 + B17001037 + B17001038 + B17001047 + B17001048 + B17001049 + B17001050 + B17001051 + B17001052 + / %')

	poverty_seniors['Below'] = build_item('Poverty', data, item_levels,
		'B17001015 B17001016 + B17001029 + B17001030 + B17001015 B17001016 + B17001029 + B17001030 + B17001044 + B17001045 + B17001058 + B17001059 + / %')
	poverty_seniors['above'] = build_item('Non-poverty', data, item_levels,
		'B17001044 B17001045 + B17001058 + B17001059 + B17001015 B17001016 + B17001029 + B17001030 + B17001044 + B17001045 + B17001058 + B17001059 + / %')

	# Economics: Child Poverty by age category
	poverty_children_distribution_by_age = OrderedDict()
	poverty_dict['children_distribution_by_age'] = poverty_children_distribution_by_age
	add_metadata(poverty_dict['children_distribution_by_age'], 'B17001', 'Population for whom poverty status is determined', acs_name)
	poverty_children_distribution_by_age['under_5'] = build_item('Under 5', data, item_levels,
		'B17001004 B17001018 + B17001004 B17001018 + B17001033 + B17001047 + / %')

	poverty_children_distribution_by_age['5_years'] = build_item('5', data, item_levels,
		'B17001005 B17001019 + B17001005 B17001019 + B17001034 + B17001048 + / %')

	poverty_children_distribution_by_age['6_to_11'] = build_item('6-11', data, item_levels,
		'B17001006 B17001020 + B17001006 B17001020 + B17001035 + B17001049 + / %')

	poverty_children_distribution_by_age['12_to_14'] = build_item('12-14', data, item_levels,
		'B17001007 B17001021 + B17001007 B17001021 + B17001036 + B17001050 + / %')

	poverty_children_distribution_by_age['15_years'] = build_item('15', data, item_levels,
		'B17001008 B17001022 + B17001008 B17001022 + B17001037 + B17001051 + / %')

	poverty_children_distribution_by_age['16_and_17'] = build_item('16-17', data, item_levels,
		'B17001009 B17001023 + B17001009 B17001023 + B17001038 + B17001052 + / %')

	# Economics: Public Assistance to households with children
	data = api.get_data('B09010', comparison_geoids, acs)
	acs_name = data['release']['name']

	poverty_dict['percent_receiving_public_assistance'] = build_item('Households with children (under 18) receiving SSI, cash or food/SNAP assistance', data, item_levels,
		'B09010002 B09010001 / %')
	add_metadata(poverty_dict['percent_receiving_public_assistance'], 'B09010', 'Population under 18 years in households', acs_name)

	# Economics: Poverty Status in the Past 12 Months of Families by Household Type by Educational Attainment of Householder
	data = api.get_data('B17018', comparison_geoids, acs)
	acs_name = data['release']['name']

	poverty_family_educational_attainment = OrderedDict()
	doc['economics']['poverty']['poverty_family_educational_attainment'] = poverty_family_educational_attainment
	add_metadata(poverty_family_educational_attainment, 'B17018', 'Families', acs_name)

	# Married Couples
	poverty_family_educational_attainment['married_couples'] = OrderedDict()
	poverty_family_educational_attainment['married_couples']['acs_release'] = acs_name
	poverty_family_educational_attainment['married_couples']['metadata'] = {
		'universe': 'Families',
		'table_id': 'B17018',
		'name': 'Married couples'
	}
	poverty_family_educational_attainment['married_couples']['-HS'] = build_item('Less than high school graduate', data, item_levels,
		'B17018004 B17018004 B17018021 + / %')	
	poverty_family_educational_attainment['married_couples']['HS'] = build_item('High school graduate (includes equivalency)', data, item_levels,
		'B17018005 B17018005 B17018022 + / %')	
	poverty_family_educational_attainment['married_couples']['-Coll'] = build_item('Some college, associate\'s degree', data, item_levels,
		'B17018006 B17018006 B17018023 + / %')	
	poverty_family_educational_attainment['married_couples']['Coll+'] = build_item('Bachelor\'s degree or higher', data, item_levels,
		'B17018007 B17018007 B17018024 + / %')	

	#Male Householder
	poverty_family_educational_attainment['male_householder'] = OrderedDict()
	poverty_family_educational_attainment['male_householder']['acs_release'] = acs_name
	poverty_family_educational_attainment['male_householder']['metadata'] = {
		'universe': 'Families',
		'table_id': 'B17018',
		'name': 'Male householder, no wife present'
	}
	poverty_family_educational_attainment['male_householder']['-HS'] = build_item('Less than high school graduate', data, item_levels,
		'B17018010 B17018010 B17018027 + / %')	
	poverty_family_educational_attainment['male_householder']['HS'] = build_item('High school graduate (includes equivalency)', data, item_levels,
		'B17018011 B17018011 B17018028 + / %')	
	poverty_family_educational_attainment['male_householder']['-Coll'] = build_item('Some college, associate\'s degree', data, item_levels,
		'B17018012 B17018012 B17018029 + / %')	
	poverty_family_educational_attainment['male_householder']['Coll+'] = build_item('Bachelor\'s degree or higher', data, item_levels,
		'B17018013 B17018013 B17018030 + / %')	

	#Female Householder
	poverty_family_educational_attainment['female_householder'] = OrderedDict()
	poverty_family_educational_attainment['female_householder']['acs_release'] = acs_name
	poverty_family_educational_attainment['female_householder']['metadata'] = {
		'universe': 'Families',
		'table_id': 'B17018',
		'name': 'Female householder, no husband present'
	}
	poverty_family_educational_attainment['female_householder']['-HS'] = build_item('Less than high school graduate', data, item_levels,
		'B17018015 B17018015 B17018032 + / %')	
	poverty_family_educational_attainment['female_householder']['HS'] = build_item('High school graduate (includes equivalency)', data, item_levels,
		'B17018016 B17018016 B17018033 + / %')	
	poverty_family_educational_attainment['female_householder']['-Coll'] = build_item('Some college, associate\'s degree', data, item_levels,
		'B17018017 B17018017 B17018034 + / %')	
	poverty_family_educational_attainment['female_householder']['Coll+'] = build_item('Bachelor\'s degree or higher', data, item_levels,
		'B17018018 B17018018 B17018035 + / %')	


	# Economics: Food assistance program participation
	data = api.get_data('B22002', comparison_geoids, acs)
	acs_name = data['release']['name']

	poverty_dict['percent_receiving_food_assistance'] = build_item('Households with food/SNAP assistance in the past 12 months', data, item_levels,
		'B22002002 B22002001 / %')
	add_metadata(poverty_dict['percent_receiving_food_assistance'], 'B22002', 'Households', acs_name)

	food_assistance_household_type = OrderedDict()
	doc['economics']['poverty']['food_assistance_household_type'] = food_assistance_household_type
	add_metadata(food_assistance_household_type, 'B22002', 'Households', acs_name)

	# Married Couples
	food_assistance_household_type['married_couples'] = OrderedDict()
	food_assistance_household_type['married_couples']['acs_release'] = acs_name
	food_assistance_household_type['married_couples']['metadata'] = {
		'universe': 'Households',
		'table_id': 'B22002',
		'name': 'Married couples'
	}
	food_assistance_household_type['married_couples']['With Children'] = build_item('With children under 18 years', data, item_levels,
		'B22002004 B22002001 / %')	
	food_assistance_household_type['married_couples']['W/O Children'] = build_item('No children under 18 years', data, item_levels,
		'B22002010 B22002001 / %')	

	#Male Householder
	food_assistance_household_type['male_householder'] = OrderedDict()
	food_assistance_household_type['male_householder']['acs_release'] = acs_name
	food_assistance_household_type['male_householder']['metadata'] = {
		'universe': 'Households',
		'table_id': 'B22002',
		'name': 'Male householder, no wife present'
	}
	food_assistance_household_type['male_householder']['With Children'] = build_item('With children under 18 years', data, item_levels,
		'B22002006 B22002001 / %')	
	food_assistance_household_type['male_householder']['W/O Children'] = build_item('No children under 18 years', data, item_levels,
		'B22002012 B22002001 / %')	

	#Female Householder
	food_assistance_household_type['female_householder'] = OrderedDict()
	food_assistance_household_type['female_householder']['acs_release'] = acs_name
	food_assistance_household_type['female_householder']['metadata'] = {
		'universe': 'Households',
		'table_id': 'B22002',
		'name': 'Female householder, no husband present'
	}
	food_assistance_household_type['female_householder']['With Children'] = build_item('With children under 18 years', data, item_levels,
		'B22002007 B22002001 / %')	
	food_assistance_household_type['female_householder']['W/O Children'] = build_item('No children under 18 years', data, item_levels,
		'B22002013 B22002001 / %')	


	# Economics: Employment, Mean Travel Time to Work, Means of Transportation to Work
	data = api.get_data(['B23025', 'B23027', 'B14005', 'B08006', 'B08013'], comparison_geoids, acs)
	acs_name = data['release']['name']

	employment_dict = dict()
	doc['economics']['employment'] = employment_dict

	employment_dict['unemployment_rate'] = build_item('Unemployment rate', data, item_levels,
		'B23025005 B23025003 / %')
	add_metadata(employment_dict['unemployment_rate'], 'B23025', 'Population 16 years and over', acs_name)

	employment_dict['nowork_rate'] = build_item('Persons 16-64 who have not worked in the last 12 months', data, item_levels,
		'B23027006 B23027011 + B23027016 + B23027021 + B23027026 + B23027002 B23027007 + B23027012 + B23027017 + B23027022 + / %')
	add_metadata(employment_dict['nowork_rate'], 'B23027', 'Population 16 years and over', acs_name)


	youth_school_employment_grouped = OrderedDict()
	employment_dict['youth_school_employment_grouped'] = youth_school_employment_grouped
	add_metadata(youth_school_employment_grouped, 'B14005', 'Population 16 to 19 years', acs_name)

	# repeating data temporarily to develop grouped column chart format
	youth_school_employment_grouped['enrolled'] = OrderedDict()
	youth_school_employment_grouped['enrolled']['acs_release'] = acs_name
	youth_school_employment_grouped['enrolled']['metadata'] = {
		'universe': 'Population 16 to 19 years',
		'table_id': 'C14005',
		'name': 'Enrolled'
	}
	youth_school_employment_grouped['enrolled']['male'] = build_item('Male', data, item_levels,
		'B14005003 B14005002 / %')
	youth_school_employment_grouped['enrolled']['female'] = build_item('Female', data, item_levels,
		'B14005017 B14005016 / %')

	youth_school_employment_grouped['graduated_employed'] = OrderedDict()
	youth_school_employment_grouped['graduated_employed']['acs_release'] = acs_name
	youth_school_employment_grouped['graduated_employed']['metadata'] = {
		'universe': 'Population 16 to 19 years',
		'table_id': 'B14005',
		'name': 'Employed; High school graduate'
	}
	youth_school_employment_grouped['graduated_employed']['male'] = build_item('Male', data, item_levels,
		'B14005009 B14005002 / %')
	youth_school_employment_grouped['graduated_employed']['female'] = build_item('Female', data, item_levels,
		'B14005023 B14005016 / %')

	youth_school_employment_grouped['not_graduated_employed'] = OrderedDict()
	youth_school_employment_grouped['not_graduated_employed']['acs_release'] = acs_name
	youth_school_employment_grouped['not_graduated_employed']['metadata'] = {
		'universe': 'Population 16 to 19 years',
		'table_id': 'B14005',
		'name': 'Employed; Not a high school graduate'
	}
	youth_school_employment_grouped['not_graduated_employed']['male'] = build_item('Male', data, item_levels,
		'B14005013 B14005002 / %')
	youth_school_employment_grouped['not_graduated_employed']['female'] = build_item('Female', data, item_levels,
		'B14005027 B14005016 / %')


	employment_dict['mean_travel_time'] = build_item('Mean travel time to work', data, item_levels,
		'B08013001 B08006001 B08006017 - /')
	add_metadata(employment_dict['mean_travel_time'], 'B08006, B08013', 'Workers 16 years and over who did not work at home', acs_name)

	data = api.get_data('B08006', comparison_geoids, acs)
	acs_name = data['release']['name']

	transportation_dict = OrderedDict()
	employment_dict['transportation_distribution'] = transportation_dict
	add_metadata(employment_dict['transportation_distribution'], 'B08006', 'Workers 16 years and over', acs_name)

	transportation_dict['drove_alone'] = build_item('Drove alone', data, item_levels,
		'B08006003 B08006001 / %')
	transportation_dict['carpooled'] = build_item('Carpooled', data, item_levels,
		'B08006004 B08006001 / %')
	transportation_dict['public_transit'] = build_item('Public transit', data, item_levels,
		'B08006008 B08006001 / %')
	transportation_dict['Bicycle'] = build_item('Bicycle', data, item_levels,
		'B08006014 B08006001 / %')
	transportation_dict['walked'] = build_item('Walked', data, item_levels,
		'B08006015 B08006001 / %')
	transportation_dict['other'] = build_item('Other', data, item_levels,
		'B08006016 B08006001 / %')
	transportation_dict['worked_at_home'] = build_item('Worked at home', data, item_levels,
		'B08006017 B08006001 / %')



	# Family and Economic Security: Vehicle Avaialabilty
	data = api.get_data(['B08006', 'B08014', 'B08015'], comparison_geoids, acs)
	acs_name = data['release']['name']

	employment_dict['mean_number_of_vehicles'] = build_item('Mean number of vehicles available', data, item_levels,
		'B08015001 B08006002 /')
	add_metadata(employment_dict['mean_number_of_vehicles'], 'B08006, B08015', 'Workers Whose Means of Transportation Is Car, Truck, or Van', acs_name)

	vehicle_availabilty_dict = OrderedDict()
	employment_dict['distribution_vehicle_availabilty'] = vehicle_availabilty_dict
	add_metadata(employment_dict['distribution_vehicle_availabilty'], 'B08006', 'Workers 16 years and over', acs_name)

	vehicle_availabilty_dict['No_vehicle_available'] = build_item('No vehicle available', data, item_levels,
		'B08014002 B08014001 / %')
	vehicle_availabilty_dict['1_vehicle_available'] = build_item('1 vehicle available', data, item_levels,
		'B08014003 B08014001 / %')
	vehicle_availabilty_dict['2_vehicles_available'] = build_item('2 vehicles available', data, item_levels,
		'B08014004 B08014001 / %')
	vehicle_availabilty_dict['3_vehicles_available'] = build_item('3 vehicles available', data, item_levels,
		'B08014005 B08014001 / %')
	vehicle_availabilty_dict['4_vehicles_available'] = build_item('4 vehicles available', data, item_levels,
		'B08014006 B08014001 / %')
	vehicle_availabilty_dict['5_or_more_vehicles_available'] = build_item('5+ vehicles available', data, item_levels,
		'B08014007 B08014001 / %')



	# Families: Marital Status by Sex
	data = api.get_data('B12001', comparison_geoids, acs)
	acs_name = data['release']['name']

	marital_status = OrderedDict()
	doc['families']['marital_status'] = marital_status
	add_metadata(marital_status, 'B12001', 'Population 15 years and over', acs_name)

	marital_status['married'] = build_item('Married', data, item_levels,
		'B12001004 B12001013 + B12001001 / %')
	marital_status['single'] = build_item('Single', data, item_levels,
		'B12001003 B12001009 + B12001010 + B12001012 + B12001018 + B12001019 + B12001001 / %')

	marital_status_grouped = OrderedDict()
	doc['families']['marital_status_grouped'] = marital_status_grouped
	add_metadata(marital_status_grouped, 'B12001', 'Population 15 years and over', acs_name)

	# repeating data temporarily to develop grouped column chart format
	marital_status_grouped['never_married'] = OrderedDict()
	marital_status_grouped['never_married']['acs_release'] = acs_name
	marital_status_grouped['never_married']['metadata'] = {
		'universe': 'Population 15 years and over',
		'table_id': 'B12001',
		'name': 'Never married'
	}
	marital_status_grouped['never_married']['male'] = build_item('Male', data, item_levels,
		'B12001003 B12001002 / %')
	marital_status_grouped['never_married']['female'] = build_item('Female', data, item_levels,
		'B12001012 B12001011 / %')

	marital_status_grouped['married'] = OrderedDict()
	marital_status_grouped['married']['acs_release'] = acs_name
	marital_status_grouped['married']['metadata'] = {
		'universe': 'Population 15 years and over',
		'table_id': 'B12001',
		'name': 'Now married'
	}
	marital_status_grouped['married']['male'] = build_item('Male', data, item_levels,
		'B12001004 B12001002 / %')
	marital_status_grouped['married']['female'] = build_item('Female', data, item_levels,
		'B12001013 B12001011 / %')

	marital_status_grouped['divorced'] = OrderedDict()
	marital_status_grouped['divorced']['acs_release'] = acs_name
	marital_status_grouped['divorced']['metadata'] = {
		'universe': 'Population 15 years and over',
		'table_id': 'B12001',
		'name': 'Divorced'
	}
	marital_status_grouped['divorced']['male'] = build_item('Male', data, item_levels,
		'B12001010 B12001002 / %')
	marital_status_grouped['divorced']['female'] = build_item('Female', data, item_levels,
		'B12001019 B12001011 / %')

	marital_status_grouped['widowed'] = OrderedDict()
	marital_status_grouped['widowed']['acs_release'] = acs_name
	marital_status_grouped['widowed']['metadata'] = {
		'universe': 'Population 15 years and over',
		'table_id': 'B12001',
		'name': 'Widowed'
	}
	marital_status_grouped['widowed']['male'] = build_item('Male', data, item_levels,
		'B12001009 B12001002 / %')
	marital_status_grouped['widowed']['female'] = build_item('Female', data, item_levels,
		'B12001018 B12001011 / %')


	# Families: Family Types with Children
	#### Useful for SODC report! ####
	data = api.get_data('B09002', comparison_geoids, acs)
	acs_name = data['release']['name']

	family_types = dict()
	doc['families']['family_types'] = family_types

	children_family_type_dict = OrderedDict()
	family_types['children'] = children_family_type_dict
	add_metadata(children_family_type_dict, 'B09002', 'Own children under 18 years', acs_name)

	children_family_type_dict['married_couple'] = build_item('Married couple', data, item_levels,
		'B09002002 B09002001 / %')
	children_family_type_dict['male_householder'] = build_item('Male householder', data, item_levels,
		'B09002009 B09002001 / %')
	children_family_type_dict['female_householder'] = build_item('Female householder', data, item_levels,
		'B09002015 B09002001 / %')


	# Families: Percent of Families with Related Children Under 18
	#### SODC ####
	data = api.get_data('B11004', comparison_geoids, acs)
	acs_name = data['release']['name']

	families_with_children = dict()
	doc['families']['families_with_children'] = families_with_children

	families_with_children['percent_familes_with_children'] = build_item('Percent of families with related children under 18', data, item_levels, 
		'B11004003 B11004010 + B11004016 + B11004001 / %')
	add_metadata(families_with_children['percent_familes_with_children'], 'B11004', 'Family Type by Presence and Age of Related Children Under 18 Years', acs_name)

	# Families: Percent of Households with Children under 18
	#### SODC ####
	data = api.get_data('B11005', comparison_geoids, acs)
	acs_name = data['release']['name']

	households_with_children = dict()
	doc['families']['households_with_children'] = households_with_children
	households_with_children['percent_households_with_children'] = build_item('Percent of households with children under 18', data, item_levels, 
		'B11005002 B11005001 / %')
	add_metadata(households_with_children['percent_households_with_children'], 'B11005', 'Households by Presence of People Under 18 Years by Household Type', acs_name)


	# Families: Birth Rate by Women's Age
	data = api.get_data('B13016', comparison_geoids, acs)
	acs_name = data['release']['name']

	fertility = dict()
	doc['families']['fertility'] = fertility

	fertility['total'] = build_item('Women 15-50 who gave birth during past year', data, item_levels,
		'B13016002 B13016001 / %')
	add_metadata(fertility['total'], 'B13016', 'Women 15 to 50 years', acs_name)

	fertility_by_age_dict = OrderedDict()
	fertility['by_age'] = fertility_by_age_dict
	add_metadata(fertility['by_age'], 'B13016', 'Women 15 to 50 years', acs_name)

	fertility_by_age_dict['15_to_19'] = build_item('15-19', data, item_levels,
		'B13016003 B13016003 B13016011 + / %')
	fertility_by_age_dict['20_to_24'] = build_item('20-24', data, item_levels,
		'B13016004 B13016004 B13016012 + / %')
	fertility_by_age_dict['25_to_29'] = build_item('25-29', data, item_levels,
		'B13016005 B13016005 B13016013 + / %')
	fertility_by_age_dict['30_to_34'] = build_item('30-35', data, item_levels,
		'B13016006 B13016006 B13016014 + / %')
	fertility_by_age_dict['35_to_39'] = build_item('35-39', data, item_levels,
		'B13016007 B13016007 B13016015 + / %')
	fertility_by_age_dict['40_to_44'] = build_item('40-44', data, item_levels,
		'B13016008 B13016008 B13016016 + / %')
	fertility_by_age_dict['45_to_50'] = build_item('45-50', data, item_levels,
		'B13016009 B13016009 B13016017 + / %')

	# Families: Number of Households, Persons per Household, Household type distribution
	data = api.get_data(['B11001', 'B11002'], comparison_geoids, acs)
	acs_name = data['release']['name']

	households_dict = dict()
	doc['families']['households'] = households_dict

	households_dict['number_of_households'] = build_item('Number of households', data, item_levels,
		'B11001001')
	add_metadata(households_dict['number_of_households'], 'B11001', 'Households', acs_name)

	households_dict['persons_per_household'] = build_item('Persons per household', data, item_levels,
		'B11002001 B11001001 /')
	add_metadata(households_dict['persons_per_household'], 'B11001,b11002', 'Households', acs_name)

	households_distribution_dict = OrderedDict()
	households_dict['distribution'] = households_distribution_dict
	add_metadata(households_dict['distribution'], 'B11001', 'Households', acs_name)

	households_distribution_dict['married_couples'] = build_item('Married couples', data, item_levels,
		'B11002003 B11002001 / %')

	households_distribution_dict['male_householder'] = build_item('Male householder', data, item_levels,
		'B11002006 B11002001 / %')

	households_distribution_dict['female_householder'] = build_item('Female householder', data, item_levels,
		'B11002009 B11002001 / %')

	households_distribution_dict['nonfamily'] = build_item('Non-family', data, item_levels,
		'B11002012 B11002001 / %')


	# Housing: Number of Housing Units, Occupancy Distribution, Vacancy Distribution
	data = api.get_data('B25002', comparison_geoids, acs)
	acs_name = data['release']['name']

	units_dict = dict()
	doc['housing']['units'] = units_dict

	units_dict['number'] = build_item('Number of housing units', data, item_levels,
		'B25002001')
	add_metadata(units_dict['number'], 'B25002', 'Housing units', acs_name)

	occupancy_distribution_dict = OrderedDict()
	units_dict['occupancy_distribution'] = occupancy_distribution_dict
	add_metadata(units_dict['occupancy_distribution'], 'B25002', 'Housing units', acs_name)

	occupancy_distribution_dict['occupied'] = build_item('Occupied', data, item_levels,
		'B25002002 B25002001 / %')
	occupancy_distribution_dict['vacant'] = build_item('Vacant', data, item_levels,
		'B25002003 B25002001 / %')

	# Housing: Structure Distribution
	data = api.get_data('B25024', comparison_geoids, acs)
	acs_name = data['release']['name']

	structure_distribution_dict = OrderedDict()
	units_dict['structure_distribution'] = structure_distribution_dict
	add_metadata(units_dict['structure_distribution'], 'B25024', 'Housing units', acs_name)

	structure_distribution_dict['single_unit'] = build_item('Single unit', data, item_levels,
		'B25024002 B25024003 + B25024001 / %')
	structure_distribution_dict['multi_unit'] = build_item('Multi-unit', data, item_levels,
		'B25024004 B25024005 + B25024006 + B25024007 + B25024008 + B25024009 + B25024001 / %')
	structure_distribution_dict['mobile_home'] = build_item('Mobile home', data, item_levels,
		'B25024010 B25024001 / %')
	structure_distribution_dict['vehicle'] = build_item('Boat, RV, van, etc.', data, item_levels,
		'B25024011 B25024001 / %')

	# Housing: Tenure
	data = api.get_data('B25003', comparison_geoids, acs)
	acs_name = data['release']['name']

	ownership_dict = dict()
	doc['housing']['ownership'] = ownership_dict

	ownership_distribution_dict = OrderedDict()
	ownership_dict['distribution'] = ownership_distribution_dict
	add_metadata(ownership_dict['distribution'], 'B25003', 'Occupied housing units', acs_name)

	ownership_distribution_dict['owner'] = build_item('Owner occupied', data, item_levels,
		'B25003002 B25003001 / %')
	ownership_distribution_dict['renter'] = build_item('Renter occupied', data, item_levels,
		'B25003003 B25003001 / %')

	data = api.get_data('B25026', comparison_geoids, acs)
	acs_name = data['release']['name']

	length_of_tenure_dict = OrderedDict()
	doc['housing']['length_of_tenure'] = length_of_tenure_dict
	add_metadata(length_of_tenure_dict, 'B25026', 'Total population in occupied housing units', acs_name)

	length_of_tenure_dict['Before_1970'] = build_item('Before 1970', data, item_levels,
		'B25026008 B25026015 + B25026001 / %')
	length_of_tenure_dict['1970s'] = build_item('1970s', data, item_levels,
		'B25026007 B25026014 + B25026001 / %')
	length_of_tenure_dict['1980s'] = build_item('1980s', data, item_levels,
		'B25026006 B25026013 + B25026001 / %')
	length_of_tenure_dict['1990s'] = build_item('1990s', data, item_levels,
		'B25026005 B25026012 + B25026001 / %')
	length_of_tenure_dict['2000_to_2004'] = build_item('2000-2004', data, item_levels,
		'B25026004 B25026011 + B25026001 / %')
	length_of_tenure_dict['since_2005'] = build_item('Since 2005', data, item_levels,
		'B25026003 B25026010 + B25026001 / %')

	# Housing: Mobility
	data = api.get_data('B07003', comparison_geoids, acs)
	acs_name = data['release']['name']

	migration_dict = dict()
	doc['housing']['migration'] = migration_dict

	migration_dict['moved_since_previous_year'] = build_item('Moved since previous year', data, item_levels,
		'B07003007 B07003010 + B07003013 + B07003016 + B07003001 / %')
	add_metadata(migration_dict['moved_since_previous_year'], 'B07003', 'Population 1 year and over in the United States', acs_name)

	migration_distribution_dict = OrderedDict()
	doc['housing']['migration_distribution'] = migration_distribution_dict
	add_metadata(migration_distribution_dict, 'B07003', 'Population 1 year and over in the United States', acs_name)

	migration_distribution_dict['same_house_year_ago'] = build_item('Same house year ago', data, item_levels,
		'B07003004 B07003001 / %')
	migration_distribution_dict['moved_same_county'] = build_item('From same county', data, item_levels,
		'B07003007 B07003001 / %')
	migration_distribution_dict['moved_different_county'] = build_item('From different county', data, item_levels,
		'B07003010 B07003001 / %')
	migration_distribution_dict['moved_different_state'] = build_item('From different state', data, item_levels,
		'B07003013 B07003001 / %')
	migration_distribution_dict['moved_from_abroad'] = build_item('From abroad', data, item_levels,
		'B07003016 B07003001 / %')

	# Housing: Median Costs
	data = api.get_data('B25105', comparison_geoids, acs)
	acs_name = data['release']['name']

	costs_dict = dict()
	doc['housing']['costs'] = costs_dict

	costs_dict['median_costs'] = build_item('Median Monthly Housing Costs', data, item_levels,
		'B25105001')
	add_metadata(costs_dict['median_costs'], 'B25105', 'Occupied housing units with monthly housing costs', acs_name)

	# Housing: HOUSING COSTS AS A PERCENTAGE OF HOUSEHOLD INCOME
	data = api.get_data('B25106', comparison_geoids, acs)
	acs_name = data['release']['name']

	housing_costs_distribution = OrderedDict()
	costs_dict['housing_costs_distribution'] = housing_costs_distribution
	add_metadata(housing_costs_distribution, 'B25106', 'Occupied housing units', acs_name)

	housing_costs_distribution['under_20'] = build_item('Under $20K', data, item_levels,
		'B25106006 B25106028 + B25106003 B25106025 + / %')
	housing_costs_distribution['20_to_35'] = build_item('$20K - $35K', data, item_levels,
		'B25106010 B25106032 + B25106007 B25106029 + / %')
	housing_costs_distribution['25_to_50'] = build_item('$35K - $50K', data, item_levels,
		'B25106014 B25106036 + B25106011 B25106033 + / %')
	housing_costs_distribution['50_to_75'] = build_item('$50K - $75K', data, item_levels,
		'B25106018 B25106040 + B25106015 B25106037 + / %')
	housing_costs_distribution['over_75'] = build_item('Over $75K', data, item_levels,
		'B25106022 B25106044 + B25106019 B25106041 + / %')

	# Housing: Median Value and Distribution of Values
	data = api.get_data('B25077', comparison_geoids, acs)
	acs_name = data['release']['name']

	ownership_dict['median_value'] = build_item('Median value of owner-occupied housing units', data, item_levels,
		'B25077001')
	add_metadata(ownership_dict['median_value'], 'B25077', 'Owner-occupied housing units', acs_name)

	data = api.get_data('B25075', comparison_geoids, acs)
	acs_name = data['release']['name']

	value_distribution = OrderedDict()
	ownership_dict['value_distribution'] = value_distribution
	add_metadata(value_distribution, 'B25075', 'Owner-occupied housing units', acs_name)

	ownership_dict['total_value'] = build_item('Total value of owner-occupied housing units', data, item_levels,
		'B25075001')

	value_distribution['under_100'] = build_item('Under $100K', data, item_levels,
		'B25075002 B25075003 + B25075004 + B25075005 + B25075006 + B25075007 + B25075008 + B25075009 + B25075010 + B25075011 + B25075012 + B25075013 + B25075014 + B25075001 / %')
	value_distribution['100_to_200'] = build_item('$100K - $200K', data, item_levels,
		'B25075015 B25075016 + B25075017 + B25075018 + B25075001 / %')
	value_distribution['200_to_300'] = build_item('$200K - $300K', data, item_levels,
		'B25075019 B25075020 + B25075001 / %')
	value_distribution['300_to_400'] = build_item('$300K - $400K', data, item_levels,
		'B25075021 B25075001 / %')
	value_distribution['400_to_500'] = build_item('$400K - $500K', data, item_levels,
		'B25075022 B25075001 / %')
	value_distribution['500_to_1000000'] = build_item('$500K - $1M', data, item_levels,
		'B25075023 B25075024 + B25075001 / %')
	value_distribution['over_1000000'] = build_item('Over $1M', data, item_levels,
		'B25075025 B25075001 / %')


	# Social: Educational Attainment
	data = api.get_data('B15002', comparison_geoids, acs)
	acs_name = data['release']['name']

	attainment_dict = dict()
	doc['social']['educational_attainment'] = attainment_dict

	attainment_dict['percent_high_school_grad_or_higher'] = build_item('High school grad or higher', data, item_levels,
		'B15002011 B15002012 + B15002013 + B15002014 + B15002015 + B15002016 + B15002017 + B15002018 + B15002028 + B15002029 + B15002030 + B15002031 + B15002032 + B15002033 + B15002034 + B15002035 + B15002001 / %')
	add_metadata(attainment_dict['percent_high_school_grad_or_higher'], 'B15002', 'Population 25 years and over', acs_name)

	attainment_dict['percent_bachelor_degree_or_higher'] = build_item('Bachelor\'s degree or higher', data, item_levels,
		'B15002015 B15002016 + B15002017 + B15002018 + B15002032 + B15002033 + B15002034 + B15002035 + B15002001 / %')
	add_metadata(attainment_dict['percent_bachelor_degree_or_higher'], 'B15002', 'Population 25 years and over', acs_name)

	attainment_distribution_dict = OrderedDict()
	doc['social']['educational_attainment_distribution'] = attainment_distribution_dict
	add_metadata(attainment_distribution_dict, 'B15002', 'Population 25 years and over', acs_name)

	attainment_distribution_dict['non_high_school_grad'] = build_item('No degree', data, item_levels,
		'B15002003 B15002004 + B15002005 + B15002006 + B15002007 + B15002008 + B15002009 + B15002010 + B15002020 + B15002021 + B15002022 + B15002023 + B15002024 + B15002025 + B15002026 + B15002027 + B15002001 / %')

	attainment_distribution_dict['high_school_grad'] = build_item('High school', data, item_levels,
		'B15002011 B15002028 + B15002001 / %')

	attainment_distribution_dict['some_college'] = build_item('Some college', data, item_levels,
		'B15002012 B15002013 + B15002014 + B15002029 + B15002030 + B15002031 + B15002001 / %')

	attainment_distribution_dict['Bachelor_degree'] = build_item('Bachelor\'s', data, item_levels,
		'B15002015 B15002032 + B15002001 / %')

	attainment_distribution_dict['post_grad_degree'] = build_item('Post-grad', data, item_levels,
		'B15002016 B15002017 + B15002018 + B15002033 + B15002034 + B15002035 + B15002001 / %')

	# Social: Health Insurance
	data = api.get_data('B27001', comparison_geoids, acs)
	acs_name = data['release']['name']

	health_insurace_dict = dict()
	doc['social']['health_insurace'] = health_insurace_dict

	health_insurace_dict['uninsured'] = build_item('Persons without health insurace', data, item_levels,
		'B27001005 B27001008 + B27001011 + B27001014 + B27001017 + B27001020 + B27001023 + B27001026 + B27001029 + B27001033 + B27001036 + B27001039 + B27001042 + B27001045 + B27001048 + B27001051 + B27001054 + B27001057 + B27001001 / %')
	add_metadata(health_insurace_dict['uninsured'], 'B27001', 'Civilian noninstitutionalized population', acs_name)

	coverage_distribution = OrderedDict()
	health_insurace_dict['coverage_distribution'] = coverage_distribution
	add_metadata(coverage_distribution, 'B27001', 'Civilian noninstitutionalized population', acs_name)

	# repeating data temporarily to develop grouped column chart format
	coverage_distribution['under_6'] = OrderedDict()
	coverage_distribution['under_6']['acs_release'] = acs_name
	coverage_distribution['under_6']['metadata'] = {
		'universe': 'Civilian noninstitutionalized population',
		'table_id': 'B27001',
		'name': 'Under 6'
	}
	coverage_distribution['under_6']['male'] = build_item('Male', data, item_levels,
		'B27001005 B27001003 / %')
	coverage_distribution['under_6']['female'] = build_item('Female', data, item_levels,
		'B27001033 B27001031 / %')

	coverage_distribution['6_17'] = OrderedDict()
	coverage_distribution['6_17']['acs_release'] = acs_name
	coverage_distribution['6_17']['metadata'] = {
		'universe': 'Civilian noninstitutionalized population',
		'table_id': 'B27001',
		'name': '6-17'
	}
	coverage_distribution['6_17']['male'] = build_item('Male', data, item_levels,
		'B27001008 B27001006 / %')
	coverage_distribution['6_17']['female'] = build_item('Female', data, item_levels,
		'B27001036 B27001034 / %')

	coverage_distribution['18_24'] = OrderedDict()
	coverage_distribution['18_24']['acs_release'] = acs_name
	coverage_distribution['18_24']['metadata'] = {
		'universe': 'Civilian noninstitutionalized population',
		'table_id': 'B27001',
		'name': '18-24'
	}
	coverage_distribution['18_24']['male'] = build_item('Male', data, item_levels,
		'B27001011 B27001009 / %')
	coverage_distribution['18_24']['female'] = build_item('Female', data, item_levels,
		'B27001039 B27001037 / %')

	coverage_distribution['25_34'] = OrderedDict()
	coverage_distribution['25_34']['acs_release'] = acs_name
	coverage_distribution['25_34']['metadata'] = {
		'universe': 'Civilian noninstitutionalized population',
		'table_id': 'B27001',
		'name': '25-34'
	}
	coverage_distribution['25_34']['male'] = build_item('Male', data, item_levels,
		'B27001014 B27001012 / %')
	coverage_distribution['25_34']['female'] = build_item('Female', data, item_levels,
		'B27001042 B27001040 / %')

	coverage_distribution['35_64'] = OrderedDict()
	coverage_distribution['35_64']['acs_release'] = acs_name
	coverage_distribution['35_64']['metadata'] = {
		'universe': 'Civilian noninstitutionalized population',
		'table_id': 'B27001',
		'name': '35-64'
	}
	coverage_distribution['35_64']['male'] = build_item('Male', data, item_levels,
		'B27001017 B27001020 + B27001023 + B27001015 B27001018 + B27001021 + / %')
	coverage_distribution['35_64']['female'] = build_item('Female', data, item_levels,
		'B27001045 B27001048 + B27001051 + B27001043 B27001046 + B27001049 + / %')

	# coverage_distribution['45_54'] = OrderedDict()
	# coverage_distribution['45_54']['acs_release'] = acs_name
	# coverage_distribution['45_54']['metadata'] = {
	# 	'universe': 'Civilian noninstitutionalized population',
	# 	'table_id': 'B27001',
	# 	'name': '45-54'
	# }
	# coverage_distribution['45_54']['male'] = build_item('Male', data, item_levels,
	# 	'B27001020 B27001018 / %')
	# coverage_distribution['45_54']['female'] = build_item('Female', data, item_levels,
	# 	'B27001048 B27001046 / %')

	# coverage_distribution['55_64'] = OrderedDict()
	# coverage_distribution['55_64']['acs_release'] = acs_name
	# coverage_distribution['55_64']['metadata'] = {
	# 	'universe': 'Civilian noninstitutionalized population',
	# 	'table_id': 'B27001',
	# 	'name': '55-64'
	# }
	# coverage_distribution['55_64']['male'] = build_item('Male', data, item_levels,
	# 	'B27001023 B27001021 / %')
	# coverage_distribution['55_64']['female'] = build_item('Female', data, item_levels,
	# 	'B27001051 B27001049 / %')

	coverage_distribution['over_65'] = OrderedDict()
	coverage_distribution['over_65']['acs_release'] = acs_name
	coverage_distribution['over_65']['metadata'] = {
		'universe': 'Civilian noninstitutionalized population',
		'table_id': 'B27001',
		'name': 'Over 65'
	}
	coverage_distribution['over_65']['male'] = build_item('Male', data, item_levels,
		'B27001026 B27001029 + B27001024 B27001027 + / %')
	coverage_distribution['over_65']['female'] = build_item('Female', data, item_levels,
		'B27001054 B27001057 + B27001052 B27001055 + / %')

	# coverage_distribution['over_75'] = OrderedDict()
	# coverage_distribution['over_75']['acs_release'] = acs_name
	# coverage_distribution['over_75']['metadata'] = {
	# 	'universe': 'Civilian noninstitutionalized population',
	# 	'table_id': 'B27001',
	# 	'name': 'Over 75'
	# }
	# coverage_distribution['over_75']['male'] = build_item('Male', data, item_levels,
	# 	'B27001029 B27001027 / %')
	# coverage_distribution['over_75']['female'] = build_item('Female', data, item_levels,
	# 	'B27001057 B27001055 / %')

	# Social: Place of Birth
	data = api.get_data('B05002', comparison_geoids, acs)
	acs_name = data['release']['name']

	foreign_dict = dict()
	doc['social']['place_of_birth'] = foreign_dict

	foreign_dict['percent_foreign_born'] = build_item('Foreign-born population', data, item_levels,
		'B05002013 B05002001 / %')
	add_metadata(foreign_dict['percent_foreign_born'], 'B05002', 'Total population', acs_name)

	data = api.get_data('B05006', comparison_geoids, acs)
	acs_name = data['release']['name']

	place_of_birth_dict = OrderedDict()
	foreign_dict['distribution'] = place_of_birth_dict
	add_metadata(place_of_birth_dict, 'B05006', 'Foreign-born population', acs_name)

	place_of_birth_dict['europe'] = build_item('Europe', data, item_levels,
		'B05006002 B05006001 / %')
	place_of_birth_dict['asia'] = build_item('Asia', data, item_levels,
		'B05006047 B05006001 / %')
	place_of_birth_dict['africa'] = build_item('Africa', data, item_levels,
		'B05006091 B05006001 / %')
	place_of_birth_dict['oceania'] = build_item('Oceania', data, item_levels,
		'B05006116 B05006001 / %')
	place_of_birth_dict['latin_america'] = build_item('Latin America', data, item_levels,
		'B05006123 B05006001 / %')
	place_of_birth_dict['north_america'] = build_item('North America', data, item_levels,
		'B05006159 B05006001 / %')

	# Social: Percentage of Non-English Spoken at Home, Language Spoken at Home for Children, Adults
	data = api.get_data('B16001', comparison_geoids, acs)
	acs_name = data['release']['name']

	language_dict = dict()
	doc['social']['language'] = language_dict

	language_dict['percent_non_english_at_home'] = build_item('Persons with language other than English spoken at home', data, item_levels,
		'B16001001 B16001002 - B16001001 / %')
	add_metadata(language_dict['percent_non_english_at_home'], 'B16001', 'Population 5 years and over', acs_name)


	data = api.get_data('B16007', comparison_geoids, acs)
	acs_name = data['release']['name']

	language_children = OrderedDict()
	language_adults = OrderedDict()
	language_dict['children'] = language_children
	add_metadata(language_dict['children'], 'B16007', 'Population 5-17 years old', acs_name)
	language_dict['adults'] = language_adults
	add_metadata(language_dict['adults'], 'B16007', 'Population 18 years and over', acs_name)

	language_children['english'] = build_item('English only', data, item_levels,
		'B16007003 B16007002 / %')
	language_adults['english'] = build_item('English only', data, item_levels,
		'B16007009 B16007015 + B16007008 B16007014 + / %')

	language_children['spanish'] = build_item('Spanish', data, item_levels,
		'B16007004 B16007002 / %')
	language_adults['spanish'] = build_item('Spanish', data, item_levels,
		'B16007010 B16007016 + B16007008 B16007014 + / %')

	language_children['indoeuropean'] = build_item('Indo-European', data, item_levels,
		'B16007005 B16007002 / %')
	language_adults['indoeuropean'] = build_item('Indo-European', data, item_levels,
		'B16007011 B16007017 + B16007008 B16007014 + / %')

	language_children['asian_islander'] = build_item('Asian/Pacific Islander', data, item_levels,
		'B16007006 B16007002 / %')
	language_adults['asian_islander'] = build_item('Asian/Pacific Islander', data, item_levels,
		'B16007012 B16007018 + B16007008 B16007014 + / %')

	language_children['other'] = build_item('Other', data, item_levels,
		'B16007007 B16007002 / %')
	language_adults['other'] = build_item('Other', data, item_levels,
		'B16007013 B16007019 + B16007008 B16007014 + / %')


	# Social: Number of Veterans, Wartime Service, Sex of Veterans
	data = api.get_data('B21002', comparison_geoids, acs)
	acs_name = data['release']['name']

	veterans_dict = dict()
	doc['social']['veterans'] = veterans_dict

	veterans_service_dict = OrderedDict()
	veterans_dict['wartime_service'] = veterans_service_dict
	add_metadata(veterans_service_dict, 'B21002', 'Civilian veterans 18 years and over', acs_name)

	veterans_service_dict['wwii'] = build_item('WWII', data, item_levels,
		'B21002009 B21002011 + B21002012 +')
	veterans_service_dict['korea'] = build_item('Korea', data, item_levels,
		'B21002008 B21002009 + B21002010 + B21002011 +')
	veterans_service_dict['vietnam'] = build_item('Vietnam', data, item_levels,
		'B21002004 B21002006 + B21002007 + B21002008 + B21002009 +')
	veterans_service_dict['gulf_1990s'] = build_item('Gulf (1990s)', data, item_levels,
		'B21002003 B21002004 + B21002005 + B21002006 +')
	veterans_service_dict['gulf_2001'] = build_item('Gulf (2001-)', data, item_levels,
		'B21002002 B21002003 + B21002004 +')

	data = api.get_data('B21001', comparison_geoids, acs)
	acs_name = data['release']['name']

	veterans_sex_dict = OrderedDict()
	veterans_dict['sex'] = veterans_sex_dict

	veterans_sex_dict['male'] = build_item('Male', data, item_levels,
		'B21001005')
	add_metadata(veterans_sex_dict['male'], 'B21001', 'Civilian population 18 years and over', acs_name)
	veterans_sex_dict['female'] = build_item('Female', data, item_levels,
		'B21001023')
	add_metadata(veterans_sex_dict['female'], 'B21001', 'Civilian population 18 years and over', acs_name)

	veterans_dict['number'] = build_item('Total veterans', data, item_levels,
		'B21001002')
	add_metadata(veterans_dict['number'], 'B21001', 'Civilian population 18 years and over', acs_name)

	veterans_dict['percentage'] = build_item('Population with veteran status', data, item_levels,
		'B21001002 B21001001 / %')
	add_metadata(veterans_dict['percentage'], 'B21001', 'Civilian population 18 years and over', acs_name)

	geo_metadata = api.get_geoid_data(geoid)

	if geo_metadata:
		geo_metadata = geo_metadata['properties']
		doc['geo_metadata'] = geo_metadata

		# add a few last things
		# make square miles http://www.census.gov/geo/www/geo_defn.html#AreaMeasurement
		square_miles = get_division(geo_metadata['aland'], 2589988)
		if square_miles < .1:
			square_miles = get_division(geo_metadata['aland'], 2589988, 3)
		total_pop = doc['geography']['this']['total_population']
		population_density = get_division(total_pop, get_division(geo_metadata['aland'], 2589988, -1))
		doc['geo_metadata']['square_miles'] = square_miles
		doc['geo_metadata']['population_density'] = population_density

	return doc

def find_dicts_with_key(dictionary, searchkey):
	stack = [dictionary]
	dict_list = []
	while stack:
		d = stack.pop()
		if searchkey in d:
			dict_list.append(d)
		for key, value in d.iteritems():
			if isinstance(value, dict) or isinstance(value, OrderedDict):
				stack.append(value)

	return dict_list

def enhance_api_data(api_data):
	dict_list = find_dicts_with_key(api_data, 'values')

	for d in dict_list:
		raw = {}
		enhanced = {}
		try:
			geo_value = d['values']['this']
		except Exception as e:
			geo_value = None

		num_comparatives = 2

		# create our containers for transformation
		for obj in ['values', 'error', 'numerators', 'numerator_errors']:
			raw[obj] = d[obj]
			enhanced[obj] = OrderedDict()
		enhanced['index'] = OrderedDict()
		enhanced['error_ratio'] = OrderedDict()
		comparative_sumlevs = []

		# enhance
		for sumlevel in ['this', 'place', 'CBSA', 'county', 'state', 'nation']:

			# favor CBSA over county, but we don't want both
			if sumlevel == 'county' and 'CBSA' in enhanced['values']:
				continue

			# add the index value for comparatives
			if sumlevel in raw['values']:
				enhanced['values'][sumlevel] = raw['values'][sumlevel]
				if geo_value:
					enhanced['index'][sumlevel] = get_ratio(geo_value, raw['values'][sumlevel])
				else:
					enhanced['index'][sumlevel] = 0


				# add to our list of comparatives for the template to use
				if sumlevel != 'this':
					comparative_sumlevs.append(sumlevel)

			# add the moe ratios
			if (sumlevel in raw['values']) and (sumlevel in raw['error']):
				enhanced['error'][sumlevel] = raw['error'][sumlevel]
				enhanced['error_ratio'][sumlevel] = get_ratio(raw['error'][sumlevel], raw['values'][sumlevel], 3)

			# add the numerators and numerator_errors
			if sumlevel in raw['numerators']:
				enhanced['numerators'][sumlevel] = raw['numerators'][sumlevel]

			if (sumlevel in raw['numerators']) and (sumlevel in raw['numerator_errors']):
				enhanced['numerator_errors'][sumlevel] = raw['numerator_errors'][sumlevel]

			if len(enhanced['values']) >= (num_comparatives + 1):
				break

		# replace data with enhanced version
		for obj in ['values', 'index', 'error', 'error_ratio', 'numerators', 'numerator_errors']:
			d[obj] = enhanced[obj]

		api_data['geography']['comparatives'] = comparative_sumlevs

	# Put this down here to make sure geoid is valid before using it
	sumlevel = api_data['geography']['this']['sumlevel']
	api_data['geography']['this']['sumlevel_name'] = SUMMARY_LEVEL_DICT[sumlevel]['name']
	api_data['geography']['this']['short_geoid'] = api_data['geography']['this']['full_geoid'].split('US')[1]
	try:
		release_bits = api_data['geography']['census_release'].split(' ')
		api_data['geography']['census_release_year'] = release_bits[1][2:]
		api_data['geography']['census_release_level'] = release_level = release_bits[2][:1]
	except:
		pass

	# ProPublica Opportunity Gap app doesn't include smallest schools.
	# Originally, this also enabled links to Census narrative profiles,
	# but those disappeared.
	if release_level in ['1','3'] and sumlevel in ['950', '960', '970']:
		api_data['geography']['this']['show_extra_links'] = True

	return api_data

if __name__ == '__main__':
	print json.dumps(geo_profile('04000US55'), indent=2)
