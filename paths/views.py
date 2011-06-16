# Create your views here.

from django.contrib.gis.geos import Point
from paths.models import PointOfInterest, Action, TypeOfAction
from layar import LayarView, POI
from math import *
from django.conf import settings 
from django.db import connection, transaction, models

class BoerenommetjeLayar(LayarView):

    def get_boerenommetje_queryset(self, latitude, longitude, radius, **kwargs):
#		haversine = (((acos(sin((:latitude1 * math.pi / 180)) * sin((latitude * math.pi / 180)) +
#                  	   cos((:latitude2 * math.pi / 180)) * cos((latitude * math.pi / 180)) * 
#                       cos((:longitude  - longitude) * math.pi / 180))
#                      ) * 180 / math.pi) * 60 * 1.1515 * 1.609344 * 1000)
#        return PointOfInterest.objects.filter()#haversine(self.lat, self.lon, self.radius))
#        return PointOfInterest.objects.filter(location__distance_lt=(Point(longitude, latitude), radius)) ###

        cursor = connection.cursor()
        sql = """SELECT id, lat, lon FROM paths_pointofinterest WHERE
                 (6371 * acos (cos( radians(%f) ) * cos( radians( lat ) ) *
                 cos( radians( lon ) - radians(%f) ) + sin( radians(%f) ) *
                 sin( radians( lat ) ) ) ) < %d LIMIT 0, 20;""" % (latitude, longitude, latitude, int(radius))
        cursor.execute(sql)
        ids = [row[0] for row in cursor.fetchall()]
        return PointOfInterest.objects.filter(id__in=ids)

	def poi_from_boerenommetje_item(self, item):
		return POI(id=item.id, lat=item.lat, lon=item.lon, title=item.title, line2=item.line2, line3='Distance: %distance%')

	def get_action(Action, self):
		cursor = connection.cursor()
		poi_selected = get_boerenommetje_queryset(self, latitude, longitude, radius)
		action = """SELECT label, url, autoTriggerRange, autoTriggerOnly, method, 
                    params, closeBiw, showActivity, activityMessage
                    FROM paths_action WHERE pointofi_id = id"""
		return PointOfInterest.action_set()        

# create an instance of BoerenommetjeLayar
boerenommetje_layar = BoerenommetjeLayar()
