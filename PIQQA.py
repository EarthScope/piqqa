#!/usr/bin/env python

'''
Created on Aug 18, 2020

@author: laura
'''
    
import pandas as pd
import reportUtils
import matplotlib.pyplot as plt
import plotly.express as px
import datetime
import sys
import os
import numpy as np

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
    
    If PIQQA is not working as expected, ensure that the conda environment is activated
    '''
    quit(helpText)
    
    
# metricList = ['ts_channel_up_time', 'sample_rms', 'ts_num_gaps']
metricList = ['ts_channel_up_time','sample_rms','num_gaps']
metricsRequired = ['percent_availability']

###### Default values
stations = "*"
locations = "*"
channels = "*"
nBoxPlotSta = 30

spectColorPalette =  'RdYlBu'
includeOutliers = False
basemap = "open-street-map"

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
    outfile = '%s_%s.html' % ( network, startYear)
    outdir = '%s_%s' % ( network, startYear)
else:
    outfile = '%s_%s-%s.html' % ( network, startYear, endYear)       
    outdir = '%s_%s-%s' % ( network, startYear, endYear)

# Create directory for this network/year(s)
if not os.path.isdir(outdir):
    print("INFO: Creating directory %s/" % outdir)
    os.makedirs(outdir)
os.chdir(outdir)    

# Put the figures all together in a subdirectory
imageDir = 'images'
if not os.path.isdir(imageDir):
    print("INFO: Creating subdirectory %s/" % imageDir)
    os.makedirs(imageDir)

mapFilename = '%s/%s_stationMap.html' % (imageDir, network)

# For testing and debugging
doBoxPlots = 1
doPDFs = 1
doMap = 1
doReport = 1

########
########

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
        print("WARNING: No metrics retrieved for %s.%s.%s.%s %s-%s" %(network, stations, locations, channels, startDate, endDate))
        boxPlotDictionary = {}
        actualChannels = list()
    else:
        try:
            metricDF = metricDF[metricDF['percent_availability'] !=0]
        except:
            print("WARNING: Unable to subset based on percent_availabity > 0")
        
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
                scaledDF.loc[affectedRows, 'sample_rms'] = scaledDF['sample_rms_orig'][affectedRows] / thisScale
            
        
        boxPlotDictionary = {}
        for channelGroup in actualChannels:
            tmpDF = scaledDF[scaledDF['target'].str.endswith(channelGroup)]

            
            print('INFO: Generating Boxplots for %s' % channelGroup)
            grouped = tmpDF.groupby(['station'])

    #         fig, axes = plt.subplots(1, len(metricList), figsize=(3*len(metricList),  0.2*nBoxPlotSta))
            fig = plt.Figure(figsize=(3,  0.2*nBoxPlotSta))
            
            filenames = list()
            for metric in metricList:
#                 print("   " + metric)
                
                try:
                    # This may fail if the metric wasn't accessible from web services
                    
                    # Sort by the median value
                    df2 = pd.DataFrame({col:vals[metric] for col,vals in grouped})
                    if df2.isnull().values.all():
                        print("WARNING: all stations are null for %s %s, bypassing" % (channelGroup, metric))                            
                        continue
                    
                    meds = df2.median(skipna=True)
                    meds.sort_values(ascending=True, inplace=True)
            #         meds.dropna(inplace = True)    # not needed because of the skipna above(? but leaving here JIC I need to bring it back)
                    df2 = df2[meds.index]
                    stationList = sorted(list(set(df2.columns)))
                
                    # If there are too many stations, then only show the top/bottom stations
                    nsta = len(stationList)
                    if nsta > nBoxPlotSta:
                        nTop = int(nBoxPlotSta / 2)
                        nBottom = int(nBoxPlotSta - nTop)
                        
                        df2 = pd.concat([df2.iloc[:, 0:nTop], df2.iloc[:, nsta-nBottom:nsta]],axis=1)
                    
            
                    # Create and save the boxplot for that metric
                    height = max(min(0.3*nsta, 0.3*nBoxPlotSta), 2)
                    width = 5
                    if includeOutliers:
                        boxplot = df2.boxplot(vert=False, grid=False, figsize=(width, height), color={'medians': 'black', 'boxes':'black', 'whiskers':'black'})
                    else:
                        boxplot = df2.boxplot(vert=False, grid=False, figsize=(width,height), showfliers=False, color={'medians': 'black', 'boxes':'black', 'whiskers':'black'})
        
                    boxplot.set_title(metric)
                 
                    plt.tight_layout()
                    filename = '%s/%s_%s_boxplot.png' % (imageDir, channelGroup, metric)
                    plt.savefig(fname=filename, bbox_inches="tight")
                    plt.close()
                    
                    filenames.append(filename)
                       
                except Exception as e:
                    print("    WARNING: could not plot %s - %s" % (metric,e))
                
                
            
            boxPlotDictionary['%s' % (channelGroup)] = filenames
    

## PDFS and SPECTROGEAM RETRIEVAL
if doPDFs:
    pdfDictionary = {}
    spectDictionary = {}
    
    for channelGroup in actualChannels:
#         print(channelGroup)
        print("INFO: Retrieving PDFs and Spectrograms for %s" % channelGroup)
        
        # Use the dataframe with the SCALED sample_rms to determine the top/bottom station/target        
        tmpDF = scaledDF[scaledDF['target'].str.endswith(channelGroup)]
        grouped = tmpDF.groupby(['target'])
        
        df2 = pd.DataFrame({col:vals['sample_rms'] for col,vals in grouped})
        if df2.isnull().values.all():
            print("WARNING: all stations are null for %s sample_rms, bypassing" % (channelGroup))                            
            continue
        meds = df2.median(skipna=True)
        meds.sort_values(ascending=True, inplace=True)
        sortedDF = df2[meds.index]

        ## NOTE: use pdf browser's availability endpoint to determine what channels to expect PDFs for
        
        # 1. smallest corrected sample_rms station
        lowestTarget = meds.index[0]
        lowestNSLC = lowestTarget[:-1]  # strip the 3rd component of the channel code, to pull up the other components of that channel later
        expectedTargets_lowest = reportUtils.retrieveExpectedPDFs(lowestNSLC, startDate, endDate)
        
        print("   lowest scaled sample_rms station: %s" % lowestTarget.split('.')[1])
        pdfFiles = list()
        spectFiles = list()
        for target in expectedTargets_lowest:
#             print("   %s" % target)
            
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
            spectFiles.append(spectFile)
            
        pdfDictionary['%s_smallest' % channelGroup] = sorted(pdfFiles)
        spectDictionary['%s_smallest' % channelGroup] = sorted(spectFiles)
        
        # 2. largest corrected sample_rms  station
        largestTarget = meds.index[-1]
        largestNSL = largestTarget[:-1]
        expectedTargets_largest = reportUtils.retrieveExpectedPDFs(largestNSL, startDate, endDate)
        
        print("   greatest scaled sample_rms station: %s" % largestTarget.split('.')[1])
        pdfFiles = list()
        spectFiles = list()
        for target in expectedTargets_largest:
#             print("   %s" % target)
            
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
            spectFiles.append(spectFile)
            
        pdfDictionary['%s_greatest' % channelGroup] = sorted(pdfFiles)
        spectDictionary['%s_greatest' % channelGroup] = sorted(spectFiles)
        
        # 3. composite stations - entire network
        print("   composite PDF of all stations")
        allTarget = '%s.%s.%s.%s' %(network, stations, locations, channelGroup[0:2])
        expectedTargets_all = reportUtils.retrieveExpectedPDFs(allTarget, startDate, endDate)
        expectedChannels = list(set([x.split('.')[3] for x in expectedTargets_all]))

        files = list()
        for channel in expectedChannels:
            file = reportUtils.getPDF("%s.%s.%s.%s.?" % (network,stations,locations,channel), startDate, endDate, spectPowerRange, imageDir)
            files.append(file)
        pdfDictionary['%s_all' % channelGroup] = sorted(files)
        
            



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
        
    #     fig.update_layout(mapbox_style="white-bg",mapbox_layers=[
    #         {
    #             "below": 'traces',
    #             "sourcetype": "raster",
    #             "sourceattribution": "United States Geological Survey",
    #             "source": [
    #                 "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}"
    #             ]
    #         }
    #       ])
    #     fig.show()
    
    
        # Write to file - add config={'scrollZoom': False} if want to disable scroll 
        #    (because it can get obnoxious when scrolling through the report)
        fig.write_html(mapFilename, config={'scrollZoom': False})
    except Exception as e:
        print('WARNING: Unable to create and save map: %s' % e)

    

# Write to HTML file

if doReport:
    print("INFO: Writing to file %s" % outfile)
    with open(outfile,'w') as f:
        #print("Writing Header")
        f.write("<html>")
        
        style = '''<style>
        
