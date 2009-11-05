#!/usr/bin/env python
##
# This utility is used for publishing 
# named and calibrated OpenCV accessible
# camera images over ROS.
#
# Usage ./ros_camera CAMERA_NAME
# where CAMERA_NAME is a name 
# in camera_config.py
#

import roslib
roslib.load_manifest('hrl_camera')
import sys
import rospy
import cv
import time
from std_msgs.msg import String
from sensor_msgs.msg import Image
from cv_bridge.cv_bridge import CvBridge, CvBridgeError
import hrl_camera.hrl_camera as hc

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'This utility is used for publishing '
        print 'named and calibrated OpenCV accessible'
        print 'camera images over ROS.'
        print '                         '              
        print 'Usage ./ros_camera CAMERA_NAME'
        print 'where CAMERA_NAME is a name '
        print 'in camera_config.py'

    camera_name = sys.argv[1]
    topic_name = 'cvcamera_' + camera_name

    image_pub = rospy.Publisher(topic_name, Image)
    rospy.init_node('cvcamera', anonymous=True)
    camera = hc.find_camera('ele_carriage')
    bridge = CvBridge()

    print 'Opening OpenCV camera with ID', camera_name
    print 'Publishing on topic', topic_name
    while not rospy.is_shutdown():
        try:
            cv_image = cv.CloneImage(camera.get_frame())
            rosimage = bridge.cv_to_imgmsg(cv_image, "bgr8")
            image_pub.publish(rosimage)
        except rospy.exceptions.ROSSerializationException, e:
            print 'serialization exception'
        except CvBridgeError, e: 
            print e
            break
        except KeyboardInterrupt:
            print "Shutting down."
            break
        time.sleep(1/100.0)

    cv.DestroyAllWindows()
