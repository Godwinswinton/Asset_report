import streamlit as st
import pandas as pd
import numpy as np
import os
import glob
import io
import xlsxwriter
import time
import zipfile
import datetime
from math import radians, cos, sin, asin, sqrt

st.title('Asset Report')

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # radius of earth in kilometers
    R = 6371 

    # convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    d = R * c

    return d
start_time_1 = st.number_input('start_time')
st.write('The current number is ', start_time_1)

end_time_1 = st.number_input('end_time')
st.write('The current number is ', end_time_1)

def generate_asset_report(start_time: int, end_time: int, progress_bar: st):
    """
    Generate an asset report for a given time period
    """
    folder_path = '/Users/godwinswinton/Documents/Projects/cleaning/EOL-dump'

    # extract the vehicle trails from the zip file
    with zipfile.ZipFile('/Users/godwinswinton/Documents/Projects/cleaning/NU-raw-location-dump.zip', 'r') as zip_ref:
        zip_ref.extractall()

    # create an empty dataframe to store the vehicle trails
    trails = pd.DataFrame()

    # loop through each vehicle trail csv file and concatenate them into a single dataframe
    num_files = len(glob.glob(os.path.join(folder_path, '*.csv')))
    for i, file in enumerate(glob.glob(os.path.join(folder_path, '*.csv'))):
        df = pd.read_csv(file, usecols=['fk_asset_id', 'lic_plate_no', 'lat', 'lon', 'tis', 'spd', 'osf'])
        df = df.rename(columns={'lic_plate_no': 'vehicle_number'})
        df['tis'] = df['tis'].apply(lambda x: datetime.datetime.utcfromtimestamp(x).strftime('%Y%m%d%H%M%S')).astype(int)
        df = df[(df['tis'] >= start_time) & (df['tis'] <= end_time)]
        trails = pd.concat([trails, df], ignore_index=True)

        # update progress bar
        progress_percent = (i + 1) / num_files * 100
        progress_bar.progress(int(progress_percent))

    # calculate the distance for each vehicle
    trails['lat_shift'] = trails['lat'].shift(1)
    trails['lon_shift'] = trails['lon'].shift(1)
    trails['distance'] = trails.apply(lambda x: haversine(x['lat'], x['lon'], x['lat_shift'], x['lon_shift']), axis=1)

    # load the trip info data
    trip_info_df = pd.read_csv('/Users/godwinswinton/Documents/Projects/cleaning/Trip-Info.csv')

    # filter the trip info data by the specified time range
    trip_info_df = trip_info_df[(trip_info_df['date_time'] >= start_time) & (trip_info_df['date_time'] <= end_time)]

    # group the trails dataframe by vehicle number and compute the total distance and number of speed violations
    groups = trails.groupby('vehicle_number').agg({'distance': 'sum', 'osf': 'sum'})

    # compute the average speed for each vehicle and add it as a new column to the groups dataframe
    groups['avg_speed'] = trails['spd'].groupby(trails['vehicle_number']).mean()

    # group the trip info dataframe by vehicle number and compute the number of trips and transporter name
    groups_1 = trip_info_df.groupby('vehicle_number').agg({'trip_id': 'count', 'transporter_name': 'first'})

    merged_groups = pd.merge(groups, groups_1, on='vehicle_number')
    data = merged_groups.reset_index()
    data = data.rename(columns={'vehicle_number': 'License plate number', 'distance': 'Distance', 'osf': 'Number of Speed Violations', 'avg_speed': 'Average Speed', 'trip_id': 'Number of Trips Completed', 'transporter_name': 'Transporter Name'})


# sort the merged dataframe by total distance in descending order
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    data.to_excel(writer, sheet_name='Sheet1', index=False)

    writer.save()
    excel_data = output.getvalue()

    # Download the excel file
    st.download_button(
        label="Download data as Excel",
        data=excel_data,
        file_name='asset_report.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )

    #asset_report=data.to_csv(index=False).encode('utf-8')
    #st.download_button(
    #label="Download data as CSV",
    #data=asset_report,
    #file_name='large_df.csv',
    #mime='text/csv',)

    return st.dataframe(data)


progress_bar = st.progress(0)

btn=st.button("report")
if btn:
    generate_asset_report(start_time_1, end_time_1, progress_bar)
    
else:
    pass
