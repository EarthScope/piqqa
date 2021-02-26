    #!/usr/bin/env python

'''
Created on Aug 18, 2020

@author: laura
'''

# version = 'v1.0'
version = 'v. 0.2'

import reportUtils

import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import collections  as mc
import matplotlib.dates as mdates
import plotly.express as px
import datetime
import sys
import os
import numpy as np
import shutil


if (len(sys.argv) == 1) or (sys.argv[1] == '--h') or (sys.argv[1] == '-h'):
    helpText = '''
    PIQQA USAGE:  python PIQQA.py --network=NET --start=YYYY-mm-dd --end=YYYY-mm-dd 
    
    Required Fields:
        --network=: network code
        --start=: start date, YYYY-mm-dd
        --end=: end date, YYYY-mm-dd; time defaults to 00:00:00, so to include all of 2020 the end date would be 2021-01-01
    Optional Fields
        --stations=: comma-separated list of station codes; defaults to "*"
        --locations=: comma-separated list of location codes; defaults to "*"
        --channels=: comma-sparated list of channel groups (HH, BH); defaults to "*"
        --metrics=: comma-separated list of metrics to run for the boxplots; defaults: ts_channel_up_time,sample_rms,num_gaps
        --maxplot=: number of stations to include in the boxplots; defaults to 30
        --colorpalette=: color palette for spectrograms; defaults to 'RdYlBu'
            options available at http://service.iris.edu/mustang/noise-spectrogram/1/
        --includeoutliers=: whether to include outliers in the boxplots, True/False; defaults to False
        --spectralrange=: power range to use in the PDFs and spectrograms, comma separated values:  min, max; defaults depend on channel type
        --basemap=: the name of the basemap to be used for the map; defaults to 'open-street-map'
    If PIQQA is not working as expected, ensure that the conda environment is activated
    '''
    quit(helpText)
    
    
# metricList = ['ts_channel_up_time', 'sample_rms', 'ts_num_gaps']
metricList = ['ts_channel_continuity','sample_rms','num_gaps']
# metricsRequired = ['percent_availability']  # can change this when ts_percent_availability is updated to ensure any metadata'd but data-less days as 0%
metricsRequired = []    # requiring percent_availability is obsolete, but leaving this as an option in case something changes in teh future. 

###### Default values
stations = "*"
locations = "*"
channels = "*"
nBoxPlotSta = 30

spectColorPalette =  'RdYlBu'
includeOutliers = False
basemap = "open-street-map"

tolerance = 60

userDefinedPowerRange = list()
powerRanges = {'BH': [-175,-75],
               'EH' : [-175,-75],
               'HH' : [-175,-75],
               'MH' : [-175,-75],
               'SH' : [-175,-75],
               'EN' : [-175,-20],
               'BN' : [-175,-20],
               'EP' : [-175,-60],
               'DP' : [-175,-60],
               'GP' : [-175,-60]}

boxplotExampleImage = './boxplot_example.png'
######

####### Overwrite defaults with values from the command line
for arg in sys.argv:
    if arg.lower().startswith('--network='):
        network = arg.split('=')[1]
    if arg.lower().startswith('--stations='):
        stations = arg.split('=')[1]
    if arg.lower().startswith('--locations='):
        locations = arg.split('=')[1]
    if arg.lower().startswith('--channels='):
        channels = arg.split('=')[1]
    if arg.lower().startswith('--start='):
        startDate = arg.split('=')[1]
    if arg.lower().startswith('--end='):
        endDate = arg.split('=')[1]
    if arg.lower().startswith('--maxplot='):
        nBoxPlotSta = int(arg.split('=')[1])
    if arg.lower().startswith('--colorpalette='):
        spectColorPalette = arg.split('=')[1]
    if arg.lower().startswith('--includeoutliers='):
        includeOutliers = arg.split('=')[1]
        if includeOutliers.lower() == "true":
            includeOutliers = True
    if arg.lower().startswith('--spectralrange='):
        userDefinedPowerRange = [x.strip() for x in arg.split('=')[1].split(',')]
    if arg.lower().startswith('--metrics='):
        metricList = [x.strip() for x in arg.split('=')[1].split(',')]
    if arg.lower().startswith('--basemap='):
        basemap = arg.split('=')[1]
#     if arg.lower().startswith('--ph5'):
#         service = 'ph5ws'


ireturn = 0
try:
    network
except:
    ireturn = 1
    print("WARNING: Network required")
try:
    startDate
except:
    ireturn = 1
    print("WARNING: Start date required")
try:
    endDate
except:
    ireturn = 1
    print("WARNING: End date required")   
try:
    startYear = datetime.datetime.strptime(startDate, '%Y-%m-%d').strftime('%Y')
except:
    ireturn = 1
    print("WARNING: could not parse start date, is it formatted correctly? YYYY-mm-dd")
try:    
    endYear = (datetime.datetime.strptime(endDate, '%Y-%m-%d') - datetime.timedelta(days=1)).strftime('%Y') 
except:
    ireturn = 1
    print("WARNING: could not parse end date, is it formatted correctly? YYYY-mm-dd")
if ireturn == 1:
    quit("INFO: Exiting PIQQA")
 
 
