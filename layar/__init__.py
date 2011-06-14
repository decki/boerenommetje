from decimal import Decimal
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.hashcompat import sha_constructor as sha1
from django.utils import simplejson as json

class LayarException(Exception):
    ''' Layar exception - takes a code (20-29) to return to Layar'''
    def __init__(self, code, message):
        self.code = code
        self.message = message

class POI(object):
    def __init__(self, id, lat, lon, title, actions=None, image_url=None,
                 line2=None, line3=None, line4=None, type=0, attribution=None,
                 dimension=1, alt=None, transform=None, object_detail=None,
                 relative_alt=None):
        self.id = str(id)
        self.lat = lat
        self.lon = lon
        self.title = title          # recommended max len 60
        self.imageURL = image_url
        self.line2 = line2          # recommended max len 35
        self.line3 = line3
        self.line4 = line4
        self.type = type
        self.attribution = attribution  # recommended max len 45
        self.dimension = dimension
        self.alt = alt
        self.transform = transform
        self.object = object_detail
        self.relativeAlt = relative_alt
        self.actions = actions

    def to_dict(self):
        d = dict(self.__dict__)

        # don't include optional attributes if not set
        remove_if_none = ('alt', 'transform', 'object', 'relativeAlt')
        for k in remove_if_none:
            if not d[k]:
                del d[k]

        # do lat/long conversion
        if isinstance(self.lat, (float, Decimal)):
            d['lat'] = int(self.lat*1000000)
        if isinstance(self.lon, (float, Decimal)):
            d['lon'] = int(self.lon*1000000)

        # convert actions dictionary into expected format
        if isinstance(self.actions, dict):
            raise DeprecationWarning('passing a dictionary for actions is deprecated - order will be lost')
            d['actions'] = [{'label':k, 'uri':v} for k,v in self.actions.iteritems()]
        elif isinstance(self.actions, list):
            pass
        else:
            d['actions'] = []

        return d

class LayarView(object):
    results_per_page = 15
    max_results = 50
    default_radius = 1000
    verify_hash = False

    #def __init__(self):
    #    self.developer_key = settings.LAYAR_DEVELOPER_KEY

    def __call__(self, request):
        try:
            # parameters from http://layar.pbworks.com/GetPointsOfInterest

            # required parameters
            user_id = request.GET['userId']
            #developer_id = request.GET['developerId']
            developer_hash = request.GET['developerHash']
            timestamp = request.GET['timestamp']
            layer_name = request.GET['layerName']
            lat = float(request.GET['lat'])
            lon = float(request.GET['lon'])

            # optional
            accuracy = request.GET.get('accuracy')
            if accuracy:
                accuracy = int(accuracy)
            radius = request.GET.get('radius')
            if radius:
                radius = int(radius)
            alt = request.GET.get('alt')
            if alt:
                alt = int(alt)
            page = int(request.GET.get('pageKey', 0))

            # user defined UI elements
            radio_option = request.GET.get('RADIOLIST')
            search = request.GET.get('SEARCHBOX')
            search2 = request.GET.get('SEARCHBOX_2')
            search3 = request.GET.get('SEARCHBOX_3')
            slider = request.GET.get('CUSTOM_SLIDER')
            slider2 = request.GET.get('CUSTOM_SLIDER_2')
            slider3 = request.GET.get('CUSTOM_SLIDER_3')
            checkboxes = request.GET.get('CHECKBOXLIST')
            if checkboxes:
                checkboxes = checkboxes.split(',')

        except KeyError, e:
            return HttpResponseBadRequest('missing required parameter: %s' % e)

        layar_response = dict(hotspots=[], layer=layer_name, errorCode=0,
                          errorString='ok', nextPageKey=None, morePages=False)

        try:

            # verify hash
            if self.verify_hash:
                key = self.developer_key + timestamp
                if sha1(key).hexdigest() != developer_hash:
                    raise LayarException(20, 'Bad developerHash')

            # get ``max_results`` items from queryset
            try:
                qs_func = getattr(self, 'get_%s_queryset' % layer_name)
            except AttributeError:
                raise LayarException(21, 'no such layer: %s' % layer_name)

            qs = qs_func(latitude=lat, longitude=lon, radius=radius,
                         radio_option=radio_option, search_query=search,
                         search_query2=search2, search_query3=search3,
                         slider_value=slider, slider_value2=slider2,
                         slider_value3=slider3, checkboxes=checkboxes)
            qs = qs[:self.max_results]

            # do pagination if results_per_page is set
            if self.results_per_page:
                start_index = self.results_per_page * page
                end_index = start_index + self.results_per_page

                # if there are more pages, indicate that in response
                if end_index < qs.count()-1:
                    layar_response['morePages'] = True
                    layar_response['nextPageKey'] = str(page+1)

                qs = qs[start_index:end_index]

            # convert queryset into POIs
            try:
                poi_func = getattr(self, 'poi_from_%s_item' % layer_name)
            except AttributeError:
                raise LayarException(21, 'no such layer: %s' % layer_name)

            pois = [poi_func(item) for item in qs]
            layar_response['hotspots'] = [poi.to_dict() for poi in pois]

            # if radius wasn't sent pass back the radius used
            if not radius:
                layar_response['radius'] = self.default_radius

        except LayarException, e:
            layar_response['errorCode'] = e.code
            layar_response['errorString'] = e.message

        content = json.dumps(layar_response)
        return HttpResponse(content,
                content_type='application/javascript; charset=utf-8')
