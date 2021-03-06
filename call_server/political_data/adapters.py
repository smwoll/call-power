# translate country specific data to campaign model field names

from collections import defaultdict

def adapt_by_key(key):
    if key.startswith("us:bioguide"):
        return UnitedStatesData()
    elif key.startswith("us_state:openstates"):
        return OpenStatesData()
    elif key.startswith("us_state:governor"):
        return GovernorAdapter()
    elif key.startswith("ca:opennorth"):
        return OpenNorthAdapter()
    elif key.startswith("custom"):
        return CustomDataAdapter()
    else:
        return DataAdapter()
    # TODO add for other countries


class DataAdapter(object):
    def __init__(self, **kwargs):
        pass

    def key(self, key, split_by='-'):
        """
        @return tuple of key and suffix, split by an optional delimiter
        """
        if split_by in key:
            return key.split(split_by, 1)
        else:
            return (key, '')

    def target(self, data):
        return data

    def offices(self, data):
        return [data]


class CustomDataAdapter(DataAdapter):
    def target(self, data):
        adapted = {
            'title': data.get('title', ''),
            'uid': data.get('uid', ''),
            'number': data.get('number', '')
        }
        if 'first_name' in data and 'last_name' in data:
            adapted['name'] = u'{first_name} {last_name}'.format(**data)
        elif 'name' in data:
            adapted['name'] = data['name']
        else:
            data['name'] = 'Unknown'
        return adapted

class UnitedStatesData(DataAdapter):
    def key(self, key):
        # split district office id from rest of bioguide
        if '-' in key:
            return key.split('-', 1)
        else:
            return (key, '')

    def target(self, data):
        adapted = {
            'number': data.get('phone', ''), # DC office number
            'title': data.get('title', ''),
            'uid': data.get('bioguide_id', ''),
            'location': 'DC', # don't parse whole address here
        }
        if 'first_name' in data and 'last_name' in data:
            adapted['name'] = u'{first_name} {last_name}'.format(**data)
        elif 'name' in data:
            adapted['name'] = data['name']
        else:
            data['name'] = 'Unknown'
        if 'district' in data and data['district']:
            adapted['district'] = '{state}-{district}'.format(**data)
        else:
            adapted['district'] = data.get('state', '')
        return adapted

    def offices(self, data):
        # district office numbers
        office_list = []
        for office in data.get('offices', []):
            if not 'phone' in office:
                continue
            office_data = {
                'name': office.get('city', ''),
                'number': office.get('phone', ''),
                'uid': office.get('id', ''),
                'type': 'district'
            }
            if 'city' in office and 'state' in office:
                if 'address' in office and 'building' in office:
                    office_data['address'] = u'{address} {building} {city} {state}'.format(**office)
                elif 'address' in office:
                    office_data['address'] = u'{address} {city} {state}'.format(**office)
                else:
                    office_data['address'] = u'{city} {state}'.format(**office)
            else:
                office_data['address'] = ''

            if 'latitude' in office and 'longitude' in office:
                office_data['latlon'] = 'POINT({latitude}, {longitude})'.format(**office)
            office_list.append(office_data)
        return office_list