/* unvisited link */
a:link {
  color: darkslategray;
}

/* visited link */
a:visited {
  color: lightslategray;
}

/* mouse over link */
a:hover {
  color: grey;
}


* {
  box-sizing: border-box;
}

body {
  margin: 0;
  #font-family: Arial;
}

.header {
  text-align: center;
  padding: 32px;
}

.row {
  display: -ms-flexbox; /* IE10 */
  display: flex;
  -ms-flex-wrap: wrap; /* IE10 */
  flex-wrap: wrap;
  padding: 0 4px;
}

/* Create four equal columns that sits next to each other */
.column {
  -ms-flex: 25%; /* IE10 */
  flex: 25%;
  max-width: 33%;
  min-width: 33%;
  padding: 0 4px;
}

.column img {
  margin-top: 8px;
  vertical-align: middle;
  width: 100%;
}

.spectcolumn {
  -ms-flex: 25%; /* IE10 */
  flex: 25%;
  max-width: 50%;
  min-width: 50%;
  padding: 0 4px;
}

.spectcolumn img {
  margin-top: 8px;
  vertical-align: middle;
  width: 100%;
}

.div-light {
background-color: white;
padding: 20;
}

.div-dark {
background-color: whitesmoke;
padding: 20;
<!-- box-shadow: 0 0 8px 8px white inset -->;
}

