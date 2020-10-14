'''
Created on Aug 18, 2020

@author: laura
'''

import requests
from io import StringIO
import pandas as pd
import numpy as np
import time


def retrieveMetrics(URL, metric):
    response = requests.get(URL) 
    tempDF = pd.read_csv(StringIO(response.text), header=1)
    tempDF.rename(columns={'target':'snclq'}, inplace=True)
    tempDF['target'] = tempDF['snclq'].apply(lambda x: '.'.join(x.split('.')[0:4]))
    tempDF['station'] = tempDF['snclq'].apply(lambda x: '.'.join(x.split('.')[1:3]))
    
    if (not metric == 'transfer_function') and (not metric == 'orientation_check'):
            tempDF.rename(columns = {'value': metric}, inplace=True)
            tempDF[metric] = tempDF[metric].map(float)
    tempDF.drop('lddate', axis=1, inplace=True)

    tempDF['start'] = pd.to_datetime(tempDF['start'])
    tempDF['end'] = pd.to_datetime(tempDF['end'])
    
    return tempDF

def addMetricToDF(metric, DF, network, stations, locations, channels, startDate, endDate):
    print("   " + metric)
    chanList = list()
    for chan in channels.split(','):
        if len(chan) == 2:
            chan = chan + "Z"
        if chan == "*":
            chan = "??Z"
        chanList.append(chan)
    
    URL = "http://service.iris.edu/mustang/measurements/1/query?metric=%s&net=%s&sta=%s&loc=%s&chan=%s&format=text&timewindow=%s,%s&nodata=404" % (metric, network, ','.join(stations), ','.join(locations), ','.join(chanList), startDate, endDate)
    
    try:
        tempDF = retrieveMetrics(URL, metric)
    except:
        print("     --> Unable to get measurements for %s, waiting 5 seconds and trying again" % (metric))
        time.sleep(5)
        try:
            tempDF = retrieveMetrics(URL, metric)
        except:
            print("     --> Still unable to get measurements for %s, bypassing" % (metric))
            tempDF = pd.DataFrame()
    
   
    if DF.empty:
        DF = tempDF.copy()
    else:
        try:
            DF = pd.merge(DF, tempDF, how='outer', left_on=['target','snclq', 'station', 'start', 'end'], right_on=['target','snclq','station', 'start', 'end'])
        except:
            print("ERROR: Something went wrong with the %s" % metric)
        
    return DF
        
def getMetadata(network, stations, locations, channels, startDate, endDate, level):
    # This one and getStations are almost redundant, except that they return at different
    # levels. Merge into one function that also takes level as an input?
     
    if level == 'channel':
        stationDF = pd.DataFrame()
    if level == 'station':
        stationDF = pd.DataFrame(columns=['#Network', 'Station', 'Latitude' , 'Longitude' , 'Elevation' , 'SiteName' , 'StartTime' , 'EndTime'])

     
    chanList = list()
    for chan in channels.split(','):
        if len(chan) == 2:
            chan = chan + "Z"
        if chan == "*":
            chan = "??Z"
        chanList.append(chan)
     
    

    try:
        for service in ['fdsnws', 'ph5ws']:
            # To prevent needing to know a priori where it's from, try both and only add if attempt is successful
            # Most experiments are one-archive only, but some have been split in the past
            try:
                stationURL = "http://service.iris.edu/%s/station/1/query?net=%s&sta=%s&loc=%s&cha=%s&starttime=%s&endtime=%s&level=%s&format=text&includecomments=true&nodata=404" % (service, network, ','.join(stations), ','.join(locations), ','.join(chanList), startDate, endDate, level)
                
                if level == 'channel':
                    tmpDF = pd.read_csv(stationURL, sep='|', dtype={' Location ': str})
                    tmpDF.rename(columns=lambda x: x.strip(), inplace=True)
                    tmpDF.rename(columns = {'#Network': 'Network'}, inplace=True)
                    tmpDF['Location'] = tmpDF.Location.replace(np.nan, '', regex=True)
                    tmpDF['Target'] = tmpDF[['Network', 'Station', 'Location','Channel']].apply(lambda x: '.'.join(x.map(str)), axis=1)
                    tmpDF.columns = tmpDF.columns.str.lower()
                     
                    tmpDF['starttime'] = pd.to_datetime(tmpDF['starttime'])
                    tmpDF['endtime'] = pd.to_datetime(tmpDF['endtime'])
                
                elif level == 'station': 
                    tmpDF = pd.read_csv(stationURL, sep='|')
                    tmpDF.rename(columns=lambda x: x.strip(), inplace=True)

            except:
                tmpDF = pd.DataFrame()
                 
            stationDF = pd.concat([stationDF, tmpDF], ignore_index=True)
    except:
        print("ERROR: Unable to retrieve metadata")        
        return stationDF
     
    return stationDF