print("INFO: Beginning Report at " + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
   
    
# sample_rms is required in order to be able to find the least/greatest rms stations, so if it is
# not already in the metric list then it must be added.    
if 'sample_rms' not in metricList:
    print("INFO: adding sample_rms to the metric list")
    metricList.append('sample_rms')

# If any metrics from metricsRequired (just percent_availability now) are in the metricList, then 
# remove them from metricsRequired. 
metricsRequired = [x for x in metricsRequired if x not in metricList]

######        
 
# Manage directories and filenames       

if startYear == endYear:
    outfile = f'{network}_{startYear}.html'
    outdir = f'{network}_{startYear}'
else:
    outfile = f'{network}_{startYear}-{endYear}.html'       
    outdir = f'{network}_{startYear}-{endYear}'

# Create directory for this network/year(s)
if not os.path.isdir(outdir):
    print(f"INFO: Creating directory {outdir}/")
    os.makedirs(outdir)

# Copy the boxplot example image into the image direcoty
boxPlotExampleImage_moved = outdir + '/' + boxplotExampleImage
try:
    shutil.copyfile(boxplotExampleImage, boxPlotExampleImage_moved)
except:
    print(f"WARNING: could not find boxplot example image - {boxplotExampleImage}")
os.chdir(outdir)    

# Put the figures all together in a subdirectory
imageDir = 'images'
if not os.path.isdir(imageDir):
    print(f"INFO: Creating subdirectory {imageDir}/")
    os.makedirs(imageDir)

boxPlotExampleImage_moved = f'{imageDir}/{boxplotExampleImage}'
try:
    shutil.move(boxplotExampleImage, boxPlotExampleImage_moved)
except:
    print(f"WARNING: could not find boxplot example image - {boxplotExampleImage}")

mapFilename = f'{imageDir}/{network}_stationMap.html'

# For testing and debugging
doAvailability = 1
doBoxPlots = 1
doPDFs = 1
doSpectrograms = 1
doMap = 1
doReport = 1

########
########



splitPlots = 0  # if there are more stations than nBoxPlotSta, for any channel group, then this will be switched to 1. Used in the html output 
nTop = int(nBoxPlotSta / 2)
nBottom = int(nBoxPlotSta - nTop)

## AVAILABILITY PLOT
if doAvailability:
    
    print("INFO: Producing availability plot")
    avFilesDictionary = {}  # collects plot filenames
    topStationsDict = {}    # list of stations in top X (default 15) for channel group, or all stations if the channel group is small 
    services_used = list()  # used to know which services to link to at the bottom of the availability section
    avDictionary = {}       # earliest and latest dates for each target, as well as the ts_percent_availabilty_total between those two dates.  
    
    totalElapsedTime = (datetime.datetime.fromisoformat(endDate).timestamp() -  datetime.datetime.fromisoformat(startDate).timestamp())/ 86400
    gapBuffer = 0.001    # if the gap is smaller than this percent of the total elapsed time, then it will be plotted as this percent of the total time

    # First, get availability from ts_availability_total so that it's easy to choose the top- and bottommost stations
    pctAvDF = pd.DataFrame()
    pctAvDF = reportUtils.addMetricToDF('ts_percent_availability_total', pctAvDF, network, stations, locations, channels, startDate, endDate)
    if pctAvDF.empty:
        print('WARNING: unable to retrieve values for requested channels, bypassing')
    else:   
        pctAvDF['slc'] = [ x + '.' + y for x, y  in zip([ i for i in pctAvDF['station'] ], [ i.split('.')[-1] for i in pctAvDF['target'] ]) ]  
    
        pctAvDF.sort_values(['ts_percent_availability_total','station'], inplace=True, ascending=[False,True])
        pctAvDF = pctAvDF.reset_index(drop=True)
        
        actualChannels = sorted(list(set([x[3] for x in pctAvDF['target'].str.split('.')])))
                
        
        for channelGroup in actualChannels:
            tmpDF = pctAvDF[pctAvDF['target'].str.endswith(channelGroup)]
                    
            stationList = sorted(list(set(tmpDF.slc)))
            nsta = len(stationList)
            
            if nsta > nBoxPlotSta:
                splitPlots = 1
#                 nTop = int(nBoxPlotSta / 2)
#                 nBottom = int(nBoxPlotSta - nTop)
           
                topStations = tmpDF.iloc[:nTop,:]
                bottomStations = tmpDF.iloc[-nBottom:,:]
                
        
                height = max(min(0.3*nsta, 0.3*nBoxPlotSta), 2)
                width = 15
                f, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(width, height))
        
                
                ## FOR each of the top and bottom station.locations, plot up:
                ##    1. the metadata extends for the sta.loc
                ##    2. the data extents for the sta.loc
                ##    3. the gap extents for the sta.loc
                
                topStationsAvDF, services = reportUtils.getAvailaility(topStations['snclq'], startDate, endDate, tolerance)
                for service in services:
                    if service not in services_used:
                        services_used.append(service)
                
                
                
                topStationList = topStations['station'].tolist()
                topLabels = [f'{a} ({b:.3f}%)' for a, b in zip(topStations['station'], topStations['ts_percent_availability_total']) ]
        
                topStationsDict[channelGroup] = topStationList
        
                datalines = []
                metadatalines = []
                gaplines = []
                stn = 0
                for station in topStationList:
                    # data extents and gaps extents
                    thisData = topStationsAvDF[topStationsAvDF['staloc'] == str(station)]
                    
                    
                    if len(thisData.index) > 1:
                        # then there are gaps
                        doGaps = True
                        thisGap = []
                        pullThis = 'first'
                    else:
                        doGaps = False
                        
                    for idx,line in thisData.iterrows():
                        datalines.append( [ ( mpl.dates.date2num(line['earliest']), stn ) , ( mpl.dates.date2num(line['latest']), stn ) ] )
                        
                        if doGaps:
                            if pullThis == 'first':
                                thisGap.append(( mpl.dates.date2num(line['latest']), stn ))
                                
                                pullThis = 'second'
                            else:
                                
                                # If the gap is too small, we can't see it. So force it to be a bit bigger.
                                gapStart = thisGap[0][0]
                                gapEnd = mpl.dates.date2num(line['earliest'])
                                
                                if gapEnd - gapStart < totalElapsedTime * gapBuffer:
                                    thisGap.append(( gapStart + (totalElapsedTime * gapBuffer), stn )) 
                                else:
                                    
                                    thisGap.append( ( gapEnd, stn ) ) 
                                gaplines.append(thisGap) 
                                
                                thisGap = []
                                thisGap.append(( mpl.dates.date2num(line['latest']), stn ))
                                                            
                    # metadata extents
                    thisStation = station.split('.')[0]
                    thisLocation = station.split('.')[1]
                    if thisLocation == "":
                        thisLocation = '--'
                    thisMetadata = reportUtils.getMetadata(network, [thisStation], [thisLocation], channels, startDate, endDate, "channel")
                    for idx,line in thisMetadata.iterrows():
                        metadatalines.append( [ ( mpl.dates.date2num(line['starttime']), stn ) , ( mpl.dates.date2num(line['endtime']), stn ) ] )
                        
                    stn += 1
        
        
                       
                DataLines = mc.LineCollection(datalines, linewidths=4, color=(.3,.5,.7,1)) 
                MetadataLines = mc.LineCollection(metadatalines, linewidths=10, color=(.9,.9,.9,1)) 
                GapLines = mc.LineCollection(gaplines, linewidths=12, color=(0,0,0,1))
                       
                ax1.add_collection(MetadataLines)
                ax1.add_collection(DataLines)
                ax1.add_collection(GapLines)
                ax1.autoscale()
                ax1.invert_yaxis()
                ax1.xaxis.set_minor_locator(mpl.ticker.AutoMinorLocator())
                ax1.set_yticks(np.arange(nTop))
                ax1.set_yticklabels(topLabels)
                ax1.set_xlim([mpl.dates.date2num(startDate), mpl.dates.date2num(endDate)] )
                 
                ax1.xaxis.grid(True, which='both', color='k', linestyle=':')
                    
                 
                # Do it again for the lowest stations
                bottomStationsAvDF, services = reportUtils.getAvailaility(bottomStations['snclq'], startDate, endDate, tolerance)
                for service in services:
                    if service not in services_used:
                        services_used.append(service)
                bottomStationList = bottomStations['station'].tolist()
                bottomLabels = [f'{a} ({b:.3f}%)' for a, b in zip(bottomStations['station'], bottomStations['ts_percent_availability_total']) ]
        
                datalines = []
                metadatalines = []
                gaplines = []
                
                stn = 0
                for station in bottomStationList:
        
                    # data extents and gaps extents
                    thisData = bottomStationsAvDF[bottomStationsAvDF['staloc'] == str(station)]
                    if len(thisData.index) > 1:
                        # then there are gaps
                        doGaps = True
                        thisGap = []
                        pullThis = 'first'
                    else:
                        doGaps = False
                        
                    for idx,line in thisData.iterrows():
                        dataStart = mpl.dates.date2num(line['earliest'])
                        dataEnd = mpl.dates.date2num(line['latest'])
                        
                        if (dataEnd - dataStart < totalElapsedTime * gapBuffer) and (not dataEnd - dataStart == 0):
                            # Then the line might be too small to see, so artificially enlarge it for visibility
                            datalines.append( [ (dataStart, stn ) , ( dataStart + (totalElapsedTime * gapBuffer), stn ) ] )
                        else:         
                            datalines.append( [ (dataStart, stn ) , ( dataEnd, stn ) ] )
                        
                        
                        datalines.append( [ ( mpl.dates.date2num(line['earliest']), stn ) , ( mpl.dates.date2num(line['latest']), stn ) ] )
                        
                        
                        
                        
                        if doGaps:
                            if pullThis == 'first':
                                thisGap.append(( mpl.dates.date2num(line['latest']), stn ))
                                
                                pullThis = 'second'
                            else:
                                
                                # If the gap is too small, we can't see it. So force it to be a bit bigger.
                                gapStart = thisGap[0][0]
                                gapEnd = mpl.dates.date2num(line['earliest'])
                                
                                if gapEnd - gapStart < totalElapsedTime * gapBuffer:
                                    thisGap.append(( gapStart + (totalElapsedTime * gapBuffer), stn )) 
                                else:
                                    
                                    thisGap.append( ( gapEnd, stn ) ) 
                                gaplines.append(thisGap) 
                                
                                thisGap = []
                                thisGap.append(( mpl.dates.date2num(line['latest']), stn ))
                                
                            
                    # metadata extents
                    thisStation = station.split('.')[0]
                    thisLocation = station.split('.')[1]
                    if thisLocation == "":
                        thisLocation = '--'
                    thisMetadata = reportUtils.getMetadata(network, [thisStation], [thisLocation], channels, startDate, endDate, "channel")
                    for idx,line in thisMetadata.iterrows():
                        metaStart = mpl.dates.date2num(line['starttime'])
                        metaEnd = mpl.dates.date2num(line['endtime'])
                        if metaEnd - metaStart < totalElapsedTime * gapBuffer:
                            # Then the line might be too small to see, so artificially enlarge it for visibility
                            metadatalines.append( [ (metaStart, stn ) , ( metaStart + (totalElapsedTime * gapBuffer), stn ) ] )
                        else:         
                            metadatalines.append( [ (metaStart, stn ) , ( metaEnd, stn ) ] )
                        
                    stn += 1
        
        
                       
                DataLines = mc.LineCollection(datalines, linewidths=4, color=(.3,.5,.7,1)) 
                MetadataLines = mc.LineCollection(metadatalines, linewidths=10, color=(.9,.9,.9,1)) 
                GapLines = mc.LineCollection(gaplines, linewidths=12, color=(0,0,0,1))
                 
                ax2.add_collection(MetadataLines)
                ax2.add_collection(DataLines)
                ax2.add_collection(GapLines)
                ax2.autoscale()
                ax2.invert_yaxis()
                ax2.set_yticks(np.arange(nTop))
                ax2.set_yticklabels(bottomLabels)
                ax2.set_xlim([mpl.dates.date2num(startDate), mpl.dates.date2num(endDate)] )
                
                ax2.xaxis.grid(True, which='both', color='k', linestyle=':')
                
                for nn, ax in enumerate([ax1,ax2]):
                    if totalElapsedTime < 91:
                        major = mdates.MonthLocator()   # every year
                        minor = mdates.WeekdayLocator()  # every month
                        major_fmt = mdates.DateFormatter('%b')
                        minor_fmt = mdates.DateFormatter('%d')
                    else:
                        major = mdates.YearLocator()   # every year
                        minor = mdates.MonthLocator()  # every month
                        major_fmt = mdates.DateFormatter('%Y')
                        minor_fmt = mdates.DateFormatter('%b')
        
                    ax.xaxis.set_major_locator(major)
                    ax.xaxis.set_major_formatter(major_fmt)
                    ax.xaxis.set_minor_locator(minor)
                    ax.xaxis.set_minor_formatter(minor_fmt)
                    ax.tick_params(axis="x", which="both", rotation=45)
                
                    
                ax1.set_title(f'Availability for {network}, {startDate} to {endDate}')
        
        
        
        
            else:
        
                height = max(min(0.3*nsta, 0.3*nBoxPlotSta), 2)
                width = 15
                f, ax = plt.subplots(figsize=(width, height))
        
                allStationsAvDF, services = reportUtils.getAvailaility(tmpDF['snclq'], startDate, endDate, tolerance)
                
                for service in services:
                    if service not in services_used:
                        services_used.append(service)
                allStationList = tmpDF['station'].tolist()
                allLabels = [f'{a} ({b:.3f}%)' for a, b in zip(tmpDF['station'], tmpDF['ts_percent_availability_total']) ]
                topStationsDict[channelGroup] = allStationList
                
                
                datalines = []
                metadatalines = []
                gaplines = []
                stn = 0
                for station in allStationList:
                    # data extents and gaps extents
                    thisData = allStationsAvDF[allStationsAvDF['staloc'] == str(station)]
                    if len(thisData.index) > 1:
                        # then there are gaps
                        doGaps = True
                        thisGap = []
                        pullThis = 'first'
                    else:
                        doGaps = False
                        
                    for idx,line in thisData.iterrows():
                        datalines.append( [ ( mpl.dates.date2num(line['earliest']), stn ) , ( mpl.dates.date2num(line['latest']), stn ) ] )
                        
                        if doGaps:
                            if pullThis == 'first':
                                thisGap.append(( mpl.dates.date2num(line['latest']), stn ))
                                
                                pullThis = 'second'
                            else:
                                
                                # If the gap is too small, we can't see it. So force it to be a bit bigger.
                                gapStart = thisGap[0][0]
                                gapEnd = mpl.dates.date2num(line['earliest'])
                                
                                if gapEnd - gapStart < totalElapsedTime * gapBuffer:
                                    thisGap.append(( gapStart + (totalElapsedTime * gapBuffer), stn )) 
                                else:
                                    
                                    thisGap.append( ( gapEnd, stn ) ) 
                                gaplines.append(thisGap) 
                                
                                thisGap = []
                                thisGap.append(( mpl.dates.date2num(line['latest']), stn ))
                                
        #                         pullThis = 'second'
                            
                    # metadata extents
                    thisStation = station.split('.')[0]
                    thisLocation = station.split('.')[1]
                    if thisLocation == "":
                        thisLocation = '--'
                    thisMetadata = reportUtils.getMetadata(network, [thisStation], [thisLocation], channels, startDate, endDate, "channel")
                    for idx,line in thisMetadata.iterrows():
                        metadatalines.append( [ ( mpl.dates.date2num(line['starttime']), stn ) , ( mpl.dates.date2num(line['endtime']), stn ) ] )
                        
                    stn += 1
        
        
                       
                DataLines = mc.LineCollection(datalines, linewidths=4, color=(.3,.5,.7,1)) 
                MetadataLines = mc.LineCollection(metadatalines, linewidths=10, color=(.9,.9,.9,1)) 
                GapLines = mc.LineCollection(gaplines, linewidths=12, color=(0,0,0,1))
                       
                ax.add_collection(MetadataLines)
                ax.add_collection(DataLines)
                ax.add_collection(GapLines)
                ax.autoscale()
                ax.invert_yaxis()
                ax.xaxis.set_minor_locator(mpl.ticker.AutoMinorLocator())
                ax.set_yticks(np.arange(nsta))
                ax.set_yticklabels(allLabels)
                ax.set_xlim([mpl.dates.date2num(startDate), mpl.dates.date2num(endDate)] )
                 
                ax.xaxis.grid(True, which='both', color='k', linestyle=':')
                
        
                years = mdates.YearLocator()   # every year
                months = mdates.MonthLocator()  # every month
                years_fmt = mdates.DateFormatter('%Y')
                months_fmt = mdates.DateFormatter('%b')
        
                ax.xaxis.set_major_locator(years)
                ax.xaxis.set_major_formatter(years_fmt)
                ax.xaxis.set_minor_locator(months)
                ax.xaxis.set_minor_formatter(months_fmt)
                ax.tick_params(axis="x", which="both", rotation=45)
                
                    
                ax.set_title(f'Availability for {network}, {startDate} to {endDate}')
        
            plt.tight_layout()
            avFilename = f'{imageDir}/{network}_{channelGroup}_availability.png'
    
            plt.savefig(fname=avFilename, bbox_inches="tight")
            plt.close()
    
            avFilesDictionary[f'{channelGroup}'] = avFilename





