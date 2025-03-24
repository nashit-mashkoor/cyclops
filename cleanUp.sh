#!/bin/bash

#Place line below in crontab 
# @reboot sleep 10 && /home/pi/edge-pi-poc/cleanUp.sh

echo Running cleanUp.sh script to start Edge device with a clean slate
echo *****************************************************************

rm /home/pi/telemetryEdgeDatabase.*
rm /home/pi/miEdgeDatabase.*

rm /home/pi/edge-pi-poc/src/miModule/weights/tflite/c4h8o/*.npy
rm /home/pi/edge-pi-poc/src/miModule/weights/tflite/ch2o/*.npy
rm /home/pi/edge-pi-poc/src/miModule/weights/tflite/etoh/*.npy
rm /home/pi/edge-pi-poc/src/miModule/weights/tflite/nh3/*.npy
rm /home/pi/edge-pi-poc/src/miModule/weights/tflite/nicotine/*.npy
rm /home/pi/edge-pi-poc/src/miModule/weights/tflite/no/*.npy
rm /home/pi/edge-pi-poc/src/miModule/weights/tflite/no2/*.npy

rm /home/pi/edge-pi-poc/src/log.txt
rm /home/pi/edge-pi-poc/out.txt

echo  Finished running cleanUp.sh script. Device should now be clean
echo *****************************************************************

