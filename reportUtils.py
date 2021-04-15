'''
Created on Aug 18, 2020

@author: laura
'''

import requests
from io import StringIO
import pandas as pd
import numpy as np
import time
# from matplotlib.contour import ClabelText
import urllib
import re



def getAvailability(snclqs, startDate, endDate, tolerance):
    
    availabilityDF = pd.DataFrame()
    services = []
    for snclq in snclqs:
        snclqList = snclq.split('.')
        n =snclqList[0]
        s = snclqList[1]
        l = snclqList[2]
        if l == '':
            luse = '--'
        else:
            luse = l
        c = snclqList[3]
        q = snclqList[4]
        
        
        if q == "M":
            service = "fdsnws"
        elif q == "D":
            service = "ph5ws"
        
        if service not in services:
            services.append(service)
            
        URL = f'http://service.iris.edu/{service}/availability/1/query?format=text&' \
              f'net={n}&sta={s}&loc={luse}&cha={c}&quality={q}&' \
              f'starttime={startDate}&endtime={endDate}&orderby=nslc_time_quality_samplerate&' \
              f'mergegaps={tolerance}&includerestricted=true&nodata=404' 
           
        try:   
            tmpDF = pd.read_csv(URL, sep=' ', dtype={'Location': str, 'Station': str}, parse_dates=['Earliest','Latest'])
            tmpDF['staloc'] = f'{s}.{luse}'
        except:
            pass
        
        try:
            availabilityDF = availabilityDF.append(tmpDF, ignore_index=True)
        except:
            pass
            
       
#     availabilityDF = availabilityDF.apply(lambda x: x.str.strip() if x.dtype == "object" else x)   
    availabilityDF.rename(columns=lambda x: x.strip().lower(), inplace=True)
    availabilityDF.rename(columns = {'#network': 'network'}, inplace=True)
    
    return availabilityDF, services 
        

def retrieveMetrics(URL, metric):
    response = requests.get(URL) 
    tempDF = pd.read_csv(StringIO(response.text), header=1)
    tempDF.rename(columns={'target':'snclq'}, inplace=True)
    tempDF['target'] = tempDF['snclq'].apply(lambda x: '.'.join(x.split('.')[0:4]))
    tempDF['station'] = tempDF['snclq'].apply(lambda x: '.'.join(x.split('.')[1:3]))    ## Because "station" is really "station.location"    
    tempDF['station'] = [x + '--' if x.endswith('.') else x for x in tempDF['station'] ]
        
    if (not metric == 'transfer_function') and (not metric == 'orientation_check'):
            tempDF.rename(columns = {'value': metric}, inplace=True)
            tempDF[metric] = tempDF[metric].map(float)
    tempDF.drop('lddate', axis=1, inplace=True)

    tempDF['start'] = pd.to_datetime(tempDF['start'])
    tempDF['end'] = pd.to_datetime(tempDF['end'])
    
    return tempDF

def addMetricToDF(metric, DF, network, stations, locations, channels, startDate, endDate):
    if not (metric== 'ts_percent_availability_total' or metric == 'percent_availability'):
        print(f"        Retrieving {metric}")
    chanList = list()
    for chan in channels.split(','):
        if len(chan) == 2:
            chan = f"{chan}Z,{chan}3"
        if chan == "*":
            chan = "??Z,??3"
        chanList.append(chan)
    
    URL = f"http://service.iris.edu/mustang/measurements/1/query?metric={metric}&net={network}&" \
          f"sta={','.join(stations)}&loc={','.join(locations)}&chan={','.join(chanList)}" \
          f'&format=text&timewindow={startDate},{endDate}&nodata=404'

    try:
        tempDF = retrieveMetrics(URL, metric)
    except Exception as e:
        if not metric== 'ts_percent_availability_total':
            print(f"         --> Unable to get measurements for {metric}, waiting 5 seconds and trying again")
            print(f"             {URL}")