## BOXPLOTS
if doBoxPlots:
    # Retrieve metrics from mustang service
    print("INFO: Retrieving metrics from the MUSTANG webservices...")
    
    metricDF = pd.DataFrame()
    for metric in metricList:
        metricDF = reportUtils.addMetricToDF(metric, metricDF, network, stations, locations, channels, startDate, endDate)
    
    for metric in metricsRequired:
        metricDF = reportUtils.addMetricToDF(metric, metricDF, network, stations, locations, channels, startDate, endDate)
    
    if metricDF.empty:
        print(f"WARNING: No metrics retrieved for {network}.{stations}.{locations}.{channels} {startDate}-{endDate}")
        boxPlotDictionary = {}
        actualChannels = list()
    else:
#         try:
#             metricDF = metricDF[metricDF['percent_availability'] !=0]
#         except:
#             print("WARNING: Unable to subset based on percent_availabity > 0")
        
        # Create a list of all channels that actually have metrics
        actualChannels = sorted(list(set([x[3] for x in metricDF['target'].str.split('.')])))    
        actualChannelsText = ','.join(actualChannels)
        metadataDF = reportUtils.getMetadata(network, stations, locations, actualChannelsText, startDate, endDate,'channel')
        
        scaledDF= metricDF.copy()
    
        # scale sample_rms by "scale" from station ws
        if 'sample_rms' in metricList:
            print("INFO: Applying scale factor to sample_rms")

            scaledDF.rename(columns={"sample_rms" : "sample_rms_orig"}, inplace=True)
            for ind, row in metadataDF.iterrows():
                thisTarget = row['target']
                thisStart = row['starttime']
                thisEnd = row['endtime']
                if pd.isnull(thisEnd):
                    thisEnd = datetime.datetime.now()
                thisScale = row['scale']
                
                affectedRows = scaledDF.index[((scaledDF['target']==thisTarget) & (scaledDF['start'] < thisEnd) & (scaledDF['end'] > thisStart))].tolist()
                scaledDF.loc[affectedRows, 'scale_corrected_sample_rms'] = scaledDF['sample_rms_orig'][affectedRows] / thisScale
            
        
        boxPlotDictionary = {}
        for channelGroup in actualChannels:
            tmpDF = scaledDF[scaledDF['target'].str.endswith(channelGroup)]

            
            print(f'INFO: Generating Boxplots for {channelGroup}')
            grouped = tmpDF.groupby(['station'])

    #         fig, axes = plt.subplots(1, len(metricList), figsize=(3*len(metricList),  0.2*nBoxPlotSta))
            fig = plt.Figure(figsize=(3,  0.2*nBoxPlotSta))
            
            filenames = list()
            for metric in metricList:
                if metric == 'sample_rms':
                    metric = "scale_corrected_sample_rms"
                
                try:
                    # This may fail if the metric wasn't accessible from web services
                    
                    # Sort by the median value
                    df2 = pd.DataFrame({col:vals[metric] for col,vals in grouped})
                    if df2.isnull().values.all():
                        print(f"WARNING: all stations are null for {channelGroup} {metric}, bypassing")                            
                        continue
                    
