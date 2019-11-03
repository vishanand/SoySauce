from flask import Flask, request, render_template
from flask_restful import Resource, Api
from sqlalchemy import create_engine
from json import dumps
import arrow
from geojson import Point, Feature, FeatureCollection, dump
from collections import defaultdict


#Create a engine for connecting to SQLite3.
#Assuming salaries.db is in your app root folder

e = create_engine('sqlite:///energy.db')

app = Flask(__name__, static_url_path='', static_folder='static',template_folder='templates')
api = Api(app)
buildings_meta_json = None

class Buildings_Meta(Resource):
    def get(self):
        #Connect to databse
        #Perform query and return JSON data
        conn = e.connect()

        query = conn.execute("select MeterID, BuildingID, BuildingName, Latitude, Longitude from config where Resource='Electricity' group by BuildingID")
        buildings_meta_json = {'buildings_meta': [i for i in query.cursor.fetchall()]}
        return buildings_meta_json
    
class Building_Time(Resource):
    def get(self, Time):
        conn = e.connect()

        query = conn.execute("select MeterID, BuildingID, BuildingName, Latitude, Longitude from config where Resource='Electricity' and length(Latitude) > 0 group by BuildingID")
        buildings_meta_map = defaultdict(list)
        for x in query:
            buildings_meta_map[x[0]] = x[1:]
        
        currTime = Time
        prevTime = arrow.get(currTime[:-1], 'YYYY-MM-DDTHH:mm:ss').shift(hours=-1)
        prevTime = prevTime.format('YYYY-MM-DDTHH:mm:ss') + 'Z'
        
        query = conn.execute("select MeterID, CurrentValue from hourly where Time='%s' and Units='kWh' order by MeterID"%currTime)
        
        currJSON = {'building': [i for i in query.cursor.fetchall()]}
        
        query = conn.execute("select MeterID, CurrentValue from hourly where Time='%s' and Units='kWh' order by MeterID"%prevTime)
        prevJSON = {'building': [i for i in query.cursor.fetchall()]}
        # print([currJSON])
    
        res = []
        for i in range(len(prevJSON["building"])):
            mid = currJSON["building"][i][0]
            building_data = buildings_meta_map[mid]
            print(building_data)
            if (building_data):
                point = Point((float(building_data[3]), float(building_data[2])))
                delta = (float(currJSON["building"][i][1]) - float(prevJSON["building"][i][1]))
                res.append(Feature(geometry=point, properties={"mag": 3}))
        feature_collection = FeatureCollection(res)
        with open('./static/data/geo_data.geojson', 'w') as f:
            dump(feature_collection, f)
        #We can have PUT,DELETE,POST here. But in our API GET implementation is sufficient
        return "Success"
class Building_Positions(Resource):
    def get(self):
        conn = e.connect()

        queries = conn.execute("select MeterID, Latitude, Longitude from config where Resource='Electricity' group by BuildingID").cursor.fetchall()
        geojson = {
            "type": "FeatureCollection",
            "features": [
            {
                "type": "Feature",
                "geometry" : {
                "type": "Point",
                "coordinates": [query[1], query[2],.1],
            },
            "properties" : query,
                } for query in queries],
        }
        # with open('./templates/data/geo_data.geojson', 'w') as f:
        #     dump(geojson, f)
        return geojson
api.add_resource(Building_Time, '/buildings/<string:Time>')
api.add_resource(Buildings_Meta, '/buildings')
api.add_resource(Building_Positions,'/positions')

@app.route("/")
def main():
    return render_template('index.htm', title = "Home")



if __name__ == '__main__':
     app.run()