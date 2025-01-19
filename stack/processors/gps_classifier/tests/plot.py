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
    
    
ax2 = plt.figure().add_subplot(projection='3d')
norm = plt.Normalize(df['Speed'].min(), df['Speed'].max())
cmap = plt.get_cmap('viridis')
colors = cmap(norm(df['Speed']))
ax2.plot(df['Latitude'], df['Longitude'], zs=df['Time'], color=colors)

# fig3, ax3 = plt.subplots(1, sharex=True)
# ax3.plot(df.Time, df['Actual Torque'])
# ax3.set_xlim(75, 175)

# fig4, ax4 = plt.subplots(1, sharex=True)
# ax4.plot(df.Time, df['Steer Voltage'], 'r')
# ax4.set_xlim(75, 175)



times = [convert_to_epoch(df.iloc[0]) * 1000]
events = [0]

times += [np.float64(1728625934135.0), np.float64(1728625939434.0), np.float64(1728625939434.0), np.float64(1728625945540.0), np.float64(1728625945540.0), np.float64(1728625963602.0), np.float64(1728625963602.0), np.float64(1728625972801.0), np.float64(1728625972801.0), np.float64(1728625978646.0), np.float64(1728625978646.0), np.float64(1728626014535.0), np.float64(1728626014535.0)]
events += [1, 1, -1, -1, 1, 1, -1, -1, 1, 1, -1, -1, 0]

times.insert(1, times[1])
events.insert(1, 0)
times.append(times[-1])
events.append(0)
times.append(convert_to_epoch(df.iloc[-1]) * 1000)
events.append(0)

df_events = pd.DataFrame({'Time': times, 'Event': events})
df_events['Time'] = df['Time'][0] + df_events['Time'] / 1000 - convert_to_epoch(df.iloc[0])

print(convert_to_epoch(df.iloc[0]))
print(df_events['Time'][0])

axs1[4].plot(df_events['Time'], df_events['Event'], 'g')
axs1[4].grid()

plt.show()