#                     meds = df2.median(skipna=True)
                    meds = df2.mean(skipna=True)
                    meds.sort_values(ascending=True, inplace=True)
                    df2 = df2[meds.index]
                    stationList = sorted(list(set(df2.columns)))
                    
                    
                    # If there are too many stations, then only show the top/bottom stations
                    nsta = len(stationList)
                    height = max(min(0.3*nsta, 0.3*nBoxPlotSta), 2)
                    width = 5
                    
                    
                    if nsta > nBoxPlotSta:
                        splitPlots = 1
                        
                        f, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(width, height))
                        
                        for ax in [ax1,ax2]:
                            if ax == ax1:
                                dftmp = df2.iloc[:, nsta-nBottom:nsta]
                            elif ax == ax2:
                                dftmp = df2.iloc[:, 0:nTop]
                                
                            if includeOutliers:
                                boxplot = dftmp.boxplot( ax=ax, vert=False, grid=False, color={'medians': 'black', 'boxes':'black', 'whiskers':'black'})
                                
                            else:
                                boxplot = dftmp.boxplot( ax=ax, vert=False, grid=False, showfliers=False, color={'medians': 'black', 'boxes':'black', 'whiskers':'black'})
                        ax1.set_title(metric)
                        ax2.set_xlabel(reportUtils.getMetricLabel(metric))
                        
                        
                        try: 
                            valueRatio = max(meds) / min(meds)
                            valueRange = max(meds) - min(meds)
                            
                            if (valueRatio > 50 ) and not (min(dftmp.min()) <= 0):
                                try:
                                    ax1.set_xscale("log")
                                    ax2.set_xscale("log")
                                except:
                                    pass

                        except Exception as e:
                            print(e)
                        
                    else:
                        # Create and save the boxplot for that metric
                        
                        if includeOutliers:
                            boxplot = df2.boxplot(vert=False, grid=False, figsize=(width, height), color={'medians': 'black', 'boxes':'black', 'whiskers':'black'})
                        else:
                            boxplot = df2.boxplot(vert=False, grid=False, figsize=(width,height), showfliers=False, color={'medians': 'black', 'boxes':'black', 'whiskers':'black'})
        
                    
                        boxplot.set_title(metric)
                        boxplot.set_xlabel(reportUtils.getMetricLabel(metric))
                        
                        try: 
                            valueRatio = max(meds) / min(meds)
                            valueRange = max(meds) - min(meds)
                            
                            if (valueRatio > 50 ) and not (min(df2.min()) <= 0):
                                boxplot.set_xscale("log")
                            
                        except Exception as e:
                            print(e)
                 
                 
                    plt.tight_layout()
                    filename = f'{imageDir}/{channelGroup}_{metric}_boxplot.png'
                    plt.savefig(fname=filename, bbox_inches="tight")
                    plt.close()
                    
                    filenames.append(filename)
                       
                except Exception as e:
                    print(f"    WARNING: could not plot {metric} - {e}")
                
                
            
            boxPlotDictionary[f'{channelGroup}'] = filenames
 
    





    
## PDFs
if doPDFs:
    pdfDictionary = {}
    
    for channelGroup in actualChannels:
#         print(channelGroup)
        print(f"INFO: Retrieving PDFs for {channelGroup}")
        
        # Use the dataframe with the SCALED sample_rms to determine the top/bottom station/target        
        tmpDF = scaledDF[scaledDF['target'].str.endswith(channelGroup)]
        
        grouped = tmpDF.groupby(['snclq'])
        
        df2 = pd.DataFrame({col:vals['scale_corrected_sample_rms'] for col,vals in grouped})
        if df2.isnull().values.all():
            print(f"WARNING: all stations are null for {channelGroup} sample_rms, bypassing")                            
            continue
        meds = df2.median(skipna=True)
        meds.sort_values(ascending=True, inplace=True)
        sortedDF = df2[meds.index]

        ## NOTE: use pdf browser's availability endpoint to determine what channels to expect PDFs for
        
        # 1. lowest corrected sample_rms station.
        for ii in range(len(meds.index)):
            # Starting with the lowest value, make sure that it has enough availability. If not, move on to the next. 
            lowestTarget = meds.index[ii]   # This now contains the quality code
            lowestNSLC = lowestTarget[:-3]  # strip the 3rd component of the channel code, to pull up the other components of that channel later
        
            thisNetwork = lowestTarget.split('.')[0]
            thisStation = str(lowestTarget.split('.')[1])
            if lowestTarget.split('.')[2] == "":
                thisLocation = '--'
            else:
                thisLocation = lowestTarget.split('.')[2]
            thisChannel = lowestTarget.split('.')[3]
            
            thisStationAvDF, service = reportUtils.getAvailaility([lowestTarget], startDate, endDate, tolerance)
            thisAvail = thisStationAvDF[(thisStationAvDF['station'] == thisStation) & (thisStationAvDF['network'] == thisNetwork) & (thisStationAvDF['location'] == thisLocation) & (thisStationAvDF['channel'] == thisChannel)]
            
            thisStart = thisAvail['earliest'].dt.strftime('%Y-%m-%dT%H:%M:%S').min()
            thisEnd = thisAvail['latest'].dt.strftime('%Y-%m-%dT%H:%M:%S').max()
            
            thisAvDF = reportUtils.addMetricToDF('ts_percent_availability_total', pd.DataFrame(), thisNetwork, [thisStation], [thisLocation], thisChannel, thisStart, thisEnd)
            thisPctAvail = thisAvDF['ts_percent_availability_total'].values[0]
            
            foundit = False
            if thisPctAvail > 75:
                # Then we can use it and break the cycle. 
                foundit = True
                break
        
        if foundit == False:
            # Then it didn't actually have any stations with over 75% available data. Use the first station, regardless of availability...
            lowestTarget = meds.index[0]
            lowestNSLC = lowestTarget[:-3] 
            
        expectedTargets_lowest = reportUtils.retrieveExpectedPDFs(lowestNSLC, startDate, endDate)
        
        print(f"   lowest scaled sample_rms station: {lowestTarget.split('.')[1]}")
        pdfFiles = list()
        for target in expectedTargets_lowest:
            
            # Get power range to display based on channel
            if not userDefinedPowerRange:
                try:
                    spectPowerRange = powerRanges[target.split('.')[3][0:2]]
                except:
                    spectPowerRange = [-175,-20]
            else:
                spectPowerRange = userDefinedPowerRange
            pdfFile = reportUtils.getPDF(target, startDate, endDate, spectPowerRange, imageDir)            
            pdfFiles.append(pdfFile)
            
        pdfDictionary[f'{channelGroup}_smallest'] = sorted(pdfFiles)
        
        

        # 2. largest corrected sample_rms  station
        for ii in reversed(range(len(meds.index))):
            largestTarget = meds.index[ii]
            largestNSL = largestTarget[:-3]
            
            thisNetwork = largestTarget.split('.')[0]
            thisStation = str(largestTarget.split('.')[1])
            if largestTarget.split('.')[2] == "":
                thisLocation = '--'
            else:
                thisLocation = largestTarget.split('.')[2]
            thisChannel = largestTarget.split('.')[3]
            
            
            
            thisStationAvDF, service = reportUtils.getAvailaility([largestTarget], startDate, endDate, tolerance)
            thisAvail = thisStationAvDF[(thisStationAvDF['station'] == thisStation) & (thisStationAvDF['network'] == thisNetwork) & (thisStationAvDF['location'] == thisLocation) & (thisStationAvDF['channel'] == thisChannel)]
            
            thisStart = thisAvail['earliest'].dt.strftime('%Y-%m-%dT%H:%M:%S').min()
            thisEnd = thisAvail['latest'].dt.strftime('%Y-%m-%dT%H:%M:%S').max()

            thisAvDF = reportUtils.addMetricToDF('ts_percent_availability_total', pd.DataFrame(), thisNetwork, [thisStation], [thisLocation], thisChannel, thisStart, thisEnd)
            thisPctAvail = thisAvDF['ts_percent_availability_total'].values[0]
            
            foundit = False
            if thisPctAvail > 75:
                # Then we can use it and break the cycle. 
                foundit = True
                break
            
        if foundit == False:
            # Then it didn't actually have any stations with over 75% available data. Use the first station, regardless of availability...
            largestTarget = meds.index[-1]
            largestNSL = largestTarget[:-3]
            
            
        expectedTargets_largest = reportUtils.retrieveExpectedPDFs(largestNSL, startDate, endDate)
        
        print(f"   greatest scaled sample_rms station: {largestTarget.split('.')[1]}")
        pdfFiles = list()
        for target in expectedTargets_largest:
            
            # Get power range to display based on channel
            if not userDefinedPowerRange:
                try:
                    spectPowerRange = powerRanges[target.split('.')[3][0:2]]
                except:
                    spectPowerRange = [-175,-20]
            else:
                spectPowerRange = userDefinedPowerRange
            pdfFile = reportUtils.getPDF(target, startDate, endDate, spectPowerRange, imageDir)
            spectFile = reportUtils.getSpectrogram(target, startDate, endDate, spectPowerRange, spectColorPalette, imageDir)
            pdfFiles.append(pdfFile)
            
        pdfDictionary[f'{channelGroup}_greatest'] = sorted(pdfFiles)

        
        # 3. composite stations - entire network
        print("   composite PDF of all stations")
        allTarget = f'{network}.{stations}.{locations}.{channelGroup[0:2]}'
        expectedTargets_all = reportUtils.retrieveExpectedPDFs(allTarget, startDate, endDate)
        expectedChannels = list(set([x.split('.')[3] for x in expectedTargets_all]))

        files = list()
        for channel in expectedChannels:
            file = reportUtils.getPDF(f"{network}.{stations}.{locations}.{channel}.?", startDate, endDate, spectPowerRange, imageDir)
            files.append(file)
        pdfDictionary[f'{channelGroup}_all'] = sorted(files)
        
            



