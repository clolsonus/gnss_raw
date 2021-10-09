#!/usr/bin/env python3

from datetime import datetime
import json
import numpy as np
import socket
import time # sleep

from laika import AstroDog
from laika.gps_time import GPSTime
from laika.raw_gnss import GNSSMeasurement, calc_pos_fix

from navpy import lla2ecef, ecef2lla


#dog = AstroDog(pull_orbit=False, valid_const=["GPS"]) # ephemeris
dog = AstroDog(pull_orbit=True, valid_const=["GPS"]) # precomputed

# connect to gpsd (presuming it's been started and presuming it's serving
# out a gps reciever that is reporting raw pseudoranges.)

init_string = b'?WATCH={"enable":true,"json":true,"scaled":true}'
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect( ("127.0.0.1", 2947) )
s.sendall(init_string)

buf = ""
measurements = []
xerr = []
yerr = []
zerr = []
tpv_x = []
tpv_y = []
tpv_z = []
lla_sol = []
est_pos = np.nan
tpv_ecef = np.nan
t_start = time.time()
while True:
    data = s.recv(4096).decode('utf-8')
    buf += data
    print("received bytes:", len(data), "len buf:", len(buf))
    messages = buf.split("\r\n")
    if len(messages[-1]):
        buf = messages[-1]
        messages.pop()
    for msg in messages:
        if len(msg):
            try:
                obj = json.loads(msg)
            except:
                print("json parse error!")
                print(msg)
                continue
            print(obj["class"])
            if obj["class"] == "TPV":
                if "lat" in obj:
                    tpv_ecef = lla2ecef(obj["lat"], obj["lon"], obj["altHAE"])
                    #tpv_ecef = lla2ecef(obj["lat"], obj["lon"], obj["alt"])
                    lla_sol = np.array( [obj["lat"], obj["lon"], obj["altHAE"]] )
                    tpv_x.append(tpv_ecef[0])
                    tpv_y.append(tpv_ecef[1])
                    tpv_z.append(tpv_ecef[2])
            elif obj["class"] == "RAW":
                # print(obj)
                # print(obj["time"], obj["nsec"])
                timestamp = obj["time"] + (obj["nsec"] / 1000000000.0)
                d = datetime.utcfromtimestamp(timestamp)
                recv_time = GPSTime.from_datetime(d)
                recv_time.tow += 18 # leap seconds !?!
                # print(timestamp)
                # print(d)
                # utcnow = GPSTime.from_datetime(datetime.utcnow())
                # print(utcnow, recv_time)

                measurements = []
                for obs in obj["rawdata"]:
                    #print(" ", obs["gnssid"], obs["svid"], obs["pseudorange"])
                    if obs["gnssid"] == 0:
                        prn = "G%02d" % obs["svid"]
                    #elif obs["gnssid"] == 1:
                    #    prn = "E%02d" % obs["svid"]
                    #elif obs["gnssid"] == 2:
                    #    prn = "R%02d" % obs["svid"]
                    else:
                        continue
                    #sat_info = dog.get_sat_info(prn, recv_time)
                    #print(prn, sat_info)
                    observables = {}
                    observables['C1C'] = obs["pseudorange"]
                    observables_std = {}
                    observables_std['C1C'] = 10.0
                    glonass_freq = np.nan
                    measurements.append(
                        GNSSMeasurement(prn,
                                        recv_time.week,
                                        recv_time.tow,
                                        observables,
                                        observables_std,
                                        glonass_freq))
                good_measurements = []
                for m in measurements:
                    m.process(dog)
                    included = False
                    if np.all(np.isnan(est_pos)):
                        print("nan position estimate, not doing correction")
                        good_measurements.append(m)
                        included = True
                    else:
                        m.correct(est_pos, dog)
                        if "C1C" in m.observables_final:
                            good_measurements.append(m)
                            included = True
                    print("sat:", m.prn, m.observables, m.observables_final, included, m.sat_clock_err)
                sol = calc_pos_fix(good_measurements)
                print("solution:", sol)
                if len(sol) and len(lla_sol):
                    est_pos = sol[0][:3]
                    print(" recv:", lla_sol)
                    print(" raw: ", np.array(ecef2lla(est_pos)))
                    if not np.all(np.isnan(tpv_ecef)):
                        print(np.mean(tpv_x), np.mean(tpv_y), np.mean(tpv_z))
                        # me = np.array( [-254847.40, -4512496.87, 4485627.85] ) # uavlab
                        err = np.linalg.norm(tpv_ecef - est_pos)
                        xerr.append( tpv_ecef[0] - est_pos[0] )
                        yerr.append( tpv_ecef[1] - est_pos[1] )
                        zerr.append( tpv_ecef[2] - est_pos[2] )
                        print("Run time: %.1f" % (time.time() - t_start))
                        print("  total error (m): %.2f" % err, "alt error: %.2f" % (ecef2lla(est_pos)[2] - lla_sol[2]))
                        print("  ecef error mean: %.2f, %.2f, %.2f (m)" % (np.mean(xerr), np.mean(yerr), np.mean(zerr)))
                        print("  ecef error std:  %.2f, %.2f, %.2f" % (np.std(xerr), np.std(yerr), np.std(zerr)))
                        print()
    time.sleep(1)