.resp-container {
    position: relative;
    overflow: hidden;
    padding-top: 50%;
}

.resp-iframe {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    border: 0;
}

/* Responsive layout - makes a two column-layout instead of four columns */
@media screen and (max-width: 800px) {
  .column {
    -ms-flex: 50%;
    flex: 50%;
    max-width: 50%;
  }
}

/* Responsive layout - makes the two columns stack on top of each other instead of next to each other */
@media screen and (max-width: 600px) {
  .column {
    -ms-flex: 100%;
    flex: 100%;
    max-width: 100%;
  }
}

table {
  border-collapse: collapse;
  width: 100%;
  
}

.hoverTable{
    width:100%; 
    border-collapse:collapse; 
}
.hoverTable td{ 
    padding:5px; 
    border:#808080 0px solid;
}
/* Define the default color for all the table rows */
.hoverTable tr{
    background: whitesmoke;
}
.hoverTable td a { 
   display: block; 
   border: 0px solid black;
   
}

/* Define the hover highlight color for the table row */
.hoverTable tr:hover {
      background-color: silver;
}

</style>'''
        
        f.write(style)
        
        
#         f.write('<div class="div-dark">')
        
        f.write("    <head>\n")
        f.write("<meta name=Title content=\"%s Data Quality Report for %s \">\n" % (network ,' - '. join([startDate, endDate])))
        f.write("<title> %s: Data Quality Report for Network for %s</title>\n" % (network ,' - '. join([startDate, endDate])))
        f.write("    </head>\n\n");
#         f.write('</div>')
        
        f.write("    <body>");
        f.write('<div class="div-light">')
        if startYear == endYear:
            f.write("<a name='top'></a> <h1>Data Quality Report for %s (%s)</h1>" % (network, startYear));
        else:
            f.write("<h1>Data Quality Report for %s (%s-%s)</h1>" % (network, startYear, endYear));
    
        f.write('<hr style="width:200;text-align:left;margin-left:2;color:lightgray">')
        f.write('<i>Covering %s to %s</i><br>' % (startDate, endDate));
        today =  datetime.datetime.today().strftime('%B %d, %Y');
        f.write('<i>Issued ' + str(today) + '</i><br>');
        f.write('<hr style="width:200;text-align:left;margin-left:2;color:lightgray">')
        
        f.write('<br>')
        intro = '''PLACEHOLDER TEXT: This report is intended as a quick overview of the overall health of the network. 
        That includes boxplot summary views of selected metrics, PDFs, and spectrograms. It is recommended
        that users may benefit from a more thorough quality assurance inspection of the data, especially if anything
        suspicious arises from this report.  
        <br>
        <br>
        Data and metadata are stored at the IRIS DMC and the information here reflects the holdings in their archive.  
        This report is generated by utilizing their quality assurance system, MUSTANG. 
        <br>
        <br>
        To see the metadata holdings, see here:
        '''
        f.write(intro)
        f.write("<p><a href=\"http://ds.iris.edu/mda/%s/?starttime=%sT00:00:00&endtime=%sT23:59:59\" target=\"_blank\"> IRIS Metadata Aggregator (MDA) for %s %s to %s</a></p>\n" % (network, startDate, endDate, network, startDate, endDate));
        f.write("<p></p>");
        toc = '''
        <br>Jump to section:<br>
        <!-- <p style="margin-left: 40px"> -->
        <!-- <a href="#boxplots" >Boxplots</a><br> -->
        <!-- <a href="#pdfs">PDF Plots</a><br> -->
        <!-- <a href="#spectrograms">Spectrograms</a><br> -->
        <!-- <a href="#map">Station Map</a><br> -->
        <!-- <a href="#stations" >Station List</a><br> -->
        
        <!-- </p> -->
        
        <br>
        <table width:100%;>
        <tr><td style="text-align:center"><a href="#boxplots" >Boxplots</a></td>
        <td style="text-align:center"><a href="#pdfs">PDF Plots</a></td>
        <td style="text-align:center"><a href="#spectrograms">Spectrograms</a></td>
        <td style="text-align:center"><a href="#map">Station Map</a></td>
        <td style="text-align:center"><a href="#stations" >Station List</a></td>
        </tr></table>
        <br>
        
        '''
        
        f.write(toc)
        f.write('</div>')
        
        ## ADD BOXPLOTS
#         f.write('<br><br>')
        
        f.write('<div class="div-dark">')
        f.write('<hr style="width:100%;color:lightgray">')
        f.write("</br>");
        f.write("<a name='boxplots'></a> <h2>Metric Boxplots</h2>")
        
        boxplotIntro = '''
        PLACEHOLDER TEXT: Boxplots are generated using the Z component for each channel group (for example, BHZ, HHZ, HNZ, etc) and for each metric included in the report.
        Each metric boxplot is ordered by the median value of the Z component.  <br><br>
        '''
        try: 
            boxplotIntro = boxplotIntro + "Displaying the %s greatest and %s smallest stations in the network for each metric." %(nTop, nBottom)
        except:
            boxplotIntro = boxplotIntro + "Displaying all stations in the network."
        
        f.write(boxplotIntro)
        f.write("<p></p>");
        
        for channel in actualChannels:
            f.write("<h3>%s </h3>" % channel[0:2])
            f.write("<p></p>");
            
            f.write('<div class="row">')

            files = boxPlotDictionary['%s' % channel]
            for file in files:
                f.write('  <div class="column">')
                f.write('    <center><a href=\"./%s\" target="_blank"><img src="%s"></a></center><br>' % (file, file))
                f.write('  </div>')
                    
            f.write('</div>')
            

        f.write("<p></p>");
        f.write("<h3>Explore the Metrics</h3>")
        
        f.write("<p>PLACEHOLDER TEXT: MUSTANG is the Quality Assurance system at the IRIS DMC. It contains around 45 metrics related to the quality of data in the archives there.\n\n")
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
            f.write("<li><a href=\"http://service.iris.edu/mustang/measurements/1//query?metric=%s&network=%s&station=%s&location=%s&channel=%s&start=%s&end=%s&format=text\" target=\"_blank\">%s</a></li>\n" % (metric, network, stations, locations, channels, startDate, endDate, metric)); 
        f.write('</ul>')
        f.write('<br>')
        f.write('<hr style="width:100%;color:lightgray">')
        f.write('<p style="text-align:center"><a href="#top">Back to Top</a></p>')
        f.write('</div>')
        
        ## ADD PDFS 
        f.write('<div class="div-light">')
        f.write("</br>");
        f.write("<a name='pdfs'></a> <h2>PDF Plots</h2>")
        f.write("PDF plots for the stations with the greatest scaled RMS, lowest scaled RMS, and composite of all stations for each channel set\n")
        
        # Loop over each channel group, create a 3x3 (if 3 component) grid for each channel group
        for channel in actualChannels: 
            f.write("<h3>%s - <a href='http://service.iris.edu/mustang/noise-pdf-browser/1/gallery?network=%s&channel=%s&interval=all&starttime=%s&endtime=%s' target='_blank' >PDF Browser</a></h3>" % (channel[0:2], network, channel[0:2]+'?', startDate, endDate))
            f.write('<div class="row">')
            f.write('  <div class="column">')
            f.write('<center>Lowest RMS Station</center><br>')
            
            try:
                files = pdfDictionary['%s_smallest' % channel]
                
                for file in files:
                    f.write('    <center><a href=\"./%s\" target="_blank"><img src="%s"></a></center><br>' % (file, file))
                
            except:
                pass
            f.write('  </div>')   
            f.write('  <div class="column">')
            f.write('<center>Greatest RMS Station</center><br>')
            
            try:
                files = pdfDictionary['%s_greatest' % channel]
                for file in files:
                    f.write('    <center><a href=\"./%s\" target="_blank"><img src="%s"></a></center><br>' % (file, file))
                
            except:
                pass
            f.write('  </div>')
            f.write('  <div class="column">')
            f.write('<center>Network Composite</center><br>')
            try:
                files = pdfDictionary['%s_all' % channel]
                for file in files:
                    f.write('    <center><a href=\"./%s\" target="_blank"><img src="%s"></a></center><br>' % (file, file))
            except:
                pass
            f.write('  </div>')
            f.write('</div>')
        f.write('<p style="text-align:center"><a href="#top">Back to Top</a></p>')
        f.write('</div>')
        
        ## ADD SPECTROGRAMS
        f.write('<br>')
        f.write('<div class="div-dark">')
        f.write('<hr style="width:100%;color:lightgray">')
        f.write("</br>");
        f.write("<a name='spectrograms'></a> <h2>Spectrogram Plots</h2>")
    
        # Loop over each channel group, create a 3x2 (if 3 component) grid for each channel group
        for channel in actualChannels: 
            f.write("<h3>%s - <a href='http://service.iris.edu/mustang/noise-pdf-browser/1/spectrogram?network=%s&channel=%s&starttime=%s&endtime=%s' target='_blank' >Spectrogram Browser</a></h3>" % (channel[0:2], network, channel[0:2]+'?', startDate, endDate))
            f.write('<div class="row">')
            f.write('  <div class="spectcolumn">')
            f.write('<center>Lowest RMS Station</center><br>')
            
            try:
                files = spectDictionary['%s_smallest' % channel]
                for file in files:
                    f.write('    <center><a href=\"./%s\" target="_blank"><img src="%s"></a></center><br>' % (file, file))
            except:
                pass
            f.write('  </div>')
            
            f.write('  <div class="spectcolumn">')
            f.write('<center>Greatest RMS Station</center><br>')
            
            try:
                files = spectDictionary['%s_greatest' % channel]
                for file in files:
                    f.write('    <center><a href=\"./%s\" target="_blank"><img src="%s"></a></center><br>' % (file, file))
            except:
                pass
            
            f.write('  </div>')
            f.write('</div>')
        f.write('<hr style="width:100%;color:lightgray">')
        f.write('<p style="text-align:center"><a href="#top">Back to Top</a></p>')
        f.write('</div>')

    
        ## ADD MAP
        f.write('<div class="div-light">')
        f.write("</br>");
        f.write("<a name='map'></a> <h2>Map</h2>")
#         f.write('<div class="resp-container">')
#         f.write('<iframe class="resp-iframe" src="%s" gesture="media"  allow="encrypted-media" allowfullscreen></iframe></div>' % mapFilename)
        with open(mapFilename, "r") as f2:
            mapText = f2.read().replace('<html>','').replace('</html>','')
        f.write(mapText)
        f.write('<p style="text-align:center"><a href="#top">Back to Top</a></p>')
        f.write('</div>')
        
        ## ADD STATION TABLE
        f.write('<br>')
        f.write('<div class="div-dark">')
        f.write('<hr style="width:100%;color:lightgray">')
        f.write("</br>");
        f.write("<a name='stations'></a> <h2>Station List</h2>")
        f.write('<table class="hoverTable">')

        f.write('<tr><td><b>Network</b></td><td><b>Station</b></td><td><b>Latitude</b></td><td><b>Longitude</b></td><td><b>Elevation</b></td><td><b>Site Name</b></td><td><b>Start Date</b></td><td><b>End Date</b></td></tr>')
        
        for ind, row in metadataDF.iterrows():
            mdaLink = "http://ds.iris.edu/mda/%s/%s/?starttime=%s&endtime=%s" % (row['#Network'], row['Station'], row['StartTime'], row['EndTime'])
            
            f.write('<tr><td><a href="%s" target="_blank" >%s</a></td>' % (mdaLink, row['#Network']))
            f.write('<td><a href="%s" target="_blank" >%s</a></td>' % (mdaLink, row['Station']))
            f.write('<td><a href="%s" target="_blank" >%s</a></td>' % (mdaLink, row['Latitude']))
            f.write('<td><a href="%s" target="_blank" >%s</a></td>' % (mdaLink, row['Longitude']))
            f.write('<td><a href="%s" target="_blank" >%s</a></td>' % (mdaLink, row['Elevation']))
            f.write('<td><a href="%s" target="_blank" >%s</a></td>' % (mdaLink, row['SiteName']))
            f.write('<td><a href="%s" target="_blank" >%s</a></td>' % (mdaLink, row['StartTime']))
            f.write('<td><a href="%s" target="_blank" >%s</a></td></tr>' % (mdaLink, row['EndTime']))
            
        f.write('</table>')
        f.write('<hr style="width:100%;color:lightgray">')
        f.write('<p style="text-align:center"><a href="#top">Back to Top</a></p>')
        f.write('</div>')
        
        
        
        ## WRAP IT UP
        f.write("</body>");
    f.close();
    
    
    
print("INFO: Report Complete at " + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
