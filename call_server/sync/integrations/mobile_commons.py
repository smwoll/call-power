from flask import current_app

import requests
from xml.etree import ElementTree
from requests.auth import HTTPBasicAuth
from requests_toolbelt import sessions
from . import CRMIntegration

class MobileCommonsIntegration(CRMIntegration):
    BATCH_ALL_CALLS_IN_SESSION = True
    # this forces the SyncCampaign to save only the first call in a session, to avoid duplicates

    def __init__(self, username, password):
        super(MobileCommonsIntegration, self).__init__()
        if username and password:
            self.mc_api = sessions.BaseUrlSession(
                base_url='https://secure.mcommons.com')
            self.mc_api.auth = HTTPBasicAuth(username, password)
        else:
            raise Exception('unable to authenticate to MobileCommons')

    def get_user(self, phone_number):
        """Not required for MobileCommons, we have a one-shot API with phone number"""
        # this is basically a no-op, but wraps the data in the desired format
        return {
            'id': phone_number,
            'phone': phone_number
        }

    def check_opt_out(self, crm_campaign_id, crm_user):
        # check user profile for existing subscription or opt-out
        # returns True 
        data = {
            'phone_number': crm_user['phone'],
        }

        response = self.mc_api.get('/api/profile', params=data)
        results = ElementTree.fromstring(response.content)
        user_profile = results.find('profile')
        if not user_profile:
            return None

        user_status = user_profile.find('status').text
        subscriptions = user_profile.find('subscriptions')
        for s in subscriptions:
            if s.get('campaign_id') == crm_campaign_id:
                if s.get('status') == 'Opted-Out':
                    return True


    def save_action(self, call, crm_campaign_id, crm_user):
        """Given a crm_user and crm_campaign_id (opt in path)
        Subscribe the user's phone number via the opt-in path
        Returns a boolean status"""

        if self.check_opt_out(crm_campaign_id, crm_user):
            current_app.logger.warning('crm user (%s) opted out of campaign (%s)' % (crm_user['phone'], crm_campaign_id))
            return False

        data = {
            'phone_number': crm_user['phone'],
            'opt_in_path_id': crm_campaign_id
        }

        response = self.mc_api.post('/api/profile_update', data)
        results = ElementTree.fromstring(response.content)
        success = bool(results.get('success'))
        # coerce 'true'/'false' into boolean

        # verify phone number
        # phone_number = results.find('profile').find('phone_number').text

        # verify subscription
        # subscriptions = results.find('profile').find('subscriptions')
        # match campaign_id to opt_in_path_id ?

        return success


    def save_campaign_meta(self, crm_campaign_id, meta={}):
        """Given a page name (crm_campaign_id) 
        Save meta values to pagefields
        Returns a boolean status"""
        raise NotImplementedError()
