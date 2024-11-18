import pandas as pd
import matplotlib.pyplot as plt

import os
from pathlib import Path

file_path = os.path.join(Path(__file__).parent, 'Log__2024_10_11__05_50_47.csv')
# file_path = os.path.join(Path(__file__).parent, 'Log__2024_10_11__05_50_47.csv')

df = pd.read_csv(file_path)

print("Data from Excel:")
print(df.head())

fig1, axs1 = plt.subplots(3, sharex=True)
[ax_.set_xlim(75, 175) for ax_ in axs1]

for ax, dir in zip(axs1, ['X', 'Y', 'Z']):
    ax.plot(df.Time, -df[f'PDU Acceleration {dir}'])
    if dir == 'X': ax.plot(df.Time, df['Actual Torque'] / 10, 'r')
    if dir == 'Y': ax.plot(df.Time, (df['Steer Voltage'] - 1.25) * -20, 'r')
    # ax.plot(df.Time, df['Inverter Torque Request'] / 5, 'r')
    # ax.plot(df.Time, df['Speed'], 'b')
    # ax.plot(df.Time, (df['Heading'].diff() / df['Time'].diff() / df['Time'].diff()) / 3000, 'g--')
    ax.grid()
    
    
    
ax2 = plt.figure().add_subplot(projection='3d')
ax2.plot(df['Latitude'], df['Longitude'], zs=df['Time'])

# fig3, ax3 = plt.subplots(1, sharex=True)
# ax3.plot(df.Time, df['Actual Torque'])
# ax3.set_xlim(75, 175)

# fig4, ax4 = plt.subplots(1, sharex=True)
# ax4.plot(df.Time, df['Steer Voltage'], 'r')
# ax4.set_xlim(75, 175)

plt.show()