#             print(f"     {e}")
        time.sleep(5)
        try:
            tempDF = retrieveMetrics(URL, metric)
        except:
            if not metric== 'ts_percent_availability_total':
                print(f"         --> Still unable to get measurements for {metric}, bypassing" )
            tempDF = pd.DataFrame()
    
   
    if DF.empty:
        DF = tempDF.copy()
    else:
        try:
            DF = pd.merge(DF, tempDF, how='outer', left_on=['target','snclq', 'station', 'start', 'end'], right_on=['target','snclq','station', 'start', 'end'])
        except:
            print(f"    ERROR: Something went wrong with the {metric}")
        
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
            chan = f"{chan}Z,{chan}3"
        if chan == "*":
            chan = "??Z,??3"
        chanList.append(chan)
     

    try:
        # Call Fed Catalog to know what service the network can be retrieved using. 
        print("        Calling on Fed Catalog")
        fedURL = f"http://service.iris.edu/irisws/fedcatalog/1/query?" \
                 f"net={network}&sta={stations}&loc={locations}&cha={','.join(chanList)}&" \
                 f"starttime={startDate}&endtime={endDate}" \
                 f"&format=request&includeoverlaps=false"
        
        try:
            with urllib.request.urlopen(fedURL) as response:
                    html_content = response.read().decode('utf-8')
            
            services = []
            for ln in html_content.split('\n'):
                if ln.startswith("STATIONSERVICE="):
                    serviceURL = ln.split('=')[1]
                    if 'iris' in serviceURL:
                        services.append(serviceURL)
            
        except Exception as e:
            print("        ERROR: unable to retrieve fed catalog information about where the data lives - %s\n%s " % (fedURL, e))
            services = ['http://service.iris.edu/fdsnws/station/1/', 'http://service.iris.edu/ph5ws/station/1/']
        
        for service in services:
            # To prevent needing to know a priori where it's from, try both and only add if attempt is successful
            # Most experiments are one-archive only, but some have been split in the past
            try:
                print("        Calling on Station Service")
                stationURL = f"{service}query?" \
                             f"net={network}&sta={stations}&loc={locations}&cha={','.join(chanList)}&" \
                             f"starttime={startDate}&endtime={endDate}&level={level}" \
                             f"&format=text&includecomments=true&nodata=404" 

                if level == 'channel':
                    try:
                        tmpDF = pd.read_csv(stationURL, sep='|', dtype={' Location ': str, ' Station ': str})
                        tmpDF.rename(columns=lambda x: x.strip(), inplace=True)
                        tmpDF.rename(columns = {'#Network': 'Network'}, inplace=True)
                        tmpDF['Location'] = tmpDF.Location.replace(np.nan, '', regex=True)
                        tmpDF['Target'] = tmpDF[['Network', 'Station', 'Location','Channel']].apply(lambda x: '.'.join(x.map(str)), axis=1)
                        tmpDF.columns = tmpDF.columns.str.lower()
                         
                        tmpDF['starttime'] = pd.to_datetime(tmpDF['starttime'])
                        tmpDF['endtime'] = pd.to_datetime(tmpDF['endtime'])
                        
                    except Exception as e:
                        print(f"    ERROR: Unable to retrieve channel information from {stationURL}")
                
                elif level == 'station': 
                    try:
                        tmpDF = pd.read_csv(stationURL, sep='|')
                        tmpDF.rename(columns=lambda x: x.strip(), inplace=True)
                    except:
                        print(f"        ERROR: Unable to retrieve channel information from {stationURL}")

            except:
                tmpDF = pd.DataFrame()
                 
            stationDF = pd.concat([stationDF, tmpDF], ignore_index=True)
    except:
        print("    ERROR: Unable to retrieve metadata")        
        return stationDF
     
    return stationDF

def retrieveExpectedPDFs(smallestNSLC, startDate, endDate):
    URL = f'http://service.iris.edu/mustang/noise-pdf-browser/1/availability?target={smallestNSLC}?.*&starttime={startDate}&endtime={endDate}&interval=all'
#     print(URL)
    response =  requests.get(URL) 
    if response.text.startswith("Error"):
        # Wait 5 seconds and try again
        print(f"--> Error retrieving list of expected PDFs for {smallestNSLC}, waiting 5 seconds and trying again")
        time.sleep(5)
        response =  requests.get(URL) 
        if response.text.startswith("Error"):
            print(f"--> Unable to retrieve PDF list for {smallestNSLC}")
            print(response.text)
            expectedTargets = list()
        
    # doing it this way so that this section will run if either the first or second attempt was successful        
    if not response.text.startswith("Error"): 
        expectedTargets = [x.split(',')[0] for x in response.text.split('\n') if not x == '']
        
    return expectedTargets

def getPDF(target, startDate, endDate, spectPowerRange, imageDir):
    URL = f"http://service.iris.edu/mustang/noise-pdf/1/query?target={target}&" \
          f"starttime={startDate}&endtime={endDate}&format=plot&plot.interpolation=bicubic&nodata=404&" \
          f"plot.power.min={spectPowerRange[0]}&plot.power.max={spectPowerRange[1]}"

    response = requests.get(URL)
    filename = (f"{imageDir}/{target}_PDF.png").replace('*','').replace('?','')
    
    file = open(filename, "wb")
    file.write(response.content)
    file.close()
    
    return filename
    
