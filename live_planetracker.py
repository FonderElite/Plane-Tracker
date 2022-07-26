import requests,json,pandas,random
from tabulate import tabulate
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import shapely.geometry as sgeom
from bokeh.plotting import figure, show
from bokeh.tile_providers import get_provider,STAMEN_TERRAIN,Vendors,ESRI_IMAGERY
from bokeh.models import HoverTool,LabelSet,ColumnDataSource
from bokeh.plotting import figure,curdoc
from bokeh.server.server import Server
from bokeh.application import Application
from bokeh.application.handlers.function import FunctionHandler
import numpy as np
lon_min,lat_min=-125.974,30.038
lon_max,lat_max=-68.748,52.214
user = ""
passwd = ""
url_data='https://' + user + passwd + '@opensky-network.org/api/states/all?lamin='+str(lat_min)+'&lomin='+str(lon_min)+'&lamax='+str(lat_max)+'&lomax='+str(lon_max)
response = requests.get(url_data).json()
#LOAD TO PANDAS DATAFRAME
doc = curdoc()
col_name=['icao24','callsign','origin_country','time_position','last_contact','long','lat','baro_altitude','on_ground','velocity',
'true_track','vertical_rate','sensors','geo_altitude','squawk','spi','position_source']
flight_df=pandas.DataFrame(response['states'])
flight_df=flight_df.loc[:,0:16]
flight_df.columns=col_name
flight_df=flight_df.fillna('No Data') #replace NAN with No Data
planes = flight_df.sort_values(by="time_position",ascending=False).head(10)

x = [9,3,4,1,4,5]
y = [13,24,5,2,1,3]

#FUNCTION TO CONVERT GCS WGS84 TO WEB MERCATOR
#DATAFRAME
def wgs84_to_web_mercator(df, lon="long", lat="lat"):
    k = 6378137
    df["x"] = df[lon] * (k * np.pi/180.0)
    df["y"] = np.log(np.tan((90 + df[lat]) * np.pi/360.0)) * k
    return df

#POINT
def wgs84_web_mercator_point(lon,lat):
    k = 6378137
    x= lon * (k * np.pi/180.0)
    y= np.log(np.tan((90 + lat) * np.pi/360.0)) * k
    return x,y


#COORDINATE CONVERSION
xy_min=wgs84_web_mercator_point(lon_min,lat_min)
xy_max=wgs84_web_mercator_point(lon_max,lat_max)

#COORDINATE RANGE IN WEB MERCATOR
x_range,y_range=([xy_min[0],xy_max[0]], [xy_min[1],xy_max[1]])

class PlaneTracker(object):
    k = 6378137
    def __init__(self,lon_min,lat_min,lon_max,lat_max):
        self.lon_min = lon_min
        self.lat_min = lon_min
        self.lon_max = lon_max
        self.lat_max = lat_max 
    def tabulize(self):
        lon_min,lat_min=-self.lon_min,self.lat_min
        lon_max,lat_max=-self.lon_max,self.lat_max
        #REQUEST TO REST API QUERY
        self.readings = flight_df[flight_df.icao24.isin(planes.icao24.str.lower())]
        self.latitude = self.readings['lat']
        self.longitude = self.readings['long']
        self.flights = self.readings.groupby(['last_contact','icao24'])
        #Show Table
        self.table = tabulate(planes,headers=col_name,tablefmt="psql")
        print(self.table)
    @staticmethod
    def flight_tracking(doc):
     # init bokeh column data source
        flight_source = ColumnDataSource({
        'icao24':[],'callsign':[],'origin_country':[],
        'time_position':[],'last_contact':[],'long':[],'lat':[],
        'baro_altitude':[],'on_ground':[],'velocity':[],'true_track':[],
        'vertical_rate':[],'sensors':[],'geo_altitude':[],'squawk':[],'spi':[],'position_source':[],'x':[],'y':[],
        'rot_angle':[],'url':[]
    })
        def update():
            response=requests.get(url_data).json() 
#LOAD TO PANDAS DATAFRAME
            col_name=['icao24','callsign','origin_country','time_position','last_contact','long','lat','baro_altitude','on_ground','velocity',
    'true_track','vertical_rate','sensors','geo_altitude','squawk','spi','position_source']
            flight_df=pandas.DataFrame(response['states'])
            flight_df=flight_df.loc[:,0:16]
            flight_df.columns=col_name
            flight_df=flight_df.fillna('No Data') #replace NAN with No Data
            flight_df['rot_angle']=flight_df['true_track']*-1
            icon_url='https://logosandtypes.com/wp-content/uploads/2021/04/Bokeh.png'
            flight_df['url']=icon_url
            planes_sort = flight_df.sort_values(by="time_position",ascending=False).head(100)
           
            # CONVERT TO BOKEH DATASOURCE AND STREAMING
            n_roll=len(flight_df.index)
            flight_source.light_source.stream(planes_sort.to_dict(orient='list'),n_roll)
        
        #CALLBACK UPATE IN AN INTERVAL
        doc.add_periodic_callback(update, 5000) #5000 ms/10000 ms for registered user .

        #PLOT AIRCRAFT POSITION
        p=figure(x_range=x_range,y_range=y_range,x_axis_type='mercator',y_axis_type='mercator',sizing_mode='scale_width',plot_height=300)
        tile_prov=get_provider(STAMEN_TERRAIN)
        p.add_tile(tile_prov,level='image')
        p.image_url(url='url', x='x', y='y',source=flight_source,anchor='center',angle_units='deg',angle='rot_angle',h_units='screen',w_units='screen',w=40,h=40)
        p.circle('x','y',source=flight_source,fill_color='red',hover_color='yellow',size=10,fill_alpha=0.8,line_width=0)

        #ADD HOVER TOOL AND LABEL
        my_hover=HoverTool()
        my_hover.tooltips=[('Call sign','@callsign'),('Origin Country','@origin_country'),('velocity(m/s)','@velocity'),('Altitude(m)','@baro_altitude')]
        labels = LabelSet(x='x', y='y', text='callsign', level='glyph',
            x_offset=5, y_offset=5, source=flight_source, render_mode='canvas',background_fill_color='white',text_font_size="8pt")
        p.add_tools(my_hover)
        p.add_layout(labels)
    
        doc.title='REAL TIME FLIGHT TRACKING'
        doc.add_root(p)
        


if __name__ == "__main__":
    tracker = PlaneTracker(125.974,30.038,68.748,52.214)
    show_table = tracker.tabulize()
    #call = tracker.flight_tracking(doc)
    # SERVER CODE
    apps = {'/': Application(FunctionHandler(tracker.flight_tracking))}
    server = Server(apps, port=8000) #define an unused port
    server.start()