## SPECTROGRAMS
if doSpectrograms: 
    spectDictionary = {}

    for channelGroup in actualChannels:
        print(f"INFO: Retrieving Spectrograms for {channelGroup}")
        
        topStations = topStationsDict[channelGroup]
        
        # Pare down to the channel group and the stations with the greatest availability
        tmpDF = scaledDF[scaledDF['target'].str.endswith(channelGroup) & scaledDF['station'].isin(topStations)]
                
        # Select the lowest and greatest rms from those stations
        grouped = tmpDF.groupby(['snclq'])
        
        df2 = pd.DataFrame({col:vals['scale_corrected_sample_rms'] for col,vals in grouped})
        if df2.isnull().values.all():
            print(f"WARNING: all stations are null for {channelGroup} scaled sample_rms, bypassing")                            
            continue
        
        meds = df2.median(skipna=True)
        meds.sort_values(ascending=True, inplace=True)
        sortedDF = df2[meds.index]

        ## NOTE: use pdf browser's availability endpoint to determine what channels to expect noise plots for
        
        # 1. lowest corrected sample_rms station
        for ii in range(len(meds.index)):
            # Starting with the lowest value, make sure that it has enough availability. If not, move on to the next. 
            lowestTarget = meds.index[ii]   # This now contains the quality code
            lowestNSLC = lowestTarget[:-3]  # strip the 3rd component of the channel code, to pull up the other components of that channel later
        
            thisNetwork = lowestTarget.split('.')[0]
            thisStation = str(lowestTarget.split('.')[1])
            if lowestTarget.split('.')[2] == "":
                thisLocation = '--'
            else:
                thisLocation = lowestTarget.split('.')[2]
            thisChannel = lowestTarget.split('.')[3]
            
            thisStationAvDF, service = reportUtils.getAvailaility([lowestTarget], startDate, endDate, tolerance)
            thisAvail = thisStationAvDF[(thisStationAvDF['station'] == thisStation) & (thisStationAvDF['network'] == thisNetwork) & (thisStationAvDF['location'] == thisLocation) & (thisStationAvDF['channel'] == thisChannel)]
            
            thisStart = thisAvail['earliest'].dt.strftime('%Y-%m-%dT%H:%M:%S').min()
            thisEnd = thisAvail['latest'].dt.strftime('%Y-%m-%dT%H:%M:%S').max()
            
            thisAvDF = reportUtils.addMetricToDF('ts_percent_availability_total', pd.DataFrame(), thisNetwork, [thisStation], [thisLocation], thisChannel, thisStart, thisEnd)
            thisPctAvail = thisAvDF['ts_percent_availability_total'].values[0]
            
            foundit = False
            if thisPctAvail > 75:
                # Then we can use it and break the cycle. 
                foundit = True
                break
        
        if foundit == False:
            # Then it didn't actually have any stations with over 75% available data. Use the first station, regardless of availability...
            lowestTarget = meds.index[0]
            lowestNSLC = lowestTarget[:-3] 
            
        expectedTargets_lowest = reportUtils.retrieveExpectedPDFs(lowestNSLC, startDate, endDate)
        
        
        print(f"   lowest scaled sample_rms station: {lowestTarget.split('.')[1]}")
        spectFiles = list()
        for target in expectedTargets_lowest:
            
            # Get power range to display based on channel
            if not userDefinedPowerRange:
                try:
                    spectPowerRange = powerRanges[target.split('.')[3][0:2]]
                except:
                    spectPowerRange = [-175,-20]
            else:
                spectPowerRange = userDefinedPowerRange
            spectFile = reportUtils.getSpectrogram(target, startDate, endDate, spectPowerRange, spectColorPalette, imageDir)
            
            spectFiles.append(spectFile)
            
        spectDictionary[f'{channelGroup}_smallest'] = sorted(spectFiles)
        
        
        # 2. largest corrected sample_rms station
        for ii in reversed(range(len(meds.index))):
            largestTarget = meds.index[ii]
            largestNSL = largestTarget[:-3]
            
            thisNetwork = largestTarget.split('.')[0]
            thisStation = str(largestTarget.split('.')[1])
            if largestTarget.split('.')[2] == "":
                thisLocation = '--'
            else:
                thisLocation = largestTarget.split('.')[2]
            thisChannel = largestTarget.split('.')[3]
            
            
            
            thisStationAvDF, service = reportUtils.getAvailaility([largestTarget], startDate, endDate, tolerance)
            thisAvail = thisStationAvDF[(thisStationAvDF['station'] == thisStation) & (thisStationAvDF['network'] == thisNetwork) & (thisStationAvDF['location'] == thisLocation) & (thisStationAvDF['channel'] == thisChannel)]
            
            thisStart = thisAvail['earliest'].dt.strftime('%Y-%m-%dT%H:%M:%S').min()
            thisEnd = thisAvail['latest'].dt.strftime('%Y-%m-%dT%H:%M:%S').max()

            thisAvDF = reportUtils.addMetricToDF('ts_percent_availability_total', pd.DataFrame(), thisNetwork, [thisStation], [thisLocation], thisChannel, thisStart, thisEnd)
            thisPctAvail = thisAvDF['ts_percent_availability_total'].values[0]
            
            foundit = False
            if thisPctAvail > 75:
                # Then we can use it and break the cycle. 
                foundit = True
                break
            
        if foundit == False:
            # Then it didn't actually have any stations with over 75% available data. Use the first station, regardless of availability...
            largestTarget = meds.index[-1]
            largestNSL = largestTarget[:-3]
            
            
        expectedTargets_largest = reportUtils.retrieveExpectedPDFs(largestNSL, startDate, endDate)

        
        print(f"   greatest scaled sample_rms station: {largestTarget.split('.')[1]}")
        spectFiles = list()
        for target in expectedTargets_largest:
            
            # Get power range to display based on channel
            if not userDefinedPowerRange:
                try:
                    spectPowerRange = powerRanges[target.split('.')[3][0:2]]
                except:
                    spectPowerRange = [-175,-20]
            else:
                spectPowerRange = userDefinedPowerRange
            spectFile = reportUtils.getSpectrogram(target, startDate, endDate, spectPowerRange, spectColorPalette, imageDir)
            spectFiles.append(spectFile)
            
        spectDictionary[f'{channelGroup}_greatest'] = sorted(spectFiles)



## MAP
if doMap:
    print("INFO: Generating station map")
    try:
        metadataDF = reportUtils.getMetadata(network, stations, locations, channels, startDate, endDate, 'station')
        metadataDF['EndTime'].replace(np.nan, '', regex=True, inplace=True)
        
        # The map doesn't have a good way to bound, but instead 'zoom' - use this to figure out a good zoom level
        latrange = metadataDF['Latitude'].max() - metadataDF['Latitude'].min()
        latScale = min(0.25, latrange *0.25)
        lonrange = metadataDF['Longitude'].max() - metadataDF['Longitude'].min()
        lonScale = min(0.25, lonrange * 0.25)
        bounds = [metadataDF['Latitude'].max()+latScale, metadataDF['Longitude'].min()-lonScale, metadataDF['Latitude'].min()-latScale,metadataDF['Longitude'].max()+lonScale]
        mapDim = {'height': 500 ,'width': 100}
        zoom = reportUtils.getBoundsZoomLevel(bounds, mapDim)        

        # Create the figure
        fig = px.scatter_mapbox(metadataDF, lat="Latitude", lon="Longitude", hover_name="Station", 
                                hover_data=["Latitude", "Longitude","StartTime","EndTime"],
                                color_discrete_sequence=["indigo"], zoom=zoom, height=500)
    
        # Add the basemap
        fig.update_layout(mapbox_style=basemap)
        fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        
        # Write to file - add config={'scrollZoom': False} if want to disable scroll 
        #    (because it can get obnoxious when scrolling through the report)
        fig.write_html(mapFilename, config={'scrollZoom': False})
    except Exception as e:
        print(f'WARNING: Unable to create and save map: {e}')

    

# Write to HTML file

if doReport:
    print(f"INFO: Writing to file {outfile}")
    
    chans = []
    for chan in channels.split(','):
        if len(chan) == 2:
            chan = f'{chan}Z,{chan}3'
        if chan == "*":
            chan = "??Z,??3"
        chans.append(chan)

    
    
    
    # Write out the introductions to each of the sections, which are placed later in the code
    introText = f'This report is intended as a quick overview of the quality of the data archived for the network ' \
                f'and time period specified above. Our goal in generating these reports is to give PIs better insight ' \
                f'into the quality of the data archived at the DMC, as well as a demonstration of the utility provided ' \
                f'by MUSTANG and the many metrics and products it generates.  For PIs, we hope that these reports will ' \
                f'inform which stations are problematic and might be avoided for ongoing data analysis, as well as providing ' \
                f'lessons on which field practices resulted in improved data quality and vice versa.  Armed with this ' \
                f'information, we hope that PIs will be better positioned to produce high quality data from future field activities.' \
                f'<br/><br/>' \
                f'It is recommended that users may benefit from a more thorough quality assurance inspection of the data, ' \
                f'especially if anything suspicious arises from this report.' \
                f'<br/><br/>' \
                f'Data and metadata are stored at the IRIS DMC and the information here reflects the holdings in their ' \
                f'archive. This report is generated by utilizing their quality assurance system, MUSTANG.' \
                f'<br/><br/>' \
                f'To see the metadata holdings, see here:<br/>' \
                f'<p><a href=\"http://ds.iris.edu/mda/{network}/?starttime={startDate}T00:00:00&endtime={endDate}T23:59:59\" target=\"_blank\"> ' \
                f'IRIS Metadata Aggregator (MDA) for {network}: {startDate} to {endDate}</a></p>\n'
      
      
    availabilityIntroText = f'The plot(s) below gives an overview of the available data for the requested timespan. ' \
                            f'There are three components to the plot(s):' \
                            f'<ol>' \
                            f'<li> Metadata extents in grey  </li>' \
                            f'<li> Available data extents in blue </li>  ' \
                            f'<li> Gaps in black  </li>' \
                            f'</ol>' \
                            f'The metadata extents are retrieved from the IRIS DMC station services ' \
                            f'(<a href=\"http://service.iris.edu/fdsnws/station/1/\" target=\"_blank\">fdsnws</a>, ' \
                            f'<a href=\"http://service.iris.edu/ph5ws/station/1/\" target=\"_blank\">ph5ws</a>), ' \
                            f'while the data extents (and gaps) ' \
                            f'are from the IRIS DMC availability services(<a href=\"http://service.iris.edu/fdsnws/availability/1/\" target=\"_blank\">fdsnws</a>, ' \
                            f'<a href=\"http://service.iris.edu/ph5ws/availability/1/\" target=\"_blank\">ph5ws</a>).' \
                            f'The gap tolerance is an adjustable value and for this report a value of {tolerance} seconds was used.<br/><br/> '\
                            f'In addition, each channel lists the percent of data available, using the '\
                            f'<a href=\"http://service.iris.edu/mustang/metrics/docs/1/desc/ts_percent_availability_total/\" ' \
                            f'target=\"_blank\">ts_percent_availability_total metric</a>. This means that it will display the percent of ' \
                            f' available data over the entire requested period, agnostic to the metadata extents.<br/>' \