def getSpectrogram(target, startDate, endDate, spectPowerRange, spectColorPalette, imageDir):
    powerRange = ','.join([str(x) for x in spectPowerRange])
    URL = f"http://service.iris.edu/mustang/noise-spectrogram/1/query?target={target}&" \
          f"starttime={startDate}&endtime={endDate}&output=power&format=plot&plot.color.palette={spectColorPalette}&" \
          f"plot.powerscale.range={powerRange}&plot.horzaxis=time&plot.time.matchrequest=true&" \
          f"plot.time.tickunit=auto&plot.time.invert=false&plot.powerscale.show=true&plot.powerscale.orientation=horz&nodata=404" 
    
    
    response = requests.get(URL)
    filename = f"{imageDir}/{target}_spectrogram.png"
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
        ZOOM_MAX = 16
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
    
    
def getMetricLabel(metric):
    metricLabels = {'amplifier_saturation':'daily flag count \n(number of occurrences)',
                     'calibration_signal':'daily flag count \n(number of occurrences)',
                     'clock_locked':'daily flag count \n(number of occurrences)',
                     'cross_talk':'correlation coefficient \n', # no units
                     'data_latency':'latency (seconds) \n',
                     'dc_offset':'daily indicator of likelihood of \nDC offset shift', # no units
                     'dead_channel_gsn':'indicator \n',
                     'dead_channel_lin':'standard deviation of residuals (dB) \n',
                     'digital_filter_charging':'daily flag count \n(number of occurrences)',
                     'digitizer_clipping':'daily flag count \n(number of occurrences)',
                     'event_begin':'daily flag count \n(number of occurrences)',
                     'event_end':'daily flag count \n(number of occurrences)',
                     'event_in_progress':'daily flag count \n(number of occurrences)',
                     'feed_latency':'latency (seconds) \n',
                     'gap_list':'daily gap length \n(seconds)',
                     'glitches':'daily flag count \n(number of occurrences)',
                     'max_gap':'daily maximum gap length \n(seconds)',
                     'max_overlap':'daily overlap length \n(seconds)',
                     'max_range':'daily maximum amplitude range, \nwindowed (counts)',
                     'max_stalta':'daily \nshort-term average / long-term \naverage', # no units
                     'missing_padded_data':'daily flag count \n(number of occurrences)',
                     'num_gaps':'daily gap count \n(number of occurrences)',
                     'num_overlaps':'daily overlap count \n(number of occurrences)',
                     'num_spikes':'daily outlier count \n(number of occurrences)',
                     'pct_above_nhnm':'daily PDF matrix above \nNew High Noise Model (%)',
                     'pct_below_nlnm':'daily PDF matrix below \nNew Low Noise Model (%)',
                     'percent_availability':'daily availability (%) \n',
                     'polarity_check':'maximum cross-correlation \nfunction', # no units
                     'pressure_effects':'daily zero-lag \ncross-correlation function', # no units
                     'sample_max':'daily maximum amplitude \n(counts)',
                     'sample_mean':'daily mean amplitude \n(counts)',
                     'sample_median':'daily median amplitude \n(counts)',
                     'sample_min':'daily minimum amplitude \n(counts)',
                     'sample_rate_channel':'daily indicator \n',
                     'sample_rate_resp':'daily indicator \n',
                     'sample_rms':'daily root-mean-square variance (counts) \n',
                     'scale_corrected_sample_rms':'daily root-mean-squared variance,\nscaled by sensitivity',
                     'sample_snr':'signal-to-noise ratio \n', # no units
                     'sample_unique':'daily unique sample values \n(number of occurrences)',
                     'spikes':'daily flag count \n(number of occurrences)',
                     'suspect_time_tag':'daily flag count \n(number of occurrences)',
                     'telemetry_sync_error':'daily flag count \n(number of occurrences)',
                     'timing_correction':'daily flag count \n(number of occurrences)',
                     'timing_quality':'daily average timing quality (%) \n',
                     'total_latency':'latency (seconds) \n',
                     'ts_num_gaps':'daily gap count \n(number of occurrences)',
                     'ts_num_gaps_total':'gap count \n(number of occurrences)',
                     'ts_max_gap':'daily maximum gap length \n(seconds)',
                     'ts_max_gap_total':'maximum gap length \n(seconds)',
                     'ts_gap_length':'daily total gap length \n(seconds)',
                     'ts_gap_length_total':'total gap length (seconds) \n',
                     'ts_percent_availability':'daily availability (%) \n',
                     'ts_percent_availability_total':'availability (%) \n',
                     'ts_channel_up_time':'daily trace segment length \n(seconds)',
                     'ts_channel_continuity':'trace segment length (seconds) \n',
                     'gain_ratio':'data/metadata gain ratio', # no units
                     'phase_diff':'data-metadata phase difference \n(degrees)',
                     'ms_coherence':'coherence function \n', # no units
                     }
    
    labelText = metricLabels[metric]
    return labelText
