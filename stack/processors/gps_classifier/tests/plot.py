import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime


import os
from pathlib import Path

def convert_to_epoch(row):
     
    dt = datetime(
        year=int(row['Year']) + 2000,
        month=int(row['Month']),
        day=int(row['Day']),
        hour=int(row['Hour']) - 5,
        minute=int(row['Minute']),
        second=int(row['Seconds']),
        microsecond=int(row['Milliseconds']) * 1000
    )
    return int(dt.timestamp())

file_path = os.path.join(Path(__file__).parent, 'Log__2024_10_11__05_50_47.csv')
# file_path = os.path.join(Path(__file__).parent, 'Log__2024_10_11__05_50_47.csv')

df = pd.read_csv(file_path)

print("Data from Excel:")
print(df.head())

fig1, axs1 = plt.subplots(5, sharex=True)
[ax_.set_xlim(75, 175) for ax_ in axs1]

for ax, dir in zip(axs1, ['X', 'Y', 'Z']):
    ax.plot(df.Time, -df[f'PDU Acceleration {dir}'])
    if dir == 'X': ax.plot(df.Time, df['Actual Torque'] / 10, 'r')
    if dir == 'Y': ax.plot(df.Time, (df['Steer Voltage'] - 1.25) * -20, 'r')
    # ax.plot(df.Time, df['Inverter Torque Request'] / 5, 'r')
    # ax.plot(df.Time, (df['Heading'].diff() / df['Time'].diff() / df['Time'].diff()) / 3000, 'g--')
    ax.grid()
    
axs1[3].plot(df.Time, df['Speed'], 'b')
axs1[3].grid()

# fig3, ax3 = plt.subplots(1, sharex=True)
# ax3.plot(df.Time, df['Actual Torque'])
# ax3.set_xlim(75, 175)

# fig4, ax4 = plt.subplots(1, sharex=True)
# ax4.plot(df.Time, df['Steer Voltage'], 'r')
# ax4.set_xlim(75, 175)



times = [convert_to_epoch(df.iloc[0]) * 1000]
events = [0]