def retrieveExpectedPDFs(smallestNSLC, startDate, endDate):
    URL = 'http://service.iris.edu/mustang/noise-pdf-browser/1/availability?target=%s?.*&starttime=%s&endtime=%s&interval=all' % (smallestNSLC,startDate, endDate)
#     print(URL)
    response =  requests.get(URL) 
    if response.text.startswith("Error"):
        # Wait 5 seconds and try again
        print("--> Error retrieving list of expected PDFs for %s, waiting 5 seconds and trying again" % smallestNSLC)
        time.sleep(5)
        response =  requests.get(URL) 
        if response.text.startswith("Error"):
            print("--> Unable to retrieve PDF list for %s" % smallestNSLC)
            print(response.text)
            expectedTargets = list()
        
    # doing it this way so that this section will run if either the first or second attempt was successful        
    if not response.text.startswith("Error"): 
        expectedTargets = [x.split(',')[0] for x in response.text.split('\n') if not x == '']
        
    return expectedTargets

def getPDF(target, startDate, endDate, spectPowerRange, imageDir):
    URL = "http://service.iris.edu/mustang/noise-pdf/1/query?target=%s&starttime=%s&endtime=%s&format=plot&plot.interpolation=bicubic&nodata=404&plot.power.min=%s&plot.power.max=%s" % (target, startDate, endDate, spectPowerRange[0], spectPowerRange[1])
#     URL = "http://service.iris.edu/mustang/noise-pdf/1/query?target=%s&starttime=%s&endtime=%s&format=plot&plot.interpolation=bicubic&nodata=404" % (target, startDate, endDate)

    response = requests.get(URL)
    filename = ("%s/%s_PDF.png" % (imageDir, target)).replace('*','').replace('?','')
    
    file = open(filename, "wb")
    file.write(response.content)
    file.close()
    
    return filename
    
def getSpectrogram(target, startDate, endDate, spectPowerRange, spectColorPalette, imageDir):
    powerRange = ','.join([str(x) for x in spectPowerRange])
    URL = "http://service.iris.edu/mustang/noise-spectrogram/1/query?target=%s&starttime=%s&endtime=%s&output=power&format=plot&plot.color.palette=%s&plot.powerscale.range=%s&plot.horzaxis=time&plot.time.matchrequest=true&plot.time.tickunit=auto&plot.time.invert=false&plot.powerscale.show=true&plot.powerscale.orientation=horz&nodata=404" % (target, startDate, endDate, spectColorPalette, powerRange)
    response = requests.get(URL)
    filename = "%s/%s_spectrogram.png" % (imageDir, target)
    file = open(filename, "wb")
    file.write(response.content)
    file.close()
    
    return filename


def getBoundsZoomLevel(bounds, mapDim):

        """
        source: https://stackoverflow.com/questions/6048975/google-maps-v3-how-to-calculate-the-zoom-level-for-a-given-bounds
        :param bounds: list of ne and sw lat/lon
        :param mapDim: dictionary with image size in pixels
        :return: zoom level to fit bounds in the visible area
        """
        n_lat = bounds[0]
        w_long = bounds[1]
        s_lat = bounds[2]
        e_long = bounds[3]
    
        scale = 2 # adjustment to reflect MapBox base tiles are 512x512 vs. Google's 256x256
        WORLD_DIM = {'height': 256 * scale, 'width': 256 * scale}
        ZOOM_MAX = 20
        ZOOM_MIN = 0.5
    
        def latRad(lat):
            sin = np.sin(lat * np.pi / 180)
            radX2 = np.log((1 + sin) / (1 - sin)) / 2
            return max(min(radX2, np.pi), -np.pi) / 2
    
        def zoom(mapPx, worldPx, fraction):
            return np.floor(np.log(mapPx / worldPx / fraction) / np.log(2))
    
        latFraction = (latRad(n_lat) - latRad(s_lat)) / np.pi
    
        lngDiff = e_long - w_long
        lngFraction = ((lngDiff + 360) if lngDiff < 0 else lngDiff) / 360
    
        latZoom = zoom(mapDim['height'], WORLD_DIM['height'], latFraction)
        lngZoom = zoom(mapDim['width'], WORLD_DIM['width'], lngFraction)
        return min(max(latZoom, lngZoom, ZOOM_MIN), ZOOM_MAX)
    
    