#!/bin/bash -x

rosrun pr2_controller_manager pr2_controller_manager stop r_arm_controller
rosrun pr2_controller_manager pr2_controller_manager unload r_arm_controller

rosparam load pr2_arm_controllers_grasp.yaml

rosrun pr2_controller_manager pr2_controller_manager load r_arm_controller

echo "Hit any key to start the controllers"
read inp
rosrun pr2_controller_manager pr2_controller_manager start r_arm_controller