class OpenStatesData(DataAdapter):
    def target(self, data):
        if data.get('leg_id'):
            return self.target_legacy(data)

        adapted = {
            'uid': data.get('id')
        }
        if 'chamber' in data:
            if type(data['chamber']) == dict:
                chamber = data['chamber'][0]['organization']['classification']
                district = data['chamber'][0]['post']['label']
            elif type(data['chamber']) == str:
                chamber = data['chamber']
                district = data.get('district', '')
            else:
                chamber = None
                district = None
        else:
            chamber = None

        if 'title' in data:
            adapted['title'] = data['title']
        elif chamber == "upper":
            adapted['title'] = 'Senator'
        else:
            adapted['title'] = 'Representative'

        adapted['district'] = district

        if data.get('name'):
            adapted['name'] = data['name']
        elif 'givenName' in data and 'familyName' in data:
            adapted['name'] = u'{givenName} {familyName}'.format(**data)

        # filter contact details for voice type
        if 'contactDetails' in data:
            office_phones = [d for d in data['contactDetails'] if d['type'] == 'voice']
            # default to capitol office
            for office in office_phones:
                if office.get('note') == 'Capitol Office':
                    adapted['number'] = office.get('value', '')
            # if none, try first
            if not 'number' in adapted:
                adapted['number'] = office_phones[0].get('value', '')
                # fallback to none

        return adapted

    def target_legacy(self, data):
        """ adapter for OpenStates v1 API data"""
        adapted = {
            'uid': data.get('leg_id', '')
        }
        if 'title' in data:
            adapted['title'] = data.get('title')
        elif 'chamber' in data:
            if data['chamber'] == "upper":
                adapted['title'] = 'Senator'
            else:
                adapted['title'] = 'Representative'

        if 'first_name' in data and 'last_name' in data:
            adapted['name'] = u'{first_name} {last_name}'.format(**data)
        elif data.get('full_name'):
            adapted['name'] = data['full_name']
        elif data.get('name'):
            adapted['name'] = data['name']
        else:
            adapted['name'] = 'Unknown'

        # default to capitol office
        if 'offices' in data:
            for office in data['offices']:
                if office.get('type') == 'capitol':
                    adapted['number'] = office.get('phone', '')
        # if none, try first
        if not 'number' in adapted:
            adapted['number'] = data.get('offices',[{}])[0].get('phone', '')
            # fallback to none

        try:
            district_num = int(data.get('district')[3:])
            adapted['district'] = district_num
        except ValueError:
            adapted['district'] = data.get('district', '')

        return adapted

    def offices(self, data):
        if data.get('leg_id'):
            return self.offices_legacy(data)

        # merge contactDetails list of dicts by note
        # so we can iterate more cleanly
        offices_dict = defaultdict(dict)
        for c in data.get('contactDetails', []):
            offices_dict[c['note']][c['type']] = c['value']
            offices_dict[c['note']]['name'] = c['note']

        office_list = []
        for office in offices_dict.values():
            office_name = office.get('name', '')
            office_name = office_name.replace('Office', '').replace('office', '')
            if '#' in office_name:
                office_name = office_name.split('#')[0]

            office_list.append({
                'name': office_name,
                'address': office.get('address', ''),
                'number': office.get('voice', ''),
                'type': office.get('name', '')
            })
        return office_list

    def offices_legacy(self, data):
        """ adapter for OpenStates v1 API data"""
        office_list = []
        for office in data.get('offices', []):
            if office.get('type') == 'capitol':
                # capitol office is captured in target.number
                continue
            if not 'phone' in office:
                continue

            office_name = office.get('name', '')
            office_name = office_name.replace('Office', '').replace('office', '')
            if '#' in office_name:
                office_name = office_name.split('#')[0]

            office_list.append({
                'name': office_name,
                'address': office.get('address', ''),
                'number': office.get('phone', ''),
                'type': office.get('type', '')
            })
        return office_list


class GovernorAdapter(DataAdapter):
    def target(self, data):
        adapted = {
            'title': data.get('title', ''),
            'number': data.get('phone', ''),
            'uid': data.get('state', ''),
            'district': data.get('state', '')
        }
        if 'first_name' in data and 'last_name' in data:
            adapted['name'] = u'{first_name} {last_name}'.format(**data)
        elif data.get('full_name'):
            adapted['name'] = data['full_name']
        else:
            adapted['name'] = 'Unknown'

        return adapted

    def offices(self, data):
        return []


class OpenNorthAdapter(DataAdapter):
    def key(self, key, split_by=None):
        # override default key split behavior, because we need to use district names which may have dashes
        return (key, '')

    def target(self, data):
        adapted = {
            'title': data.get('elected_office', ''),
            'uid': data.get('cache_key', ''),
            'district': data.get('district_name', '')
        }
        if data.get('offices'):
            office_legistlature = list(filter(lambda d: d['type'] == 'legislature', data['offices']))
            adapted['number'] = office_legistlature[0].get('tel', '')
            # legislature office number is the main one
        else:
            adapted['number'] = ''

        if 'first_name' in data and 'last_name' in data:
            adapted['name'] = u'{first_name} {last_name}'.format(**data)
        elif data.get('full_name'):
            adapted['name'] = data['full_name']
        elif data.get('name'):
            adapted['name'] = data['name']
        else:
            adapted['name'] = 'Unknown'

        if 'title' in data:
            adapted['title'] = data.get('title')

        return adapted

    def offices(self, data):
        office_list = []
        for office in data.get('offices', []):
            if office.get('type') == 'legislature':
                # legislature office is captured in target.number
                continue
            if not 'tel' in office:
                continue
            office_list.append({
                'name': office.get('type', ''),
                'address': office.get('postal', ''),
                'number': office.get('tel', ''),
                'type': office.get('type', '')
            })
        return office_list