#                             f'If a metadata, data, or gap extent is shorter than {gapBuffer*100}% of the total time requested, ' \
#                             f'the bar is extended to that value simply for viewing purposes <br/><br/> ' \
      
      
    
    if splitPlots == 1:
        availabilityIntroText = f'{availabilityIntroText} <br/>The {nTop} stations with the greatest availability and {nBottom} stations' \
                                f'with the least availability are plotted.<br/>'
         
    else:
        availabilityIntroText = f'{availabilityIntroText} <br/>Displaying all stations in the network.<br/>'
    
    
    try:
        availabilityOutroText = 'To view the availbility numbers used to create the availability plot(s), see:'
    
        for service in services:
            serviceLink = f'http://service.iris.edu/{service}/availability/1/query?format=text&' \
                          f'net={network}&sta={stations}&loc={locations}&cha={",".join(chans)}&' \
                          f'starttime={startDate}&endtime={endDate}&orderby=nslc_time_quality_samplerate&' \
                          f'mergegaps={tolerance}&includerestricted=true&nodata=404'
                                    
                                    
            availabilityOutroText = f'<br/>{availabilityOutroText} <br/><a href=\"{serviceLink}\" target=\"_blank\">{serviceLink}</a>'
        
        availabilityOutroText = f'{availabilityOutroText}<br/><br/>To view the metadata information, see: '

        for service in services:
            serviceLink = f'http://service.iris.edu/{service}/station/1/query?' \
                          f'net={network}&sta={stations}&loc={locations}&cha={",".join(chans)}&' \
                          f'starttime={startDate}&endtime={endDate}&level=channel&' \
                          f'format=text&includecomments=true&nodata=404'
                          
            availabilityOutroText = f'{availabilityOutroText}<br/><a href=\"{serviceLink}\" target=\"_blank\">{serviceLink}</a>'
            
    except:
        availabilityOutroText = "No availability was found for the selected channels."   
    
    
      
    boxPlotIntroText = '''
    Metric Boxplots are generated using the Z component for each channel group (for example, BHZ, HHZ, HNZ, etc.) 
    and for each metric included in the report. Each metric boxplot is sorted by the median value of the Z component.<br/><br/> 
    
    '''
    
    boxPlotIntroText2 = f'The boxplots contain the following features:<br/>' \
                        f'<ul>' \
                        f'<li>Quartile Boxes<br/>' \
                        f'The plot consists of two adjoining boxes that extend out to the 25% and 75% confidence interval regions, respectively.  ' \
                        f'50% of all values in the sample population fall within the range of these two boxes, also known as the Interquartile Range (IQR).</li>' \
                        f'<li>Median Line<br/>' \
                        f'The Median Line lies where the two boxes join, indicating the 50% confidence mark where the most points in the sample population land.  ' \
                        f'This line is many times not in the center, being skewed left or skewed right within the two quartiles.</li>' \
                        f'<li>Range Whiskers<br/>' \
                        f'Two lines run out from the quartile boxes, extending to the smallest non-outlier value and the largest non-outlier value.  ' \
                        f'The end points of the whiskers are determined by a range rule, which by default is a value 1.5 times the IQR value from the outer edge' \
                        f'of the quartile box.</li>' \
                        f'<li>Outlier Dots (optional)<br/>' \
                        f'If outliers are selected for the plot, then all other points that do not apply to the established “range” of values are' \
                        f'displayed as a dot or small circle to the extremes.  These values are atypical representations of the sample population as' \
                        f'a whole, but can offer insights into anomalies. </li>' \
                        f'</ul>'
    
    if splitPlots == 1: 
        boxPlotIntroText3 = f'<br/>Within each boxplot, we display the {nTop} greatest and the {nBottom} smallest mean metric ' \
                            f'values for stations in the network.  ' \
                            f'To help visualize these groups, they are plotted separately with the top plot containing the {nTop} greatest, and the bottom plot ' \
                            f'the {nBottom} smallest mean metric values.<br/>' \
                            f'<br/> Detailed information about each metric and how it was generated can be found by visiting the following links:<br/> ' 
                            
    else:
        boxPlotIntroText3 = f'<br/>Displaying all stations in the network.<br/>' \
                            f'<br/> Detailed information about each metric and how it was generated can be found by visiting the following links:<br/>' 

    # Loop over the metrics actually used in the report and append the link to the documentation on that metric
    for metric in metricList:
        boxPlotIntroText3 = f'{boxPlotIntroText3}<li><a href=\"http://service.iris.edu/mustang/metrics/docs/1/desc/{metric}\" target=\"_blank\">{metric}</a></li>\n'

    
    pdfPlotIntroText = f'This section contains probability density function (PDF) plots for the stations with the greatest median scaled RMS, ' \
                       f'lowest median scaled RMS, and composite of all stations for each channel set.  Station/channels with less than ' \
                       f'75% data availability are omitted unless none of the stations have at least 75% availability. Detailed information ' \
                       f'about these PDF plots and how MUSTANG generates them ' \
                       f'can be found by visiting this link: <a href=\"http://service.iris.edu/mustang/noise-pdf/docs/1/help/\" target=\"_blank\">' \
                       f'http://service.iris.edu/mustang/noise-pdf/docs/1/help/</a></p>\n' \
                       f'Please note that you can also click the links below to access the MUSTANG PDF browser, which allows you to view ' \
                       f'PDF plots by stations and channels on an annual, monthly, or daily basis.' 

    
    if splitPlots == 1:
        spectrgramPlotIntoText = f'This section contains spectrogram plots for the most continuous stations with the greatest median scaled RMS and ' \
                             f'lowest median scaled RMS for each channel set.  Stations are selected from the list of the {nTop} stations ' \
                             f'with the greatest total availability for that channel group. Stations with less than 75% data availability are omitted '\
                             f'unless none of the top {nTop} stations have at least 75% availability - in which case, the station with the greatest/lowest median '\
                             f'scaled RMS value from the top {nTop} stations is used.<br/><br/> ' \
                             f'Detailed information about these spectrogram plots and how MUSTANG ' \
                             f'generates them can be found by visiting this link: <a href=\"http://service.iris.edu/mustang/noise-spectrogram/' \
                             f'docs/1/help/\" target=\"_blank\"> http://service.iris.edu/mustang/noise-spectrogram/docs/1/help/</a></p>' \
                             f'Please note that you can also click the links below to access the MUSTANG spectrogram browser for each channel group below, ' \
                             f'which allows you to view spectrogram plots from all the stations in your network.' 
    else:
        spectrgramPlotIntoText = f'This section contains spectrogram plots for the stations with the greatest median scaled RMS and ' \
                             f'lowest median scaled RMS for each channel set. Station/channels with less than 75% data availability are omitted ' \
                             f'unless none of the stations have at least 75% availability - in which case, the station with the greatest/lowest median '\
                             f'scaled RMS value is used.<br/><br/> ' \
                             f'Detailed information about these spectrogram plots and how MUSTANG ' \
                             f'generates them can be found by visiting this link: <a href=\"http://service.iris.edu/mustang/noise-spectrogram/' \
                             f'docs/1/help/\" target=\"_blank\"> http://service.iris.edu/mustang/noise-spectrogram/docs/1/help/</a></p>' \
                             f'Please note that you can also click the links below to access the MUSTANG spectrogram browser for each channel group below, ' \
                             f'which allows you to view spectrogram plots from all the stations in your network.' 
    
    mapURL = f'http://ds.iris.edu/gmap/#network={network}&starttime={startDate}&endtime={endDate}'
    mapIntroText = f'Below is a plot of station locations for the network and time period specified at the beginning of this report. ' \
                   f'To access an interactive map including these locations please visit this link: ' \
                   f'<a href=\"{mapURL}\" target=\"_blank\"> {mapURL}</a></p>\n'

    
    
    stationIntroText = f'Below is a list of stations, their locations, and start and end dates.  ' \
                       f'Clicking on any text from a station row will take you to the IRIS metadata aggregator ' \
                       f'page for that station where you can view more detailed information about data epochs, ' \
                       f'instrumentation, metadata changes, and virtual network affiliations.'
    
    


    style = '<style>' \
            '/* unvisited link */' \
            'a:link {' \
            ' color: darkslategray;' \
            '}' \
            '/* visited link */' \
            'a:visited {' \
            ' color: lightslategray;' \
            '}' \
            '/* mouse over link */' \
            'a:hover {' \
            ' color: grey;' \
            '}' \
            '* {' \
            ' box-sizing: border-box;' \
            '}' \
            'body {' \
            ' margin: 0;' \
            '}' \
            '.header {' \
            ' text-align: center;' \
            ' padding: 32px;' \
            '}' \
            '.row {' \
            ' display: -ms-flexbox; /* IE10 */' \
            ' display: flex;' \
            ' -ms-flex-wrap: wrap; /* IE10 */' \
            ' flex-wrap: wrap;' \
            ' padding: 0 4px;' \
            '}' \
            '/* Create four equal columns that sits next to each other */' \
            '.column {' \
            '  -ms-flex: 25%; /* IE10 */' \
            '  flex: 25%;' \
            '  max-width: 33%;' \
            '  min-width: 33%;' \
            '  padding: 0 4px;' \
            '}' \
            '.column img {' \
            '  margin-top: 8px;' \
            '  vertical-align: middle;' \
            '  width: 100%;' \
            '}' \
            '.spectcolumn {' \
            '  -ms-flex: 25%; /* IE10 */' \
            '  flex: 25%;' \
            '  max-width: 50%;' \
            '  min-width: 50%;' \
            '  padding: 0 4px;' \
            '}' \
            '.spectcolumn img {' \
            '  margin-top: 8px;' \
            '  vertical-align: middle;' \
            '  width: 100%;' \
            '}' \
            '.div-light {' \
            'background-color: white;' \
            'padding: 20;' \
            '}' \
            '.div-dark {' \
            'background-color: whitesmoke;' \
            'padding: 20;' \
            '<!-- box-shadow: 0 0 8px 8px white inset -->;' \
            '}' \
            '.resp-container {' \
            '    position: relative;' \
            '    overflow: hidden;' \
            '    padding-top: 50%;' \
            '}' \
            '.resp-iframe {' \
            '    position: absolute;' \
            '    top: 0;' \
            '    left: 0;' \
            '    width: 100%;' \
            '    height: 100%;' \
            '    border: 0;' \
            '}' \
            '/* Responsive layout - makes a two column-layout instead of four columns */' \
            '@media screen and (max-width: 800px) {' \
            '  .column {' \
            '    -ms-flex: 50%;' \
            '    flex: 50%;' \
            '    max-width: 50%;' \
            '  }' \
            '}' \
            '/* Responsive layout - makes the two columns stack on top of each other instead of next to each other */' \
            '@media screen and (max-width: 600px) {' \
            '  .column {' \
            '    -ms-flex: 100%;' \
            '    flex: 100%;' \
            '    max-width: 100%;' \
            '  }' \
            '}' \
            'table {' \
            '  border-collapse: collapse;' \
            '  width: 100%;' \
            '}' \
            '.hoverTable{' \
            '    width:100%; ' \
            '    border-collapse:collapse; ' \
            '}' \
            '.hoverTable td{ ' \
            '    padding:5px; ' \
            '    border:#808080 0px solid;' \
            '}' \
            '/* Define the default color for all the table rows */' \
            '.hoverTable tr{' \
            '    background: whitesmoke;' \
            '}' \
            '.hoverTable td a { ' \
            '   display: block; ' \
            '   border: 0px solid black;' \
            '}' \
            '/* Define the hover highlight color for the table row */' \
            '.hoverTable tr:hover {' \
            '      background-color: silver;' \
            '}' \
            '</style>'
        
    
    
    
    
    
    with open(outfile,'w') as f:
        #print("Writing Header")
        f.write("<html>")
                
        f.write(style)
        
        