times += [np.float64(1728625927680.0), np.float64(1728625927680.0), np.float64(1728625939984.0), np.float64(1728625939984.0), np.float64(1728625939984.0), np.float64(1728625939984.0), np.float64(1728625944217.0), np.float64(1728625944217.0), np.float64(1728625940539.0), np.float64(1728625940539.0), np.float64(1728625944217.0), np.float64(1728625944217.0), np.float64(1728625941109.0), np.float64(1728625941109.0), np.float64(1728625944217.0), np.float64(1728625944217.0), np.float64(1728625942210.0), np.float64(1728625942210.0), np.float64(1728625942495.0), np.float64(1728625942495.0), np.float64(1728625942783.0), np.float64(1728625942783.0), np.float64(1728625943049.0), np.float64(1728625943049.0), np.float64(1728625943337.0), np.float64(1728625943337.0), np.float64(1728625945283.0), np.float64(1728625945283.0), np.float64(1728625950812.0), np.float64(1728625950812.0), np.float64(1728625945551.0), np.float64(1728625945551.0), np.float64(1728625949910.0), np.float64(1728625949910.0), np.float64(1728625945835.0), np.float64(1728625945835.0), np.float64(1728625949910.0), np.float64(1728625949910.0), np.float64(1728625946675.0), np.float64(1728625946675.0), np.float64(1728625949910.0), np.float64(1728625949910.0), np.float64(1728625960835.0), np.float64(1728625960835.0), np.float64(1728625964617.0), np.float64(1728625964617.0), np.float64(1728625961668.0), np.float64(1728625961668.0), np.float64(1728625961954.0), np.float64(1728625961954.0), np.float64(1728625963612.0), np.float64(1728625963612.0), np.float64(1728625963894.0), np.float64(1728625963894.0), np.float64(1728625969413.0), np.float64(1728625969413.0), np.float64(1728625964162.0), np.float64(1728625964162.0), np.float64(1728625969716.0), np.float64(1728625969716.0), np.float64(1728625964446.0), np.float64(1728625964446.0), np.float64(1728625969716.0), np.float64(1728625969716.0), np.float64(1728625964997.0), np.float64(1728625964997.0), np.float64(1728625969716.0), np.float64(1728625969716.0), np.float64(1728625972263.0), np.float64(1728625972263.0), np.float64(1728625977830.0), np.float64(1728625977830.0), np.float64(1728625978657.0), np.float64(1728625978657.0), np.float64(1728625983407.0), np.float64(1728625983407.0), np.float64(1728625978937.0), np.float64(1728625978937.0), np.float64(1728625983407.0), np.float64(1728625983407.0), np.float64(1728625981446.0), np.float64(1728625981446.0), np.float64(1728625981726.0), np.float64(1728625981726.0), np.float64(1728625982278.0), np.float64(1728625982278.0), np.float64(1728625982568.0), np.float64(1728625982568.0), np.float64(1728625984247.0), np.float64(1728625984247.0), np.float64(1728625990412.0), np.float64(1728625990412.0), np.float64(1728625984531.0), np.float64(1728625984531.0), np.float64(1728625990709.0), np.float64(1728625990709.0), np.float64(1728625984797.0), np.float64(1728625984797.0), np.float64(1728625989721.0), np.float64(1728625989721.0), np.float64(1728625985079.0), np.float64(1728625985079.0), np.float64(1728625989721.0), np.float64(1728625989721.0), np.float64(1728625985366.0), np.float64(1728625985366.0), np.float64(1728625989721.0), np.float64(1728625989721.0), np.float64(1728625994699.0), np.float64(1728625994699.0), np.float64(1728625997217.0), np.float64(1728625997217.0), np.float64(1728625999616.0), np.float64(1728625999616.0), np.float64(1728626014535.0)]
events += [0, 1, 1, 0, 0, -1, -1, 0, 0, -1, -1, 0, 0, -1, -1, 0, 0, -1, 0, -1, 0, -1, 0, -1, 0, -1, 0, -1, -1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, -1, -1, 0, 0, -1, 0, -1, 0, -1, 0, -1, -1, 0, 0, -1, -1, 0, 0, -1, -1, 0, 0, -1, -1, 0, 0, 1, 1, 0, 0, -1, -1, 0, 0, -1, -1, 0, 0, -1, 0, -1, 0, -1, 0, -1, 0, -1, -1, 0, 0, -1, -1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, -1, 0, 1, 1, 0, 0]

times.insert(1, times[1])
events.insert(1, 0)
times.append(times[-1])
events.append(0)
times.append(convert_to_epoch(df.iloc[-1]) * 1000)
events.append(0)

print(df['Speed'].describe())

df_events = pd.DataFrame({'Time': times, 'Event': events})
df_events['Time'] = df['Time'][0] + df_events['Time'] / 1000 - convert_to_epoch(df.iloc[0])

print(convert_to_epoch(df.iloc[0]))
print(df_events['Time'][0])




ax2 = plt.figure().add_subplot(projection='3d')

color_mapping = {1: 'green', -1: 'red', 0: 'black'}
colors = [color_mapping[event] for event in df_events['Event']]
for i in range(len(df_events['Time']) - 1):
    start_index = df['Time'].where(df['Time'] >= df_events['Time'][i]).argmin()
    end_index = df['Time'].where(df['Time'] >= df_events['Time'][i + 1]).argmin()

    
    plt.plot(df['Latitude'].iloc[start_index:end_index], df['Longitude'].iloc[start_index:end_index], zs=df['Time'].iloc[start_index:end_index], color=colors[i])


# ax2.plot(df['Latitude'], df['Longitude'], zs=df['Time'])


axs1[4].plot(df_events['Time'], df_events['Event'], 'g')
axs1[4].grid()

plt.show()