#         f.write('<div class="div-dark">')
        
        f.write("    <head>\n")
        f.write(f"<meta name=Title content=\"{network} Data Quality Report for {' - '. join([startDate, endDate])} \">\n")
        f.write(f"<title> {network}: Data Quality Report for Network for {' - '. join([startDate, endDate])}</title>\n")
        f.write("    </head>\n\n");
#         f.write('</div>')
        
        f.write("    <body>");
        f.write('<div class="div-light">')
        if startYear == endYear:
            f.write(f"<a name='top'></a> <h1>Data Quality Report for {network} ({startYear})</h1>");
        else:
            f.write(f"<h1>Data Quality Report for {network} ({startYear}-{endYear})</h1>");
    
        f.write('<hr style="width:200;text-align:left;margin-left:2;color:lightgray">')
        f.write(f'<i>Covering {startDate} to {endDate}</i><br/>');
        today =  datetime.datetime.today().strftime('%B %d, %Y');
        f.write(f'<i>Issued on {today}<br/>Using PIQQA {version} </i><br/>');
        f.write('<hr style="width:200;text-align:left;margin-left:2;color:lightgray">')
        
        f.write('<br/>')
        intro = '''This report is intended as a quick overview of the quality of the data archived for the specified network. 
        That includes boxplot summary views of selected metrics, PDFs, and spectrograms. It is recommended
        that users may benefit from a more thorough quality assurance inspection of the data, especially if anything
        suspicious arises from this report.  
        <br/>
        <br/>
        Data and metadata are stored at the IRIS DMC and the information here reflects the holdings in their archive.  
        This report is generated by utilizing their quality assurance system, MUSTANG. 
        <br/>
        <br/>
        To see the metadata holdings, see here:
        '''
        f.write(introText)
        f.write("<p></p>");
        
        
        toc = '''
        <br/>Jump to section:<br/>
        <!-- <p style="margin-left: 40px"> -->
        <!-- <a href="#boxplots" >Boxplots</a><br/> -->
        <!-- <a href="#pdfs">PDF Plots</a><br/> -->
        <!-- <a href="#spectrograms">Spectrograms</a><br/> -->
        <!-- <a href="#map">Station Map</a><br/> -->
        <!-- <a href="#stations" >Station List</a><br/> -->
        
        <!-- </p> -->
        
        <br/>
        <table width:100%;>
        <tr><td style="text-align:center"><a href="#availability" >Availability</a></td>
        <td style="text-align:center"><a href="#boxplots" >Boxplots</a></td>
        <td style="text-align:center"><a href="#pdfs">PDF Plots</a></td>
        <td style="text-align:center"><a href="#spectrograms">Spectrograms</a></td>
        <td style="text-align:center"><a href="#map">Station Map</a></td>
        <td style="text-align:center"><a href="#stations" >Station List</a></td>
        </tr></table>
        <br/>
        
        '''
        
        f.write(toc)
        f.write('</div>')
        
        
        #### ADD AVAILABILITY PLOT
        f.write('<div class="div-dark">')
        f.write('<hr style="width:100%;color:lightgray">')
        f.write("<br/>");
        f.write("<a name='availability'></a> <h2>Availability Plot</h2>")
        f.write(availabilityIntroText)
        
        
        f.write("<p></p>");
        
        for channel in actualChannels:
            f.write(f"<h3>{channel[0:2]}</h3>")
            f.write("<p></p>");
            
            f.write('<div class="row">')

            file = avFilesDictionary[f'{channel}']
#             for file in files:
            f.write(f'    <center><a href=\"./{file}\" target="_blank"><img src="{file}" width="100%"></a></center><br/>')
                    
            f.write('</div>')
            

        f.write("<p></p>");
        
        
        
        
#         
#         f.write("<p></p>");
#         
#         f.write('    <center><a href=\"./{}\" target="_blank"><img src="{}" width="100%"></a></center><br/>'.format(avFilename, avFilename))
        f.write(availabilityOutroText)
        f.write('<br/>')
        f.write('<hr style="width:100%;color:lightgray">')
        f.write('<p style="text-align:center"><a href="#top">Back to Top</a></p>')
        f.write('</div>')
        
        
        #### ADD BOXPLOTS   
        f.write('<div class="div-light">')     
#         f.write('<div class="div-dark">')
#         f.write('<hr style="width:100%;color:lightgray">')
        f.write("<br/>");
        f.write("<a name='boxplots'></a> <h2>Metric Boxplots</h2>")
        
        # Add intro, boxplot example plot, and rest of intro
        f.write(boxPlotIntroText)
        f.write(boxPlotIntroText2)
        f.write(f'    <center><a href=\"./{boxPlotExampleImage_moved}\" target="_blank"><img src="{boxPlotExampleImage_moved}" width="50%"></a></center><br/>')
        f.write(boxPlotIntroText3)
        
        
        f.write("<p></p>");
        
        for channel in actualChannels:
            f.write(f"<h3>{channel[0:2]}</h3>")
            f.write("<p></p>");
            
            f.write('<div class="row">')

            files = boxPlotDictionary[f'{channel}']
            for file in files:
                f.write('  <div class="column">')
                f.write(f'    <center><a href=\"./{file}\" target="_blank"><img src="{file}"></a></center><br/>')
                f.write('  </div>')
                    
            f.write('</div>')
            

        f.write("<p></p>");
        f.write("<h3>Explore the Metrics</h3>")
        
        f.write("<p>MUSTANG is the Quality Assurance system at the IRIS DMC. It contains around 45 metrics related to the quality of data in the archives there.\n\n")
        f.write("The majority of metrics are available via the <a href=\"http://service.iris.edu/mustang/measurements/1/\" target=\"_blank\">measurements web service.</a>\n\n")
        f.write("To learn more about the metrics, navigate to the measurements service Service Interface page and hit the red \"Current List of all metrics\" for a brief description and links to more detailed documentation.\n\n")
        
        f.write("<p>To view the metric values used in the plots above: </p>")
        f.write('<ul>')
        channelsExpanded = list()
        for channel in channels.split(','):
            if len(channel)==2:
                channel = channel + '?'
            channelsExpanded.append(channel)
        channels = ','.join(channelsExpanded)
        for metric in metricList:
            metricsLinks = f"http://service.iris.edu/mustang/measurements/1//query?metric={metric}"\
                          f"&network={network}&station={stations}&location={locations}&channel={channels}"\
                          f"&start={startDate}&end={endDate}&format=text"
            f.write(f"<li><a href=\"{metricsLinks}\" target=\"_blank\">{metric}</a></li>\n") 
        f.write('</ul>')
        f.write('<br/>')
#         f.write('<hr style="width:100%;color:lightgray">')
        f.write('<p style="text-align:center"><a href="#top">Back to Top</a></p>')
        f.write('</div>')
        
        
        
        #### ADD PDFS 
        f.write('<div class="div-dark">')
        f.write('<hr style="width:100%;color:lightgray">')
#         f.write('<div class="div-light">')
        f.write("<br/>");
        f.write("<a name='pdfs'></a> <h2>PDF Plots</h2>")
        
        
        f.write(pdfPlotIntroText)
        
        # Loop over each channel group, create a 3x3 (if 3 component) grid for each channel group
        for channel in actualChannels: 
            pdfLink = f'http://service.iris.edu/mustang/noise-pdf-browser/1/gallery?'\
                       f'network={network}&channel={channel[0:2]}?&interval=all&' \
                       f'starttime={startDate}&endtime={endDate}'
            f.write(f"<h3>{channel[0:2]} - <a href='{pdfLink}' target='_blank' >PDF Browser</a></h3>")
            f.write('<div class="row">')
            f.write('  <div class="column">')
            f.write('<center>Lowest RMS Station</center><br/>')
            
            try:
                files = pdfDictionary[f'{channel}_smallest']
                
                for file in files:
                    f.write(f'    <center><a href=\"./{file}\" target="_blank"><img src="{file}"></a></center><br/>')
            except:
                pass
            
            f.write('  </div>')   
            f.write('  <div class="column">')
            f.write('<center>Greatest RMS Station</center><br/>')
            
            try:
                files = pdfDictionary[f'{channel}_greatest']
                for file in files:
                    f.write(f'    <center><a href=\"./{file}\" target="_blank"><img src="{file}"></a></center><br/>')
                
            except:
                pass
            f.write('  </div>')
            f.write('  <div class="column">')
            f.write('<center>Network Composite</center><br/>')
            try:
                files = pdfDictionary[f'{channel}_all']
                for file in files:
                    f.write(f'    <center><a href=\"./{file}\" target="_blank"><img src="{file}"></a></center><br/>')
            except:
                pass
            f.write('  </div>')
            f.write('</div>')
        f.write('<hr style="width:100%;color:lightgray">')
        f.write('<p style="text-align:center"><a href="#top">Back to Top</a></p>')
        f.write('</div>')
        
        
        
        
        #### ADD SPECTROGRAMS
        f.write('<br/>')
        f.write('<div class="div-light">')
#         f.write('<div class="div-dark">')
#         f.write('<hr style="width:100%;color:lightgray">')
        f.write("<br/>");
        f.write("<a name='spectrograms'></a> <h2>Spectrogram Plots</h2>")
        
        f.write(spectrgramPlotIntoText)
    
        # Loop over each channel group, create a 3x2 (if 3 component) grid for each channel group
        for channel in actualChannels: 
            spectLink = f'http://service.iris.edu/mustang/noise-pdf-browser/1/spectrogram?' \
                        f'network={network}&channel={channel[0:2]}?&' \
                        f'starttime={startDate}&endtime={endDate}'
            f.write(f"<h3>{channel[0:2]} - <a href='{spectLink}' target='_blank' >Spectrogram Browser</a></h3>")
            f.write('<div class="row">')
            f.write('  <div class="spectcolumn">')
            f.write('<center>Lowest RMS Station</center><br/>')
            
            try:
                files = spectDictionary[f'{channel}_smallest']
                for file in files:
                    f.write(f'    <center><a href=\"./{file}\" target="_blank"><img src="{file}"></a></center><br/>')
            except:
                pass
            f.write('  </div>')
            
            f.write('  <div class="spectcolumn">')
            f.write('<center>Greatest RMS Station</center><br/>')
            
            try:
                files = spectDictionary[f'{channel}_greatest']
                for file in files:
                    f.write(f'    <center><a href=\"./{file}\" target="_blank"><img src="{file}"></a></center><br/>')
            except:
                pass
            
            f.write('  </div>')
            f.write('</div>')
#         f.write('<hr style="width:100%;color:lightgray">')
        f.write('<p style="text-align:center"><a href="#top">Back to Top</a></p>')
        f.write('</div>')

    
        #### ADD MAP
        f.write('<div class="div-dark">')
        f.write('<hr style="width:100%;color:lightgray">')
#         f.write('<hr style="width:100%;color:lightgray">')
#         f.write('<div class="div-light">')
        f.write("<br/>");
        f.write("<a name='map'></a> <h2>Map</h2>")
        
        f.write(mapIntroText)
        
        with open(mapFilename, "r") as f2:
            mapText = f2.read().replace('<html>','').replace('</html>','')
        f.write(mapText)
        
        f.write('<br/>')
        f.write('<hr style="width:100%;color:lightgray">')
        f.write('<p style="text-align:center"><a href="#top">Back to Top</a></p>')
        f.write('</div>')
        
        
        
        
        
        ## ADD STATION TABLE
        f.write('<br/>')
        f.write('<div class="div-light">')
#         f.write('<div class="div-dark">')
#         f.write('<hr style="width:100%;color:lightgray">')
        f.write("<br/>");
        f.write("<a name='stations'></a> <h2>Station List</h2>")
        f.write(stationIntroText)
        
        f.write('<table class="hoverTable">')
        f.write('<tr><td><b>Network</b></td><td><b>Station</b></td><td><b>Latitude</b></td><td><b>Longitude</b></td><td><b>Elevation</b></td><td><b>Site Name</b></td><td><b>Start Date</b></td><td><b>End Date</b></td></tr>')
        
        for ind, row in metadataDF.iterrows():
            mdaLink = f"http://ds.iris.edu/mda/{row['#Network']}/{row['Station']}/?starttime={row['StartTime']}&endtime={row['EndTime']}"
            
            f.write(f'<tr><td><a href="{mdaLink}" target="_blank" >{row["#Network"]}</a></td>')
            f.write(f'<td><a href="{mdaLink}" target="_blank" >{row["Station"]}</a></td>')
            f.write(f'<td><a href="{mdaLink}" target="_blank" >{row["Latitude"]:.4f}</a></td>')
            f.write(f'<td><a href="{mdaLink}" target="_blank" >{row["Longitude"]:.4f}</a></td>')
            f.write(f'<td><a href="{mdaLink}" target="_blank" >{row["Elevation"]:.1f}</a></td>')
            f.write(f'<td><a href="{mdaLink}" target="_blank" >{row["SiteName"]}</a></td>')
            f.write(f'<td><a href="{mdaLink}" target="_blank" >{row["StartTime"]}</a></td>')
            f.write(f'<td><a href="{mdaLink}" target="_blank" >{row["EndTime"]}</a></td></tr>')
            
        f.write('</table>')
        
#         f.write('<hr style="width:100%;color:lightgray">')
        f.write('<p style="text-align:center"><a href="#top">Back to Top</a></p>')
        f.write('</div>')
        
        
        
        ## WRAP IT UP
        f.write("</body>");
    f.close();
    
    
    
print(f"INFO: Report written to {outdir}/{outfile} at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
# Create a zipped version of the report
path_parent = os.path.dirname(os.getcwd())
os.chdir(path_parent)
shutil.make_archive(outdir, 'zip', outdir)

print(f"INFO: Report zipped to {outdir}, PIQQA report is complete.")
